"""PPO a masque d'actions, self-play avec pool fige. **Le seul module qui entraine.**

L'algorithme et ses raisons sont pre-inscrits au paragraphe 5 de
`mesure/phase3_hypothese_et_instrument.md`, **avant** tout entrainement. Ce module ne rouvre
aucun arbitrage ; il execute ce qui y est ecrit, et chaque constante ci-dessous renvoie au
paragraphe qui la fixe.

Trois choses que ce module fait autrement que le PPO des manuels, et pourquoi
------------------------------------------------------------------------------

**1. `gamma = 1` et `lambda = 1`. L'avantage est de Monte-Carlo, pas de GAE.**

`gamma = 1` est pre-inscrit : l'horizon est **fixe** -- 4 tours par joueur -- et le gain
n'arrive qu'au terminal, donc actualiser prefererait un point tot a un point tard alors que
seul le decompte paie.

`lambda = 1` n'est pas un defaut de paresse, c'est une **decision de correction**. GAE avec
`lambda < 1` a besoin de « l'etat suivant du siege `i` », et a trois joueurs entrelaces
**ce n'est pas le nœud suivant de la partie** : c'est le prochain nœud ou `i` decide, deux ou
trois nœuds plus loin. Un bootstrap qui prendrait le nœud suivant amorcerait sur la valeur d'un
adversaire, et la faute serait **silencieuse** : la perte descendrait, l'agent apprendrait
autre chose que ce qu'on croit. A `lambda = 1` l'avantage vaut `R - V(s)` et ne demande que le
gain terminal du siege, qui est sans ambiguite. Le prix est une variance plus grande, et il est
paye sciemment.

**2. Les trajectoires sont par SIEGE, pas par partie.** Une partie produit une trajectoire par
siege joue par la politique **courante**. Les sieges tenus par un checkpoint fige sont joues
mais **jamais collectes** : leurs actions viennent d'une autre politique, donc les inclure
rendrait la mise a jour hors-politique sans que le ratio de PPO le sache.

**3. Le tirage passe par `random.Random`, jamais par le generateur global de torch.** C'est
`reseau.tirer`, et c'est le meme chemin de decision a l'entrainement et a l'evaluation :
l'agent mesure est **exactement** celui qui a ete entraine, pas une variante deterministe de
lui-meme.

Ce qui n'entraine pas
----------------------
**Ni le greedy ni l'aleatoire n'entrent dans le pool** (paragraphe 6 de la pre-inscription).
S'entrainer contre le greedy transformerait « bat le greedy » en test **dans** la distribution.
L'aleatoire sert au garde-fou, et **ce qui mesure n'entraine pas**.

La contrepartie assumee est l'**effondrement de convention** en self-play, dont les checkpoints
figes sont le garde-fou -- et qui se mesure, paragraphe 9.1.
"""

from __future__ import annotations

import random
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

import torch
from torch import nn, optim

from agents import reseau as reseau_module
from courtisans.engine import Engine, State
from courtisans.infoset import tenseur
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J

#: Les donnes d'entrainement. **Disjointes de toutes les plages de mesure** : 20000-21999
#: (dimensionnement), 30000+ (campagne finale), 40000+ (garde-fou). S'entrainer sur les donnes
#: qui jugeront l'agent lui donnerait un avantage qui n'est pas de l'habilete.
DEPART_DONNE_ENTRAINEMENT = 100_000

#: Les aleas. Disjoints de ceux de la phase 2 et de `mesure/phase3.py`.
DECALAGE_TIRAGE = 9_000_000
DECALAGE_ADVERSAIRE = 9_500_000

#: Paragraphe 6.1 de la pre-inscription : 60 % copie courante, 40 % checkpoint fige. **Choix de
#: plan, pas mesure.** Les changer est un levier de la phase 4, une variable a la fois.
PART_SELF_PLAY = 0.60
POOL_MAXIMUM = 8

#: Hyperparametres de PPO. **Choix de plan**, valeurs usuelles, non mesurees sur ce jeu.
TAUX_APPRENTISSAGE = 3e-4
CLIP = 0.2
EPOQUES = 4
TAILLE_LOT = 1024
COEFFICIENT_ENTROPIE = 0.01
COEFFICIENT_VALEUR = 0.5
NORME_GRADIENT_MAX = 0.5


@dataclass
class Trajectoires:
    """Ce qu'une vague de parties a produit, pour les seuls sieges de la politique courante.

    Attributes:
        observations: un tenseur par nœud decide.
        masques: les actions legales de ce nœud.
        actions: l'indice choisi.
        log_probabilites: `log pi(a|s)` **au moment du choix**, sous la politique qui a joue.
        valeurs: `V(s)` au moment du choix.
        gains: le gain terminal du siege qui decidait. Le meme pour tous les nœuds d'un siege.
        donnes: la donne d'ou vient le nœud.
        sieges: le siege qui decidait.

    **`donnes` et `sieges` ne servent pas a l'apprentissage** -- PPO melange les nœuds, leur
    ordre lui est indifferent. Ils servent a l'AUDIT : sans eux, la provenance d'un nœud est
    perdue des qu'il entre dans la vague, et « ce nœud porte-t-il le gain de son siege ? » n'est
    plus une question verifiable. Les nœuds sont ranges dans l'ordre du **lock-step**, pas par
    partie : un lecteur qui comparerait deux vagues de tailles differentes par leur prefixe
    comparerait deux entrelacements distincts.
    """

    observations: list[list[float]] = field(default_factory=list)
    masques: list[list[int]] = field(default_factory=list)
    actions: list[int] = field(default_factory=list)
    log_probabilites: list[float] = field(default_factory=list)
    valeurs: list[float] = field(default_factory=list)
    gains: list[float] = field(default_factory=list)
    donnes: list[int] = field(default_factory=list)
    sieges: list[int] = field(default_factory=list)

    def par_partie(self) -> dict[tuple[int, int], list[int]]:
        """Les indices des nœuds, groupes par `(donne, siege)`. L'entree de tout audit."""
        groupes: dict[tuple[int, int], list[int]] = {}
        for rang, (donne, siege) in enumerate(zip(self.donnes, self.sieges, strict=True)):
            groupes.setdefault((donne, siege), []).append(rang)
        return groupes

    def __len__(self) -> int:
        return len(self.actions)


@dataclass
class _PartieEnCours:
    """Une partie de la vague, et qui joue quel siege.

    **Chaque partie porte son propre aleatoire, derive de sa donne.** C'est ce qui la rend
    reproductible depuis son seul seed, independamment de la taille de la vague : les parties
    avancent en lock-step, donc un aleatoire partage ferait dependre le deroulement d'une
    partie de celles qui l'accompagnent par hasard dans le meme lot. Une vague de 64 et une
    vague de 256 ne joueraient alors pas les memes parties sur les memes donnes, et aucun
    resultat ne serait rejouable a l'unite. C'est le paragraphe 5 des conventions.

    **Trouve par un test**, `test_chaque_noeud_porte_le_gain_terminal_de_SON_siege` : sa
    reconstruction independante rejouait les parties l'une apres l'autre et obtenait d'autres
    parties. La boucle n'etait pas fausse, elle etait irreproductible a l'unite -- et c'est un
    defaut a part entiere quand un chiffre doit se refaire.
    """

    etat: State
    #: Pour chaque siege : `None` s'il est joue par la politique courante, sinon l'indice du
    #: checkpoint fige qui le joue.
    tenu_par: list[int | None]
    #: Les indices des nœuds collectes, par siege, pour leur attribuer le gain terminal.
    noeuds_par_siege: dict[int, list[int]]
    #: L'aleatoire de tirage de CETTE partie.
    alea: random.Random
    #: La donne, recopiee pour que chaque nœud collecte porte sa provenance.
    donne: int


def _composer(alea: random.Random, pool: Sequence[object]) -> list[int | None]:
    """Qui joue quel siege, pour une partie.

    L'agent courant occupe un siege tire uniformement ; les deux autres sont tires
    **independamment** entre copie courante et checkpoint fige. Independamment, et c'est
    delibere : une partie peut opposer l'agent a une copie de lui-meme **et** a un checkpoint,
    et une population ou il ne rencontrerait jamais deux especes a la fois ne ressemblerait a
    aucune des deux compositions mesurees.

    Quand le pool est vide -- au tout debut du run --, tout est joue par la politique courante :
    c'est du self-play pur, et c'est le seul etat possible avant le premier checkpoint.
    """
    tenu: list[int | None] = [None] * CONFIG.joueurs
    apprenant = alea.randrange(CONFIG.joueurs)
    for siege in range(CONFIG.joueurs):
        if siege == apprenant or not pool:
            continue
        if alea.random() >= PART_SELF_PLAY:
            tenu[siege] = alea.randrange(len(pool))
    return tenu


def _forward(
    modele: reseau_module.ReseauPolitiqueValeur,
    observations: list[list[float]],
    actions_legales: list[list[int]],
    appareil: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Une passe avant, en lot. Rend `(loi masquee, valeurs)`, toutes deux sur le CPU."""
    with torch.no_grad():
        entree = torch.tensor(observations, dtype=torch.float32, device=appareil)
        logits, valeurs = modele(entree)
        plan = reseau_module.masque(actions_legales, modele.nb_actions).to(appareil)
        loi = reseau_module.probabilites(logits, plan)
    return loi.cpu(), valeurs.cpu()


def jouer_une_vague(
    modele: reseau_module.ReseauPolitiqueValeur,
    pool: Sequence[reseau_module.ReseauPolitiqueValeur],
    nb_parties: int,
    premiere_donne: int,
    appareil: torch.device,
) -> tuple[Trajectoires, int]:
    """Joue `nb_parties` parties en parallele et rend les trajectoires de la politique courante.

    **Il n'y a pas de parametre `alea`, et c'est voulu.** Chaque partie derive le sien de sa
    donne, donc la vague entiere est determinee par `premiere_donne` et `nb_parties`. Un
    aleatoire passe de l'exterieur ferait dependre une partie de celles qui l'accompagnent
    dans le lot, et « la meme donne » ne designerait plus la meme partie.

    **Les parties avancent en lock-step et les decisions sont groupees par reseau.** Une passe
    avant par reseau et par pas, plutot qu'une par nœud : le reseau est minuscule, donc le cout
    d'un appel est domine par son lancement, pas par son calcul.

    Rend aussi le nombre de parties jouees, qui sert a chiffrer le debit.
    """
    moteur = Engine(CONFIG)
    parties = []
    for indice in range(nb_parties):
        donne = premiere_donne + indice
        etat = moteur.reset(donne)
        parties.append(
            _PartieEnCours(
                etat=etat,
                tenu_par=_composer(random.Random(DECALAGE_ADVERSAIRE + donne), pool),
                noeuds_par_siege={siege: [] for siege in range(CONFIG.joueurs)},
                alea=random.Random(DECALAGE_TIRAGE + donne),
                donne=donne,
            )
        )

    trajectoires = Trajectoires()
    vivantes = [p for p in parties if not p.etat.is_terminal()]
    while vivantes:
        # Grouper les nœuds en attente par reseau decideur. `None` est la politique courante.
        groupes: dict[int | None, list[_PartieEnCours]] = {}
        for partie in vivantes:
            siege = partie.etat.current_player()
            groupes.setdefault(partie.tenu_par[siege], []).append(partie)

        for decideur, lot in groupes.items():
            reseau_decideur = modele if decideur is None else pool[decideur]
            observations = []
            actions_legales = []
            for partie in lot:
                siege = partie.etat.current_player()
                observations.append(tenseur(partie.etat, siege))
                actions_legales.append(partie.etat.legal_actions())
            loi, valeurs = _forward(
                reseau_decideur, observations, actions_legales, appareil
            )
            for rang, partie in enumerate(lot):
                siege = partie.etat.current_player()
                ligne = loi[rang].tolist()
                indice = reseau_module.tirer(ligne, partie.alea)
                # `indice` EST l'action : la tete du reseau est indexee sur l'espace d'action
                # du moteur, et `probabilites` a mis a **exactement** zero tout ce qui n'est
                # pas legal. Le controle ci-dessous ne devrait donc jamais mordre -- et c'est
                # pour ca qu'il LEVE au lieu de replier sur une action par defaut. Un repli
                # silencieux ferait jouer autre chose que ce que la politique a choisi, et
                # l'agent apprendrait sur une action qu'il n'a pas prise.
                if indice not in actions_legales[rang]:
                    raise ValueError(
                        f"action {indice} tiree alors qu'elle n'est pas legale parmi "
                        f"{actions_legales[rang]} : le masque de `probabilites` ne tient plus."
                    )
                action = indice
                if decideur is None:
                    # **Seuls les nœuds de la politique courante sont collectes.** Ceux d'un
                    # checkpoint fige viennent d'une autre politique : les inclure rendrait la
                    # mise a jour hors-politique sans que le ratio de PPO le sache.
                    partie.noeuds_par_siege[siege].append(len(trajectoires))
                    trajectoires.observations.append(observations[rang])
                    trajectoires.masques.append(actions_legales[rang])
                    trajectoires.actions.append(indice)
                    trajectoires.log_probabilites.append(
                        float(torch.log(torch.clamp(loi[rang, indice], min=1e-12)))
                    )
                    trajectoires.valeurs.append(float(valeurs[rang]))
                    trajectoires.gains.append(0.0)  # rempli au terminal
                    trajectoires.donnes.append(partie.donne)
                    trajectoires.sieges.append(siege)
                partie.etat.apply(action)

        vivantes = [p for p in vivantes if not p.etat.is_terminal()]

    # Le gain terminal du siege, recopie sur chacun de ses nœuds. `gamma = 1`, donc le retour
    # d'un nœud EST le gain final : il n'y a rien a actualiser ni a cumuler.
    for partie in parties:
        gains = partie.etat.returns()
        for siege, noeuds in partie.noeuds_par_siege.items():
            for noeud in noeuds:
                trajectoires.gains[noeud] = gains[siege]
    return trajectoires, len(parties)


def mettre_a_jour(
    modele: reseau_module.ReseauPolitiqueValeur,
    optimiseur: optim.Optimizer,
    trajectoires: Trajectoires,
    appareil: torch.device,
    alea: random.Random,
) -> dict[str, float]:
    """Une mise a jour PPO complete sur une vague. Rend ses pertes, pour le journal.

    L'avantage est `R - V(s)`, **normalise sur la vague**. La normalisation est faite une fois,
    avant les epoques, et non par mini-lot : normaliser par mini-lot ferait dependre l'avantage
    d'un nœud de ceux qui l'accompagnent par hasard dans le tirage.
    """
    if not trajectoires:
        raise ValueError("vague vide : une mise a jour ne se fait pas sur du vide")

    observations = torch.tensor(
        trajectoires.observations, dtype=torch.float32, device=appareil
    )
    plan = reseau_module.masque(trajectoires.masques, modele.nb_actions).to(appareil)
    actions = torch.tensor(trajectoires.actions, dtype=torch.long, device=appareil)
    anciennes = torch.tensor(
        trajectoires.log_probabilites, dtype=torch.float32, device=appareil
    )
    retours = torch.tensor(trajectoires.gains, dtype=torch.float32, device=appareil)

    avantages = retours - torch.tensor(
        trajectoires.valeurs, dtype=torch.float32, device=appareil
    )
    avantages = (avantages - avantages.mean()) / (avantages.std() + 1e-8)

    nb = len(trajectoires)
    ordre = list(range(nb))
    pertes = {"politique": 0.0, "valeur": 0.0, "entropie": 0.0}
    lots = 0
    for _ in range(EPOQUES):
        alea.shuffle(ordre)
        for debut in range(0, nb, TAILLE_LOT):
            indices = torch.tensor(
                ordre[debut : debut + TAILLE_LOT], dtype=torch.long, device=appareil
            )
            logits, valeurs = modele(observations[indices])
            loi = reseau_module.probabilites(logits, plan[indices])
            journal = torch.log(torch.clamp(loi, min=1e-12))
            choisies = journal.gather(1, actions[indices].unsqueeze(1)).squeeze(1)

            ratio = torch.exp(choisies - anciennes[indices])
            avantage = avantages[indices]
            perte_politique = -torch.min(
                ratio * avantage,
                torch.clamp(ratio, 1.0 - CLIP, 1.0 + CLIP) * avantage,
            ).mean()
            perte_valeur = nn.functional.mse_loss(valeurs, retours[indices])
            entropie = -(loi * journal).sum(dim=-1).mean()

            perte = (
                perte_politique
                + COEFFICIENT_VALEUR * perte_valeur
                - COEFFICIENT_ENTROPIE * entropie
            )
            optimiseur.zero_grad(set_to_none=True)
            perte.backward()
            nn.utils.clip_grad_norm_(modele.parameters(), NORME_GRADIENT_MAX)
            optimiseur.step()

            # `.detach()` avant la conversion : sans lui, torch avertit qu'on transforme en
            # scalaire un tenseur qui porte encore son graphe de gradient.
            pertes["politique"] += float(perte_politique.detach())
            pertes["valeur"] += float(perte_valeur.detach())
            pertes["entropie"] += float(entropie.detach())
            lots += 1
    return {cle: valeur / lots for cle, valeur in pertes.items()}


def construire(appareil: torch.device) -> reseau_module.ReseauPolitiqueValeur:
    """Un reseau de la bonne taille pour `entrainement-3j`, **mesuree et non ecrite en dur**.

    La taille de l'observation et le nombre d'actions sont **demandes au moteur**, jamais
    recopies : le paragraphe 3 des conventions interdit la valeur en dur, et une tete de
    mauvaise taille produirait un agent qui croit poser une carte et en pose une autre.
    """
    etat = Engine(CONFIG).reset(0)
    taille = len(tenseur(etat, 0))
    nb_actions = 6 * 2 * (CONFIG.joueurs - 1)
    if max(etat.legal_actions()) >= nb_actions:
        raise ValueError(
            f"le moteur expose une action d'indice {max(etat.legal_actions())} pour une tete "
            f"de {nb_actions} : l'espace d'action et le reseau ont divergé."
        )
    modele = reseau_module.ReseauPolitiqueValeur(taille, nb_actions).to(appareil)
    return modele


def appareil_par_defaut() -> torch.device:
    """Le GPU s'il existe. **La phase 2 n'en utilisait aucun ; la phase 3 le peut.**"""
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def chronometrer_le_debit(
    modele: reseau_module.ReseauPolitiqueValeur,
    appareil: torch.device,
    nb_parties: int = 64,
    passes: int = 3,
) -> dict[str, list[float]]:
    """Chronometre separement le moteur et le reseau, sur **plusieurs passes**.

    **Repond a un SUPPOSE laisse ouvert dans le compte rendu du tour 1** : « le moteur stdlib
    est le goulot, pas le reseau » a ete ecrit comme un fait alors qu'il n'etait pas mesure, et
    il fondait la conception de la parallelisation. Le paragraphe 0.2 exige au moins **trois
    passes avec leur etendue** ; cette fonction les rend toutes, sans moyenne, pour que
    l'etendue soit lisible.

    Les deux mesures ne sont pas exclusives : « partie complete » contient le reseau. Ce qui se
    lit est leur **rapport**, et l'ecart entre la partie complete et le moteur seul.
    """
    resultats: dict[str, list[float]] = {
        "partie_complete": [],
        "moteur_seul": [],
        "reseau_seul": [],
    }
    for passe in range(passes):
        debut = time.perf_counter()
        jouer_une_vague(
            modele, [], nb_parties, DEPART_DONNE_ENTRAINEMENT + 900_000, appareil
        )
        resultats["partie_complete"].append(time.perf_counter() - debut)

        # Le moteur seul : memes parties, action tiree sans reseau.
        moteur = Engine(CONFIG)
        alea = random.Random(DECALAGE_TIRAGE + passe)
        debut = time.perf_counter()
        noeuds = 0
        for indice in range(nb_parties):
            etat = moteur.reset(DEPART_DONNE_ENTRAINEMENT + 900_000 + indice)
            while not etat.is_terminal():
                tenseur(etat, etat.current_player())
                etat.apply(alea.choice(etat.legal_actions()))
                noeuds += 1
        resultats["moteur_seul"].append(time.perf_counter() - debut)

        # Le reseau seul : autant de passes avant que de nœuds, en lots de la meme taille.
        observations = [[0.0] * modele.taille_observation for _ in range(nb_parties)]
        legales = [list(range(modele.nb_actions)) for _ in range(nb_parties)]
        debut = time.perf_counter()
        for _ in range(max(1, noeuds // nb_parties)):
            _forward(modele, observations, legales, appareil)
        resultats["reseau_seul"].append(time.perf_counter() - debut)
    return resultats


__all__ = [
    "CONFIG",
    "DEPART_DONNE_ENTRAINEMENT",
    "POOL_MAXIMUM",
    "PART_SELF_PLAY",
    "Trajectoires",
    "appareil_par_defaut",
    "chronometrer_le_debit",
    "construire",
    "jouer_une_vague",
    "mettre_a_jour",
]

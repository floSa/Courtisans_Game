"""La decision d'un agent entraine. **Ce module ne voit ni `State` ni `Perception`.**

Sa frontiere est plus etroite que celle du greedy, et c'est delibere
-------------------------------------------------------------------
`agents/greedy.py` recoit une `Perception` : un objet riche, dont chaque champ a du etre
justifie un a un. Ce module-ci recoit **un vecteur de flottants et une liste d'indices**. Un
`Sequence[float]` ne porte aucune methode, aucun `State`, aucune reference : il ne peut rien
fuiter, quelle que soit la facon dont il est lu. **L'aveuglement n'est pas une discipline a
tenir, c'est une consequence de la signature** -- comme pour le greedy, mais d'un cran plus
serre.

Ce que le vecteur contient, et pourquoi il a le droit d'y etre
---------------------------------------------------------------
C'est exactement `courtisans.infoset.tenseur(etat, joueur)`, l'observation officielle du
moteur, definie au paragraphe 4.2 de `03_specification_moteur.md` et tenue par l'invariant
I7. Elle part de `vue_du_joueur` -- les faces visibles et ses propres Espions -- et ne contient
**rien d'autre** : `tests/infoset/test_vue_du_joueur.py` permute l'identite des dos adverses et
exige que le tenseur ne bouge pas.

**Aucun champ n'est ajoute a `Perception` par cette phase.** Le paragraphe 4.2 des regles n'a
pas eu a etre rouvert : l'observation existante suffit.

Ce que ce module ne fait PAS, et c'est ce qui rend la preuve possible
----------------------------------------------------------------------
Il n'appelle pas le moteur, ne calcule aucune regle, ne decode aucune action. Il ne sait meme
pas ce que ses 24 sorties signifient : c'est `agents/politique_reseau.py` qui traduit, et c'est
**lui seul** qui touche un `State`.

Le masque : un seul site, et il refuse le vide
------------------------------------------------
Les indices d'action se **recouvrent** entre phases -- une pose va de 0 a 23, un ciblage de 0 a
`len(cibles)`, et l'indice 2 ne designe pas la meme chose dans les deux. Ce qui les separe est
**dans le tenseur** : la phase et la zone de l'Assassin en cours y sont encodees, et c'est le
troisieme des trois pieges du paragraphe 4.2. Le reseau a donc de quoi les distinguer, et le
masque n'a qu'a interdire ce qui n'est pas legal ici et maintenant.

Le masquage vit dans **une seule fonction**, `probabilites`. Un second site finirait par ne plus
etre d'accord avec le premier, et c'est la mesure qui aurait tort sans que rien ne le signale.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

import torch
from torch import nn

#: Le nombre d'actions distinctes de l'instance. **Passe a la construction, jamais en dur** :
#: le paragraphe 3 des conventions l'interdit, et une tete de mauvaise taille produirait un
#: agent qui croit poser une carte et en pose une autre.
#:
#: Pour `entrainement-3j` il vaut 24 -- `6 x 2 x (joueurs - 1)`, paragraphe 3.2 des regles --
#: et les ciblages, qui vont de 0 a `len(cibles)`, y tiennent tous.


class ReseauPolitiqueValeur(nn.Module):
    """Un tronc partage, une tete de politique, une tete de valeur.

    **Un seul reseau pour les trois sieges, et ce n'est pas une economie.** L'observation est
    deja **relative a l'observateur** -- `infoset._relatif`, « 0 c'est moi, 1 le suivant, 2
    celui d'apres » --, donc un reseau partage est la **symetrie correcte du probleme**. Trois
    reseaux distincts apprendraient trois fois la meme fonction sur trois tiers des donnees.

    Le risque que cette relativite fait naitre est le seul qui compte ici : si deux nœuds a des
    positions differentes dans l'ordre du tour partageaient un tenseur, le reseau serait
    **plafonne par construction et rien ne le dirait**. Le controle est pre-inscrit et mesure --
    115 299 nœuds, 106 590 tenseurs distincts, **0 collision** sur la composition de la
    phase 3 -- et c'est un ECHANTILLON, pas une preuve d'injectivite.

    Attributes:
        taille_observation: la longueur du tenseur. 205 sur `entrainement-3j`.
        nb_actions: la taille de la tete de politique.
    """

    def __init__(
        self,
        taille_observation: int,
        nb_actions: int,
        largeur: int = 256,
        profondeur: int = 2,
    ) -> None:
        super().__init__()
        if taille_observation < 1 or nb_actions < 1:
            raise ValueError(
                f"un reseau a besoin d'une observation et d'actions : "
                f"taille_observation={taille_observation}, nb_actions={nb_actions}"
            )
        if profondeur < 1:
            raise ValueError(f"il faut au moins une couche cachee, {profondeur} demandee(s)")
        self.taille_observation = taille_observation
        self.nb_actions = nb_actions

        couches: list[nn.Module] = []
        entree = taille_observation
        for _ in range(profondeur):
            couches += [nn.Linear(entree, largeur), nn.ReLU()]
            entree = largeur
        self.tronc = nn.Sequential(*couches)
        self.tete_politique = nn.Linear(largeur, nb_actions)
        self.tete_valeur = nn.Linear(largeur, 1)

        # Initialisation orthogonale, gains usuels de PPO. La tete de politique part a 0,01
        # pour que la politique initiale soit **quasi uniforme** sur les actions legales : une
        # politique initiale piquee explorerait mal, et le premier checkpoint du pool serait
        # une convention arbitraire plutot qu'un point de depart neutre.
        for couche in self.tronc:
            if isinstance(couche, nn.Linear):
                nn.init.orthogonal_(couche.weight, gain=math.sqrt(2))
                nn.init.zeros_(couche.bias)
        nn.init.orthogonal_(self.tete_politique.weight, gain=0.01)
        nn.init.zeros_(self.tete_politique.bias)
        nn.init.orthogonal_(self.tete_valeur.weight, gain=1.0)
        nn.init.zeros_(self.tete_valeur.bias)

    def forward(self, observations: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Rend `(logits, valeurs)`. `valeurs` est aplatie : une valeur par ligne."""
        if observations.dim() != 2 or observations.shape[1] != self.taille_observation:
            raise ValueError(
                f"observations de forme {tuple(observations.shape)}, attendu "
                f"(n, {self.taille_observation})"
            )
        cache = self.tronc(observations)
        return self.tete_politique(cache), self.tete_valeur(cache).squeeze(-1)


def masque(actions_legales: Sequence[Sequence[int]], nb_actions: int) -> torch.Tensor:
    """Un booleen par (ligne, action) : vrai si l'action est legale sur cette ligne.

    Raises:
        ValueError: si une ligne n'a aucune action legale, ou si un indice sort de la tete.
            Une ligne vide produirait un `softmax` de `-inf` partout, donc des `NaN` qui se
            propageraient dans le gradient **sans que rien ne leve** -- l'agent apprendrait sur
            du bruit et la perte deviendrait `NaN` plusieurs etapes plus tard, loin de la cause.
    """
    if not actions_legales:
        raise ValueError("aucune ligne : un masque ne se construit pas sur du vide")
    plan = torch.zeros(len(actions_legales), nb_actions, dtype=torch.bool)
    for ligne, actions in enumerate(actions_legales):
        if not actions:
            raise ValueError(
                f"ligne {ligne} : aucune action legale. Un etat de decision en a toujours au "
                f"moins une (controle C17) ; masquer tout produirait des NaN silencieux."
            )
        for action in actions:
            if not 0 <= action < nb_actions:
                raise ValueError(
                    f"ligne {ligne} : action {action} hors de la tete de taille {nb_actions}. "
                    f"La tete du reseau et l'espace d'action du moteur ont divergé."
                )
            plan[ligne, action] = True
    return plan


def probabilites(logits: torch.Tensor, plan: torch.Tensor) -> torch.Tensor:
    """La politique masquee. **Le seul site ou le masque s'applique.**

    Les actions illegales recoivent `-inf` avant le `softmax`, donc une probabilite
    **exactement** nulle -- pas « tres petite ». Une probabilite tres petite finit par etre
    tiree une fois sur un million de coups, et le moteur leverait alors sur une action illegale,
    tres loin de la cause.
    """
    if logits.shape != plan.shape:
        raise ValueError(
            f"logits de forme {tuple(logits.shape)} et masque {tuple(plan.shape)} : "
            f"les deux doivent decrire les memes (ligne, action)"
        )
    return torch.softmax(logits.masked_fill(~plan, float("-inf")), dim=-1)


def tirer(loi: Sequence[float], alea: random.Random) -> int:
    """Tire un indice selon `loi`, par fonction de repartition inverse.

    **Le tirage passe par `random.Random`, jamais par le generateur global de torch.** Le
    paragraphe 5 des conventions l'impose -- « aucun appel a `random` global : une instance
    `Random(seed)` passee explicitement » -- et c'est ce qui rend une partie reproductible
    depuis son seul seed. C'est aussi ce qui permet a l'entrainement et a l'evaluation de
    partager **un seul** chemin de tirage : le meme code decide dans les deux, donc l'agent
    mesure est celui qui a ete entraine.

    Raises:
        ValueError: si la loi ne somme pas a 1 a 1e-6 pres. Une loi qui ne somme pas a 1 est
            le symptome d'un masque mal applique, et le tirage rendrait quand meme un indice.
    """
    total = float(sum(loi))
    if not math.isfinite(total) or abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"la loi somme a {total}, attendu 1 : le masque a ete mal applique, ou un logit "
            f"vaut NaN. Tirer quand meme rendrait un indice sans signification."
        )
    seuil = alea.random() * total
    cumul = 0.0
    for indice, poids in enumerate(loi):
        cumul += poids
        if seuil < cumul:
            return indice
    # Atteignable seulement par accumulation de flottants quand `seuil` frole `total`.
    # On rend le dernier indice de probabilite non nulle, jamais un indice masque.
    for indice in range(len(loi) - 1, -1, -1):
        if loi[indice] > 0.0:
            return indice
    raise ValueError("loi entierement nulle : aucun indice n'est tirable")


def choisir(
    reseau: ReseauPolitiqueValeur,
    observation: Sequence[float],
    actions_legales: Sequence[int],
    alea: random.Random,
) -> int:
    """L'action choisie pour **une** observation. C'est toute la decision de l'agent.

    Sa signature est la preuve statique de son aveuglement : une suite de flottants, une suite
    d'indices, un generateur. **Rien de ce qui entre ici ne peut porter la pioche, une main
    adverse, l'identite d'un dos, `scores()` ni `returns()`.**
    """
    with torch.no_grad():
        entree = torch.tensor([list(observation)], dtype=torch.float32)
        logits, _ = reseau(entree.to(next(reseau.parameters()).device))
        loi = probabilites(logits.cpu(), masque([list(actions_legales)], reseau.nb_actions))
    indice = tirer(loi[0].tolist(), alea)
    return indice


def choisir_le_plus_probable(
    reseau: ReseauPolitiqueValeur,
    observation: Sequence[float],
    actions_legales: Sequence[int],
) -> int:
    """La variante deterministe : l'action la plus probable, departage par plus petit indice.

    **Biaisee, et rapportee a cote de la mesure de reference, jamais a sa place** -- exactement
    le statut de `greedy.choisir_par_plus_petit_indice`. L'indice d'une action de pose encode
    l'assignation, la position au banquet et l'adversaire vise, donc une preference stable pour
    le petit indice fabriquerait un artefact directement dans B2, B3 et B6.
    """
    with torch.no_grad():
        entree = torch.tensor([list(observation)], dtype=torch.float32)
        logits, _ = reseau(entree.to(next(reseau.parameters()).device))
        loi = probabilites(logits.cpu(), masque([list(actions_legales)], reseau.nb_actions))
    return int(torch.argmax(loi[0]).item())


__all__ = [
    "ReseauPolitiqueValeur",
    "choisir",
    "choisir_le_plus_probable",
    "masque",
    "probabilites",
    "tirer",
]

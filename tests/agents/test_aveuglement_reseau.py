"""Les trois preuves que l'agent entraine ne lit pas la vue de dieu.

**Ecrites AVANT l'entrainement**, etape 3 du protocole. Un agent se teste comme le greedy s'est
teste, et le greedy a place la barre : trois niveaux, chacun assorti d'un cas qui verifie que le
piege MORD.

Ce qui change par rapport au greedy, et ce qui ne change pas
-------------------------------------------------------------
Le greedy decide a partir d'une `Perception` -- un objet riche dont chaque champ a du etre
justifie. Le reseau decide a partir d'un **`Sequence[float]` et d'un `Sequence[int]`** : sa
frontiere est d'un cran plus serree, parce qu'une suite de flottants ne porte aucune methode,
aucun `State`, aucune reference.

Cette frontiere plus serree ne dispense d'aucune des trois preuves, et c'est le point :

- **P1** dit que le module de decision ne *nomme* aucun acces a l'etat. Elle ne voit pas une
  fuite qui passerait par un intermediaire -- ici, par le tenseur lui-meme.
- **P2** dit qu'il ne *lit* pas la vue de dieu pendant qu'il decide. Elle ne voit pas une fuite
  deja recopiee dans l'observation.
- **P3** dit que sa decision ne *depend* pas de ce qu'il n'a pas le droit de savoir. C'est la
  seule qui couvre une fuite indirecte, et donc la seule qui couvre le cas qui compte ici :
  **si `tenseur` fuitait, P1 et P2 passeraient toutes les deux.**

P3 est donc, pour un agent qui observe par le tenseur, **plus** importante que pour le greedy.

Une difference de nature avec le greedy, qu'il faut lire
---------------------------------------------------------
Le greedy est deterministe a departage pres : deux appels sur la meme perception avec le meme
`Random` rendent la meme action. Le reseau **echantillonne**. P3 compare donc deux appels avec
un `Random` reinitialise a la meme graine -- ce qui teste bien l'invariance de la **loi**, et
pas seulement celle d'un tirage : a graine egale, `reseau.tirer` parcourt la meme fonction de
repartition, donc une loi differente donnerait presque toujours un indice different.

**Et ce « presque » est verifie**, pas suppose : `test_p3_le_tirage_a_graine_egale_separe_bien_
deux_lois_differentes` construit deux lois voisines et exige que le tirage les distingue.

Le reseau teste ici n'est pas entraine
---------------------------------------
**C'est deliberé, et c'est plus severe.** Un reseau a l'initialisation orthogonale de gain 0,01
a une politique quasi uniforme : ses logits sont petits, donc une perturbation de l'entree se
propage en une perturbation *relative* plus grande de la loi qu'elle ne le ferait sur un reseau
pique. Si l'invariance tient ici, elle tient a plus forte raison sur un reseau entraine -- et
elle est **rejouee sur le reseau entraine** en fin de phase, par le meme code.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest
import torch

from agents import reseau as reseau_module
from courtisans.cards import ROLES_CACHES, Carte
from courtisans.engine import Engine, State
from courtisans.infoset import tenseur
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J

#: Ce qu'un module de decision n'a pas le droit de nommer. **La meme liste que pour le
#: greedy**, importee plutot que recopiee : deux listes finiraient par ne plus etre d'accord,
#: et c'est la copie la plus courte qui deviendrait la vraie.
from tests.agents.test_aveuglement import ACCES_INTERDITS  # noqa: E402


def _reseau() -> reseau_module.ReseauPolitiqueValeur:
    """Un reseau non entraine, **de forme mesuree sur le moteur** et non ecrite en dur."""
    torch.manual_seed(0)
    etat = Engine(CONFIG).reset(0)
    return reseau_module.ReseauPolitiqueValeur(
        taille_observation=len(tenseur(etat, 0)), nb_actions=6 * 2 * (CONFIG.joueurs - 1)
    )


# ---------------------------------------------------------------------------------
# P1 -- structurelle
# ---------------------------------------------------------------------------------


def test_p1_le_module_de_decision_ne_nomme_aucun_acces_a_l_etat():
    """Le texte de `agents/reseau.py` ne contient aucun des acces interdits.

    Un test de texte est faible en general ; ici il est exactement adapte, parce que la faute
    qu'il cherche est un **retour en arriere** : quelqu'un qui rebrancherait la decision sur le
    `State` pour « aller plus vite » ecrirait l'un de ces noms.
    """
    source = Path("agents/reseau.py").read_text(encoding="utf-8")
    # La docstring cite `vue_privilegiee`, `scores` et `returns` pour dire qu'ils sont
    # interdits : on ne cherche donc que dans le CODE, docstrings et commentaires retires.
    code = _code_seul(source)
    trouves = [nom for nom in ACCES_INTERDITS if nom in code]
    assert not trouves, f"`agents/reseau.py` nomme des acces interdits : {trouves}"


def _code_seul(source: str) -> str:
    """Le source prive de ses docstrings et de ses commentaires.

    Ecrit parce que la docstring du module **doit** pouvoir nommer ce qu'elle interdit. Un test
    qui interdirait le mot partout obligerait a ne pas documenter la regle, ce qui est la
    mauvaise incitation.
    """
    import ast
    import io
    import tokenize

    arbre = ast.parse(source)
    docstrings = set()
    for nœud in ast.walk(arbre):
        if isinstance(nœud, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            texte = ast.get_docstring(nœud, clean=False)
            if texte is not None:
                docstrings.add(texte)
    morceaux = []
    for jeton in tokenize.generate_tokens(io.StringIO(source).readline):
        if jeton.type == tokenize.COMMENT:
            continue
        if jeton.type == tokenize.STRING and jeton.string.strip("\"'") in docstrings:
            continue
        morceaux.append(jeton.string)
    return " ".join(morceaux)


def test_p1_le_module_de_decision_n_importe_pas_le_moteur_d_etat():
    """`agents/reseau.py` n'importe ni `courtisans.engine` ni `agents.perception`.

    Il n'importe **rien** de `courtisans` : sa seule entree est une suite de flottants.
    """
    import ast

    arbre = ast.parse(Path("agents/reseau.py").read_text(encoding="utf-8"))
    importes = set()
    for nœud in ast.walk(arbre):
        if isinstance(nœud, ast.Import):
            importes.update(alias.name for alias in nœud.names)
        elif isinstance(nœud, ast.ImportFrom) and nœud.module:
            importes.add(nœud.module)
    fautifs = [nom for nom in importes if nom.startswith(("courtisans", "agents.perception"))]
    assert not fautifs, (
        f"le module de decision importe {fautifs} : sa frontiere n'est plus sa signature"
    )


def test_p1_la_signature_de_choisir_ne_prend_ni_etat_ni_perception():
    """`choisir(reseau, observation, actions_legales, alea)` : rien ne peut porter un `State`.

    Le controle porte sur les **annotations evaluees**, pas sur du texte : `from __future__
    import annotations` rend les annotations sous forme de chaines, et comparer du texte
    laisserait passer un alias.
    """
    import inspect
    from collections.abc import Sequence

    parametres = list(inspect.signature(reseau_module.choisir).parameters)
    assert parametres == ["reseau", "observation", "actions_legales", "alea"]

    annotations = inspect.get_annotations(reseau_module.choisir, eval_str=True)
    assert annotations["observation"] == Sequence[float]
    assert annotations["actions_legales"] == Sequence[int]
    assert annotations["alea"] is random.Random
    assert annotations["reseau"] is reseau_module.ReseauPolitiqueValeur


def test_p1_le_reseau_ne_recoit_qu_un_tenseur_de_flottants():
    """`ReseauPolitiqueValeur.forward` prend un `torch.Tensor` et rien d'autre.

    Un `nn.Module` qui accepterait un objet du moteur pourrait le lire. Celui-ci refuse tout ce
    qui n'a pas la bonne forme, et le cas le verifie en le lui donnant.
    """
    modele = _reseau()
    etat = Engine(CONFIG).reset(0)
    with pytest.raises((TypeError, AttributeError, ValueError)):
        modele(etat)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="attendu"):
        modele(torch.zeros(1, modele.taille_observation + 1))


# ---------------------------------------------------------------------------------
# P2 -- runtime
# ---------------------------------------------------------------------------------


def test_p2_une_partie_entiere_se_joue_avec_la_vue_de_dieu_piegee(monkeypatch):
    """Pendant `choisir`, `State.vue_privilegiee` leve. La partie doit aller au bout.

    Le piege est pose **apres** la construction de l'observation et retire avant la suivante,
    ce qui n'est possible que parce que `politique_reseau` construit le tenseur **entier**
    d'abord. Une observation paresseuse rendrait cette preuve vide.
    """
    modele = _reseau()
    vraie_vue = State.vue_privilegiee
    appels = {"decisions": 0}

    def vue_piegee(self):  # noqa: ANN001, ANN202 - signature imposee par le remplacement
        raise AssertionError(
            "l'agent a lu vue_privilegiee() pendant qu'il decidait : il triche"
        )

    alea = random.Random(7)

    def politique_sous_piege(etat: State) -> int:
        observation = tenseur(etat, etat.current_player())
        actions = etat.legal_actions()
        monkeypatch.setattr(State, "vue_privilegiee", vue_piegee)
        try:
            appels["decisions"] += 1
            return reseau_module.choisir(modele, observation, actions, alea)
        finally:
            monkeypatch.setattr(State, "vue_privilegiee", vraie_vue)

    etat = Engine(CONFIG).reset(0)
    while not etat.is_terminal():
        etat.apply(politique_sous_piege(etat))

    assert appels["decisions"] >= CONFIG.tours * CONFIG.joueurs
    assert etat.is_terminal()


def test_p2_le_piege_mord_si_on_le_teste_sur_lui_meme():
    """Un piege qui ne peut pas echouer ne prouve rien : on verifie qu'il attrape la faute."""
    etat = Engine(CONFIG).reset(0)
    vraie_vue = State.vue_privilegiee
    try:
        State.vue_privilegiee = lambda self: (_ for _ in ()).throw(  # noqa: ARG005
            AssertionError("piege")
        )
        with pytest.raises(AssertionError, match="piege"):
            etat.vue_privilegiee()
    finally:
        State.vue_privilegiee = vraie_vue
    assert etat.vue_privilegiee().posees == ()


def test_p2_le_piege_mordrait_un_agent_qui_tricherait():
    """La contre-epreuve : un decideur qui LIT la vue de dieu doit etre attrape.

    Sans ce cas, P2 passerait aussi bien si le piege etait pose au mauvais moment -- par
    exemple apres la decision. On fabrique un tricheur et on exige que le piege le morde
    **au meme endroit du code** que celui ou l'agent decide.
    """
    vraie_vue = State.vue_privilegiee
    etat = Engine(CONFIG).reset(0)

    def tricheur(etat_courant: State) -> int:
        etat_courant.vue_privilegiee()  # ce que l'agent ne fait pas
        return etat_courant.legal_actions()[0]

    try:
        State.vue_privilegiee = lambda self: (_ for _ in ()).throw(  # noqa: ARG005
            AssertionError("l'agent a lu vue_privilegiee()")
        )
        with pytest.raises(AssertionError, match="a lu vue_privilegiee"):
            tricheur(etat)
    finally:
        State.vue_privilegiee = vraie_vue


# ---------------------------------------------------------------------------------
# P3 -- invariance : la preuve forte, et la SEULE qui couvre une fuite par le tenseur
# ---------------------------------------------------------------------------------
#
# Les trois brouilleurs sont importes de `tests/agents/test_aveuglement.py` plutot que
# recopies. La note de sa premiere version vaut ici mot pour mot : on permute les CARTES entre
# les emplacements, on ne reassigne pas leur famille -- sinon on fabrique des plateaux
# IMPOSSIBLES, portant deux fois la meme carte, et c'est l'instrument qui est faux, pas l'agent.


def _permuter_espions_adverses(etat: State, joueur: int, alea: random.Random) -> None:
    """Echange l'identite des Espions adverses poses. Le public ne bouge pas, la verite si."""
    dos = [
        indice
        for indice, posee in enumerate(etat._posees)  # noqa: SLF001 - le test triche, pas l'agent
        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur
    ]
    if len(dos) < 2:
        return
    cartes = [etat._posees[indice].carte for indice in dos]  # noqa: SLF001
    alea.shuffle(cartes)
    for indice, carte in zip(dos, cartes, strict=True):
        posee = etat._posees[indice]  # noqa: SLF001
        etat._posees[indice] = type(posee)(carte, posee.zone, posee.poseur)  # noqa: SLF001


def _permuter_la_pioche(etat: State, alea: random.Random) -> None:
    """Melange les cartes jamais piochees. Personne ne les verra jamais (paragraphe 3.4)."""
    alea.shuffle(etat._pioche)  # noqa: SLF001


def _permuter_les_mains_adverses(etat: State, joueur: int, alea: random.Random) -> None:
    """Melange les cartes entre les mains adverses, en gardant leur taille."""
    autres = [siege for siege in range(etat.config.joueurs) if siege != joueur]
    ensemble: list[Carte] = []
    for siege in autres:
        ensemble.extend(etat._mains[siege])  # noqa: SLF001
    if len(ensemble) < 2:
        return
    alea.shuffle(ensemble)
    for siege in autres:
        taille = len(etat._mains[siege])  # noqa: SLF001
        etat._mains[siege] = ensemble[:taille]  # noqa: SLF001
        del ensemble[:taille]


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 6, 7])
def test_p3_la_decision_ne_depend_d_aucune_information_cachee(seed: int):
    """Sur chaque nœud, on perturbe le cache et on exige **le meme tenseur et la meme action**.

    Deux assertions, et elles ne disent pas la meme chose. Que le **tenseur** ne bouge pas est
    la propriete de l'encodage, celle que l'invariant I7 protege ; que l'**action** ne bouge pas
    est la propriete de l'agent. Si un jour l'encodage fuitait, la premiere tomberait et
    nommerait la cause, la seconde ne ferait que constater.
    """
    modele = _reseau()
    etat = Engine(CONFIG).reset(seed)
    noeuds = 0
    while not etat.is_terminal():
        joueur = etat.current_player()
        observation = tenseur(etat, joueur)
        actions = etat.legal_actions()
        action = reseau_module.choisir(modele, observation, actions, random.Random(1234))

        perturbe = etat.clone()
        brouilleur = random.Random(9_000 + seed + noeuds)
        _permuter_espions_adverses(perturbe, joueur, brouilleur)
        _permuter_la_pioche(perturbe, brouilleur)
        _permuter_les_mains_adverses(perturbe, joueur, brouilleur)

        observation_perturbee = tenseur(perturbe, joueur)
        assert observation_perturbee == observation, (
            f"seed {seed}, nœud {noeuds} : le TENSEUR a bouge sous une perturbation invisible "
            f"du decideur. C'est l'encodage qui fuite, pas l'agent."
        )
        assert perturbe.legal_actions() == actions

        assert (
            reseau_module.choisir(
                modele, observation_perturbee, perturbe.legal_actions(), random.Random(1234)
            )
            == action
        ), f"seed {seed}, nœud {noeuds} : la decision a change"
        noeuds += 1
        etat.apply(action)

    assert noeuds > CONFIG.tours * CONFIG.joueurs


def test_p3_le_brouilleur_change_vraiment_la_verite():
    """Une preuve d'invariance ne vaut rien si la perturbation ne perturbe rien."""
    trouve = False
    for seed in range(8):
        etat = Engine(CONFIG).reset(seed)
        noeuds = 0
        while not etat.is_terminal() and not trouve:
            joueur = etat.current_player()
            perturbe = etat.clone()
            brouilleur = random.Random(9_000 + seed + noeuds)
            _permuter_espions_adverses(perturbe, joueur, brouilleur)
            _permuter_la_pioche(perturbe, brouilleur)
            _permuter_les_mains_adverses(perturbe, joueur, brouilleur)
            if perturbe.vue_privilegiee() != etat.vue_privilegiee():
                trouve = True
            noeuds += 1
            etat.apply(etat.legal_actions()[0])
    assert trouve, "le brouilleur n'a jamais rien change : P3 ne testerait rien"


def test_p3_le_tirage_a_graine_egale_separe_bien_deux_lois_differentes():
    """Le « presque toujours » de la docstring du module, verifie plutot que suppose.

    P3 compare deux tirages a graine egale. Ca ne prouve l'invariance de la **loi** que si un
    tirage a graine egale distingue reellement deux lois voisines. On le verifie sur des lois
    qui different d'un centieme, et on exige que la difference se voie sur une large majorite
    des graines.
    """
    loi_a = [0.25, 0.25, 0.25, 0.25]
    loi_b = [0.26, 0.25, 0.25, 0.24]
    differents = sum(
        reseau_module.tirer(loi_a, random.Random(graine))
        != reseau_module.tirer(loi_b, random.Random(graine))
        for graine in range(2000)
    )
    # Deux lois qui different de 0,01 sur deux composantes se separent sur environ 1 % des
    # graines : le tirage EST sensible a la loi, et il l'est proportionnellement a l'ecart.
    assert differents > 0, (
        "aucune graine ne separe deux lois differentes : le tirage ignore la loi, et P3 ne "
        "testerait rien du tout"
    )
    # Et le controle inverse : la meme loi donne toujours le meme tirage a graine egale.
    assert all(
        reseau_module.tirer(loi_a, random.Random(graine))
        == reseau_module.tirer(loi_a, random.Random(graine))
        for graine in range(200)
    )


# ---------------------------------------------------------------------------------
# Les memes preuves, rejouees sur le reseau ENTRAINE
#
# La docstring de ce module promet que l'invariance « est rejouee sur le reseau entraine en
# fin de phase, par le meme code ». **Une promesse sans code n'est pas une preuve** : ces cas
# la tiennent.
#
# Pourquoi ca ne va pas de soi. Les cas au-dessus tournent sur un reseau a l'initialisation,
# dont la politique est quasi uniforme -- etendue relative mesuree a 0,1452 au plus. Un reseau
# entraine est **pique** : ses logits sont grands, donc une meme perturbation de l'entree
# deplace la loi bien plus, et un tirage a graine egale la separe bien plus facilement.
# L'invariance y est donc **plus difficile a tenir**, pas moins.
#
# Ils SAUTENT si `models/phase3/final.pt` n'existe pas -- le fichier est ignore par git, et un
# depot fraichement clone n'en a pas. Le saut est bruyant : il nomme le fichier manquant et la
# commande qui le produit, plutot que de laisser croire que la preuve a ete faite.
# ---------------------------------------------------------------------------------

CHEMIN_AGENT_ENTRAINE = Path("models/phase3/final.pt")


def _agent_entraine() -> reseau_module.ReseauPolitiqueValeur:
    """Le reseau entraine, ou un saut bruyant qui nomme ce qui manque."""
    if not CHEMIN_AGENT_ENTRAINE.exists():
        pytest.skip(
            f"{CHEMIN_AGENT_ENTRAINE} absent -- les preuves d'aveuglement n'ont PAS ete "
            f"rejouees sur le reseau entraine. Le produire par "
            f"`uv run python -m agents.campagne --dossier models/phase3`."
        )
    from agents.politique_reseau import charger

    etat = Engine(CONFIG).reset(0)
    return charger(
        str(CHEMIN_AGENT_ENTRAINE),
        taille_observation=len(tenseur(etat, 0)),
        nb_actions=6 * 2 * (CONFIG.joueurs - 1),
    )


def test_l_agent_entraine_est_bien_PIQUE_donc_le_cas_suivant_est_plus_severe():
    """Le fondement de la severite, verifie avant d'en tirer parti.

    Si le reseau entraine etait reste quasi uniforme, rejouer P3 dessus ne serait pas plus
    severe que sur un reseau neuf, et l'affirmation de la docstring serait fausse. Le cas
    mesure l'etendue relative de sa politique et exige qu'elle depasse largement celle d'un
    reseau a l'initialisation -- 0,1452 au plus, MESURE sur 10 graines x 20 etats.
    """
    modele = _agent_entraine()
    # Une position avancee de huit coups, pour que le plateau porte des dos et que la
    # politique ait de quoi discriminer. Un etat initial serait le cas le plus favorable.
    etat = Engine(CONFIG).reset(0)
    alea = random.Random(50_000)
    for _ in range(8):
        etat.apply(alea.choice(etat.legal_actions()))
    legales = etat.legal_actions()
    with torch.no_grad():
        logits, _ = modele(
            torch.tensor([tenseur(etat, etat.current_player())], dtype=torch.float32)
        )
    loi = reseau_module.probabilites(
        logits, reseau_module.masque([legales], modele.nb_actions)
    )
    valeurs = [loi[0, a].item() for a in legales]
    etendue = (max(valeurs) - min(valeurs)) * len(legales)
    assert etendue > 0.30, (
        f"l'agent entraine a une politique d'etendue relative {etendue:.4f}, du meme ordre "
        f"qu'un reseau neuf : rejouer P3 dessus n'est pas plus severe, et la docstring de ce "
        f"module doit etre relue avant d'etre crue."
    )


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5, 6, 7])
def test_p3_sur_l_agent_ENTRAINE(seed: int):
    """P3, mot pour mot, sur le reseau qui a ete mesure. C'est celui-la qui compte."""
    modele = _agent_entraine()
    etat = Engine(CONFIG).reset(seed)
    noeuds = 0
    while not etat.is_terminal():
        joueur = etat.current_player()
        observation = tenseur(etat, joueur)
        actions = etat.legal_actions()
        action = reseau_module.choisir(modele, observation, actions, random.Random(1234))

        perturbe = etat.clone()
        brouilleur = random.Random(9_000 + seed + noeuds)
        _permuter_espions_adverses(perturbe, joueur, brouilleur)
        _permuter_la_pioche(perturbe, brouilleur)
        _permuter_les_mains_adverses(perturbe, joueur, brouilleur)

        observation_perturbee = tenseur(perturbe, joueur)
        assert observation_perturbee == observation, (
            f"seed {seed}, nœud {noeuds} : le TENSEUR a bouge sous une perturbation invisible "
            f"du decideur. C'est l'encodage qui fuite, pas l'agent."
        )
        assert (
            reseau_module.choisir(
                modele, observation_perturbee, perturbe.legal_actions(), random.Random(1234)
            )
            == action
        ), f"seed {seed}, nœud {noeuds} : la decision de l'agent ENTRAINE a change"
        noeuds += 1
        etat.apply(action)
    assert noeuds > CONFIG.tours * CONFIG.joueurs


def test_p2_sur_l_agent_ENTRAINE(monkeypatch):
    """P2, mot pour mot, sur le reseau qui a ete mesure."""
    modele = _agent_entraine()
    vraie_vue = State.vue_privilegiee
    appels = {"decisions": 0}

    def vue_piegee(self):  # noqa: ANN001, ANN202 - signature imposee par le remplacement
        raise AssertionError("l'agent entraine a lu vue_privilegiee() en decidant : il triche")

    alea = random.Random(7)
    etat = Engine(CONFIG).reset(0)
    while not etat.is_terminal():
        observation = tenseur(etat, etat.current_player())
        actions = etat.legal_actions()
        monkeypatch.setattr(State, "vue_privilegiee", vue_piegee)
        try:
            appels["decisions"] += 1
            action = reseau_module.choisir(modele, observation, actions, alea)
        finally:
            monkeypatch.setattr(State, "vue_privilegiee", vraie_vue)
        etat.apply(action)
    assert appels["decisions"] >= CONFIG.tours * CONFIG.joueurs

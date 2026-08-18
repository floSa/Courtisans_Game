"""Les trois preuves que le greedy ne lit pas la vue de dieu.

C'est le point sur lequel la consigne de la phase 2 est la plus exigeante : « un AGENT ne voit
jamais `vue_privilegiee()`. Le greedy que tu ecris est un agent : s'il lit la vue de dieu, il
triche, et son winrate ne veut rien dire. »

Trois preuves, et elles ne disent pas la meme chose.

**P1, structurelle.** Le module de decision ne *mentionne* aucun acces a l'etat. Elle ne peut
pas voir une fuite qui passerait par un intermediaire.

**P2, runtime.** Il ne *lit* pas la vue de dieu pendant qu'il decide. Elle ne peut pas voir une
fuite deja recopiee dans la `Perception`.

**P3, invariance.** Sa decision ne *depend* pas de ce qu'il n'a pas le droit de savoir. Elle
couvre ce que les deux autres laissent passer.

P3 est la seule qui couvre une fuite indirecte : P1 et P2 disent qu'il ne regarde pas, P3 dit
que ce qu'il rend n'en depend pas. Les trois sont gardees parce qu'elles echouent a des
endroits differents, et parce que P1 et P2 nomment la cause quand P3 ne fait que constater.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from courtisans.cards import ROLES_CACHES, Carte
from courtisans.engine import Engine, Phase, State
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J

#: Ce qu'un module de decision n'a pas le droit de nommer. `scores` et `returns` sont dedans :
#: ils comptent les Espions adverses, donc les lire fuiterait ce que l'invariant I7 protege.
ACCES_INTERDITS = (
    "vue_privilegiee",
    "_pioche",
    "_mains",
    "_posees",
    "_defausse",
    "cibles_courantes",
    "scores",
    "returns",
    "chance_outcomes",
)


# ---------------------------------------------------------------------------------
# P1 -- structurelle
# ---------------------------------------------------------------------------------


def test_p1_le_module_de_decision_ne_nomme_aucun_acces_a_l_etat():
    """Le texte de `agents/greedy.py` ne contient aucun des acces interdits.

    Un test de texte est faible en general ; ici il est exactement adapte, parce que la faute
    qu'il cherche est un **retour en arriere** : quelqu'un qui rebrancherait le greedy sur le
    `State` pour aller plus vite. Il nomme la cause, ce que P3 ne sait pas faire.
    """
    source = Path("agents/greedy.py").read_text(encoding="utf-8")
    corps = "\n".join(
        ligne for ligne in source.splitlines() if not ligne.lstrip().startswith("#")
    )
    # La docstring du module cite `vue_privilegiee` pour dire qu'il ne la lit pas. On coupe
    # l'en-tete au premier `import`, ce qui laisse tout le code et aucune prose.
    code = corps[corps.index("from __future__") :]
    for interdit in ACCES_INTERDITS:
        assert interdit not in code, f"`{interdit}` apparait dans le code de agents/greedy.py"


def test_p1_le_module_de_decision_n_importe_pas_le_moteur_d_etat():
    """`greedy.py` importe `rules`, `cards`, `config` -- jamais `Engine` ni `State`.

    `Phase` est un enum de phase, sans acces a rien : il est autorise, et l'assertion le dit
    explicitement pour qu'un lecteur ne prenne pas son absence de la liste pour un oubli.
    """
    code = Path("agents/greedy.py").read_text(encoding="utf-8")
    assert "import Engine" not in code
    assert "import State" not in code
    assert "from courtisans.engine import Phase" in code


def test_p1_la_signature_de_choisir_ne_prend_pas_d_etat():
    """`choisir(perception, alea)` : rien dans sa signature ne peut porter un `State`."""
    import inspect

    from agents.greedy import choisir

    parametres = list(inspect.signature(choisir).parameters)
    assert parametres == ["perception", "alea"]
    # `eval_str=True` est indispensable : `from __future__ import annotations` rend les
    # annotations sous forme de chaines, et sans evaluation le test comparerait du texte.
    annotations = inspect.get_annotations(choisir, eval_str=True)
    assert annotations["perception"].__name__ == "Perception"


# ---------------------------------------------------------------------------------
# P2 -- runtime
# ---------------------------------------------------------------------------------


def test_p2_une_partie_entiere_se_joue_avec_la_vue_de_dieu_piegee(monkeypatch):
    """Pendant `choisir`, `State.vue_privilegiee` leve. La partie doit aller au bout.

    Le piege est pose **apres** `percevoir` et retire avant, ce qui est possible parce que
    `politique_greedy` construit la perception entiere d'abord. Une perception paresseuse
    rendrait cette preuve vide -- c'est pourquoi `percevoir` ne rend rien de differe.
    """
    from agents import greedy
    from agents.perception import percevoir

    appels = {"decisions": 0}
    vraie_vue = State.vue_privilegiee

    def vue_piegee(self):  # noqa: ANN001, ANN202 - signature imposee par le remplacement
        raise AssertionError(
            "le greedy a lu vue_privilegiee() pendant qu'il decidait : il triche"
        )

    def politique_sous_piege(etat: State) -> int:
        perception = percevoir(etat, etat.current_player())
        monkeypatch.setattr(State, "vue_privilegiee", vue_piegee)
        try:
            appels["decisions"] += 1
            return greedy.choisir(perception, alea)
        finally:
            monkeypatch.setattr(State, "vue_privilegiee", vraie_vue)

    alea = random.Random(7)
    etat = Engine(CONFIG).reset(0)
    while not etat.is_terminal():
        etat.apply(politique_sous_piege(etat))

    assert appels["decisions"] >= CONFIG.tours * CONFIG.joueurs
    assert etat.is_terminal()


def test_p2_le_piege_mord_si_on_le_teste_sur_lui_meme():
    """Un piege qui ne peut pas echouer ne prouve rien : on verifie qu'il attrape la faute.

    Le meme piege, mais on lit deliberement la vue de dieu -- il doit lever. Sans ce cas, P2
    passerait aussi bien si `monkeypatch` ne remplacait rien.
    """
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


# ---------------------------------------------------------------------------------
# P3 -- invariance : la preuve forte
# ---------------------------------------------------------------------------------


def _permuter_espions_adverses(etat: State, joueur: int, alea: random.Random) -> None:
    """Echange l'identite des Espions adverses deja poses, sans changer ce qui est public.

    Un dos reste un dos, dans la meme zone, pose par le meme joueur : la vue publique et la
    vue du decideur sont **inchangees**. Seule la verite change. Une decision qui bougerait
    dependrait d'une information que le decideur n'a pas.

    **On permute les CARTES entre les emplacements**, on ne reassigne pas leur famille. La
    premiere version faisait le second, et fabriquait des plateaux **impossibles** : donner la
    famille 1 a un dos de famille 2 pouvait recreer une carte deja posee ailleurs, donc un
    doublon. P3 echouait alors sur un etat qu'aucune partie legale ne produit -- l'instrument
    etait faux, pas l'agent. Permuter les identites entre elles conserve exactement le
    multi-ensemble du paquet.
    """
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
    """Melange les cartes entre les mains adverses, en gardant leur taille.

    La main du decideur n'est pas touchee. Les tailles restent celles du moteur, sinon on
    fabriquerait un etat que les regles interdisent au lieu d'un etat legal different.
    """
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
    """Sur chaque noeud d'une partie, on perturbe le cache et on exige la meme action.

    Trois perturbations a la fois : l'identite des Espions adverses poses, l'ordre des cartes
    jamais piochees, et le contenu des mains adverses. Chacune laisse la `Perception` du
    decideur identique ; une decision qui changerait dependrait de ce qu'il n'a pas le droit
    de savoir.

    **La perturbation est appliquee sur un clone**, et c'est le clone qu'on interroge : la
    partie de reference continue intacte, donc on parcourt bien la trajectoire reelle et pas
    une trajectoire deviee par le test.
    """
    from agents import greedy
    from agents.perception import percevoir

    etat = Engine(CONFIG).reset(seed)
    noeuds = 0
    while not etat.is_terminal():
        joueur = etat.current_player()
        reference = percevoir(etat, joueur)
        action = greedy.choisir(reference, random.Random(1234))

        perturbe = etat.clone()
        brouilleur = random.Random(9_000 + seed + noeuds)
        _permuter_espions_adverses(perturbe, joueur, brouilleur)
        _permuter_la_pioche(perturbe, brouilleur)
        _permuter_les_mains_adverses(perturbe, joueur, brouilleur)

        vue_perturbee = percevoir(perturbe, joueur)
        assert vue_perturbee.connues == reference.connues
        assert vue_perturbee.main == reference.main
        assert vue_perturbee.actions_legales == reference.actions_legales
        assert vue_perturbee.cibles == reference.cibles

        assert greedy.choisir(vue_perturbee, random.Random(1234)) == action, (
            f"seed {seed}, noeud {noeuds} : la decision a change sous une perturbation "
            f"invisible du decideur"
        )
        noeuds += 1
        etat.apply(action)

    assert noeuds > CONFIG.tours * CONFIG.joueurs


def test_p3_le_brouilleur_change_vraiment_la_verite():
    """Une preuve d'invariance ne vaut rien si la perturbation ne perturbe rien.

    On cherche, sur les seeds de P3, un noeud ou le brouilleur modifie effectivement la vue
    de dieu. S'il n'en existait aucun, P3 passerait en ne testant rien.
    """
    from agents.perception import percevoir

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
            etat.apply(percevoir(etat, joueur).actions_legales[0])
    assert trouve, "le brouilleur n'a jamais rien change : P3 ne testerait rien"


# ---------------------------------------------------------------------------------
# Integration : le greedy joue de vraies parties, legalement
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_le_greedy_joue_une_partie_entiere_et_legale(seed: int):
    """Chaque action rendue est legale, et la partie se termine avec les bons comptes."""
    from agents.politique import politique_greedy

    politique = politique_greedy(random.Random(5_000 + seed))
    etat = Engine(CONFIG).reset(seed)
    poses = [0] * CONFIG.joueurs
    while not etat.is_terminal():
        if etat.phase() is Phase.POSE:
            poses[etat.current_player()] += 1
        action = politique(etat)
        assert action in etat.legal_actions()
        etat.apply(action)

    assert poses == [CONFIG.tours] * CONFIG.joueurs
    assert sum(etat.returns()) == pytest.approx(0.0, abs=1e-12)


def test_le_greedy_deterministe_joue_aussi_une_partie_entiere():
    """La variante de robustesse doit rester jouable, sinon on ne peut pas la rapporter."""
    from agents.politique import politique_greedy_deterministe

    politique = politique_greedy_deterministe()
    etat = Engine(CONFIG).reset(3)
    while not etat.is_terminal():
        action = politique(etat)
        assert action in etat.legal_actions()
        etat.apply(action)
    assert etat.is_terminal()


def test_les_deux_departages_ne_donnent_pas_la_meme_partie():
    """Si les deux variantes coincidaient, rapporter la seconde ne dirait rien.

    Elles doivent differer sur au moins une des parties, sinon le report de `M3(deterministe)`
    est un doublon et il faut le retirer plutot que de le publier.
    """
    from agents.politique import politique_greedy, politique_greedy_deterministe

    differe = False
    for seed in range(8):
        aleatoire = politique_greedy(random.Random(5_000 + seed))
        deterministe = politique_greedy_deterministe()
        etat_a = Engine(CONFIG).reset(seed)
        etat_b = Engine(CONFIG).reset(seed)
        while not etat_a.is_terminal():
            etat_a.apply(aleatoire(etat_a))
            etat_b.apply(deterministe(etat_b))
        if etat_a.scores() != etat_b.scores():
            differe = True
            break
    assert differe

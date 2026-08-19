"""Controles hostiles sur MES sept compteurs : les zeros exacts et le denominateur vide.

Un compteur de comportement se juge sur ce qu'il refuse de compter. Chaque cas ci-dessous
construit une situation ou la reponse est **exactement** zero -- pas « peu » -- ou bien ou
la question ne se pose pas du tout.
"""

from __future__ import annotations

import random

import pytest

from audit.phase2 import comportements as B
from audit.phase2.greedy import Aleatoire, Greedy
from audit.phase2.trace import EvenementCiblage, EvenementPose, Trace, jouer
from courtisans.cards import Carte, Position, Role
from courtisans.engine import Engine
from tests.audit_phase2.outils import INSTANCE, SANS_ASSASSIN, banquet, domaine

LUMIERE, INDIFFERENTE, OBSCURITE = 1, 0, -1


def _pose(
    index: int,
    joueur: int,
    *,
    famille_banquet: int,
    position: Position,
    famille_adverse: int,
    d_avant: dict[int, int] | None = None,
    expose: frozenset[int] = frozenset(),
    imprenables: frozenset[int] = frozenset(),
    dos: int = 0,
    d_visible: dict[int, int] | None = None,
) -> EvenementPose:
    """Un evenement de pose fabrique de toutes pieces, pour isoler un compteur."""
    reel = d_avant or dict.fromkeys(range(4), 0)
    return EvenementPose(
        index=index,
        tour=index // 3,
        joueur=joueur,
        destinataire=(joueur + 1) % 3,
        banquet=banquet(Carte(famille_banquet, Role.NEUTRE, 0), position, joueur),
        propre=domaine(Carte(0, Role.GARDE, 0), joueur, joueur),
        adverse=domaine(Carte(famille_adverse, Role.NEUTRE, 1), (joueur + 1) % 3, joueur),
        d_avant=reel,
        d_visible_avant=d_visible or reel,
        dos_adverses_banquet=dos,
        expose_avant=expose,
        expose_visible_avant=expose,
        imprenables_avant=imprenables,
    )


def _trace(poses, ciblages=(), statuts=None) -> Trace:
    """Une trace fabriquee, dont l'issue est imposee."""
    trace = Trace(seed=0, config_familles=4, joueurs=3, tours=4)
    trace.poses = list(poses)
    trace.ciblages = list(ciblages)
    trace.statuts_finaux = statuts or dict.fromkeys(range(4), INDIFFERENTE)
    trace.scores_finaux = [0, 0, 0]
    trace.gains_finaux = [0.0, 0.0, 0.0]
    return trace


# ---------------------------------------------------------------------------------
# Le denominateur vide -- 0/0 n'est pas 0
# ---------------------------------------------------------------------------------


def test_un_taux_sur_un_denominateur_vide_n_a_pas_de_valeur():
    """`Taux.valeur` rend `None`, jamais `0.0`, et le rendu l'ecrit en toutes lettres."""
    vide = B.Taux("B4", "noeud de ciblage offrant au moins une cible", 0, 0)
    assert vide.valeur is None
    assert "NON DEFINI" in vide.texte()
    assert "0.00 %" not in vide.texte()


def test_sans_assassin_les_denominateurs_de_b2_et_b4_valent_exactement_zero():
    """Une instance sans Assassin ne rend pas « 0 % de refus » : elle ne rend rien.

    C'est le controle inverse de l'intuition : la question a poser n'est pas « le taux
    vaut-il zero », c'est « le denominateur est-il vide, et le code refuse-t-il alors de
    publier un taux ». Un `0 %` imprime ici serait un chiffre juste au bit pres decrivant
    autre chose que ce que sa phrase annonce.
    """
    engine = Engine(SANS_ASSASSIN)
    traces = [
        jouer(engine, seed, [Aleatoire(random.Random(seed * 3 + s)) for s in range(3)])
        for seed in range(40)
    ]
    assert sum(len(t.ciblages) for t in traces) == 0

    b4 = B.cumule([B.b4(t) for t in traces])
    assert b4.denominateur == 0
    assert b4.numerateur == 0
    assert b4.valeur is None

    for zone in B.b2_distribution(traces[0]):
        cumul = B.cumule([B.b2_distribution(t)[zone] for t in traces])
        assert cumul.denominateur == 0, zone
        assert cumul.valeur is None, zone

    assert B.cumule([B.b2_bascule(t) for t in traces]).valeur is None
    # Les compteurs qui ne dependent pas de l'Assassin, eux, restent definis.
    assert B.cumule([B.b1(t) for t in traces]).denominateur == 40 * 3 * SANS_ASSASSIN.tours


def test_un_intervalle_de_confiance_refuse_zero_observation():
    """Le meme principe, du cote des statistiques."""
    from audit.phase2.stats import clopper_pearson

    with pytest.raises(ValueError, match="zero observation"):
        clopper_pearson(0, 0)


# ---------------------------------------------------------------------------------
# B1 -- les zeros exacts, dont celui qui teste l'ordre du temps
# ---------------------------------------------------------------------------------


def test_b1_vaut_exactement_zero_sans_aucune_action_de_bascule():
    """Aucune pose en Disgrace, aucun meurtre : rien ne peut avoir ete bascule.

    Les familles finissent pourtant toutes hors Lumiere, donc la moitie du critere est
    satisfaite. Un compteur qui oublierait d'exiger l'action rendrait ici 100 %.
    """
    poses = [
        _pose(i, i % 3, famille_banquet=1, position=Position.ESTIME, famille_adverse=2)
        for i in range(12)
    ]
    trace = _trace(poses, statuts=dict.fromkeys(range(4), OBSCURITE))
    taux = B.b1(trace)
    assert taux.numerateur == 0
    assert taux.denominateur == 12


def test_b1_vaut_exactement_zero_quand_la_bascule_precede_le_don():
    """« Nourrir **puis** basculer ». Une bascule anterieure ne planifie rien.

    Le compteur voit le meme joueur, la meme famille, la meme issue finale : seul l'ordre
    des indices les separe. C'est exactement ce qu'un compteur ecrit sans horodatage --
    un ensemble de familles touchees, compare apres coup -- compterait a tort.
    """
    bascule_dabord = _pose(
        0, 0, famille_banquet=2, position=Position.DISGRACE, famille_adverse=1
    )
    don_ensuite = _pose(
        3, 0, famille_banquet=1, position=Position.ESTIME, famille_adverse=2
    )
    trace = _trace(
        [bascule_dabord, don_ensuite],
        statuts={0: LUMIERE, 1: LUMIERE, 2: OBSCURITE, 3: LUMIERE},
    )
    assert B.b1(trace).numerateur == 0

    # Le meme couple, l'ordre inverse : le motif est alors bien present.
    don_dabord = _pose(0, 0, famille_banquet=1, position=Position.ESTIME, famille_adverse=2)
    bascule_ensuite = _pose(
        3, 0, famille_banquet=2, position=Position.DISGRACE, famille_adverse=1
    )
    temoin = _trace(
        [don_dabord, bascule_ensuite],
        statuts={0: LUMIERE, 1: LUMIERE, 2: OBSCURITE, 3: LUMIERE},
    )
    assert B.b1(temoin).numerateur == 1


def test_b1_n_attribue_pas_a_un_joueur_la_bascule_d_un_autre():
    """Le donneur et le basculeur doivent etre le meme siege.

    Sans ce controle, B1 compterait la coincidence de deux joueurs differents -- ce qui
    est frequent a trois -- et le chiffre publie decrirait le hasard de la table.
    """
    don = _pose(0, 0, famille_banquet=1, position=Position.ESTIME, famille_adverse=2)
    bascule_par_un_autre = _pose(
        1, 1, famille_banquet=2, position=Position.DISGRACE, famille_adverse=3
    )
    trace = _trace(
        [don, bascule_par_un_autre],
        statuts={0: LUMIERE, 1: LUMIERE, 2: OBSCURITE, 3: LUMIERE},
    )
    # La pose de J1 chez J2 porte la famille 3, restee en Lumiere : elle ne compte pas
    # non plus. Le seul candidat est le don de J0, et sa bascule vient d'un autre siege.
    assert B.b1(trace).numerateur == 0


def test_b1_distingue_l_indifference_de_l_obscurite():
    """Le seuil du paragraphe 2.2 contre la lettre du paragraphe 7.2, chiffre.

    Une famille passee de Lumiere a Indifferente a annule le cadeau : ses cartes ne
    rapportent plus rien au receveur. La lecture stricte, `obscurite`, ne la compte pas.
    L'ecart entre les deux est ce que le choix de definition coute, et il se mesure.
    """
    don = _pose(0, 0, famille_banquet=1, position=Position.ESTIME, famille_adverse=2)
    bascule = _pose(3, 0, famille_banquet=2, position=Position.DISGRACE, famille_adverse=1)
    trace = _trace([don, bascule], statuts={0: 0, 1: LUMIERE, 2: INDIFFERENTE, 3: 0})
    assert B.b1(trace, seuil_final="hors_lumiere").numerateur == 1
    assert B.b1(trace, seuil_final="obscurite").numerateur == 0


# ---------------------------------------------------------------------------------
# B3 et B7 -- zeros exacts
# ---------------------------------------------------------------------------------


def test_b3_vaut_exactement_zero_quand_le_poseur_n_est_expose_sur_rien():
    """Aucune carte a soi dans son propre domaine : aucune alliance possible."""
    poses = [
        _pose(i, i % 3, famille_banquet=0, position=Position.ESTIME, famille_adverse=i % 4)
        for i in range(12)
    ]
    taux = B.b3(_trace(poses))
    assert taux.numerateur == 0
    assert taux.denominateur == 12


def test_b7_vaut_exactement_zero_quand_aucune_famille_n_est_imprenable():
    """Sans famille hors d'atteinte, aucune carte ne peut etre gaspillee a la defendre."""
    poses = [
        _pose(
            i,
            i % 3,
            famille_banquet=0,
            position=Position.ESTIME,
            famille_adverse=1,
            d_avant={0: 5, 1: 0, 2: 0, 3: 0},
        )
        for i in range(12)
    ]
    trace = _trace(poses)
    assert B.b7(trace).numerateur == 0
    assert B.occasions_b7(trace).numerateur == 0


def test_b7_ne_compte_pas_une_carte_qui_affaiblit_une_famille_imprenable():
    """Le sens compte : jouer **contre** une famille imprenable n'est pas la defendre.

    Un compteur qui ne testerait que l'appartenance a la famille rendrait ici 12 sur 12.
    """
    poses = [
        _pose(
            i,
            i % 3,
            famille_banquet=0,
            position=Position.DISGRACE,
            famille_adverse=1,
            d_avant={0: 5, 1: 0, 2: 0, 3: 0},
            imprenables=frozenset({0}),
        )
        for i in range(12)
    ]
    trace = _trace(poses)
    assert B.b7(trace).numerateur == 0
    assert B.occasions_b7(trace).numerateur == 12  # l'occasion existait pourtant

    renforts = [
        _pose(
            i,
            i % 3,
            famille_banquet=0,
            position=Position.ESTIME,
            famille_adverse=1,
            d_avant={0: 5, 1: 0, 2: 0, 3: 0},
            imprenables=frozenset({0}),
        )
        for i in range(12)
    ]
    assert B.b7(_trace(renforts)).numerateur == 12


# ---------------------------------------------------------------------------------
# B2 et B4 -- ce que la structure des regles impose
# ---------------------------------------------------------------------------------


def test_un_assassin_de_domaine_ne_peut_jamais_faire_basculer_une_famille():
    """Seules les cartes du banquet portent le statut (paragraphe 5) : B2.bascule = 0.

    Propriete des regles, pas artefact de mesure. Un compteur qui rendrait autre chose
    lirait les domaines dans le calcul d'influence -- la faute la plus couteuse possible
    sur ce jeu.
    """
    assassin = domaine(Carte(1, Role.ASSASSIN, 0), 0, 0)
    cibles = (
        domaine(Carte(0, Role.NOBLE, 0), 0, 1),
        domaine(Carte(2, Role.NEUTRE, 0), 0, 2),
    )
    tir = EvenementCiblage(
        index=0,
        tour=0,
        joueur=0,
        assassin=assassin,
        cibles=cibles,
        victime=None,
        refus=True,
        ecart_si_refus=3,
        ecarts_si_meurtre=(1, 2),
        d_avant={0: 1, 1: 1, 2: 1, 3: 0},
    )
    trace = _trace([], [tir])
    assert B.b2_bascule(trace).numerateur == 0
    assert B.b2_bascule(trace).denominateur == 1
    assert B.b2_distribution(trace)["domaine_propre"].numerateur == 1


def test_b4_separe_le_refus_choisi_du_refus_force():
    """Le denominateur litteral gonfle le taux en y versant des refus mecaniques.

    Trois noeuds : deux sans cible -- refus force -- et un avec cible, ou le joueur tue.
    Le taux qui decrit une decision vaut `0 / 1`. Le taux litteral vaut `2 / 3`, et il ne
    mesure que la frequence des Assassins isoles.
    """
    isole = EvenementCiblage(
        index=0,
        tour=0,
        joueur=0,
        assassin=banquet(Carte(1, Role.ASSASSIN, 0), Position.ESTIME, 0),
        cibles=(),
        victime=None,
        refus=True,
        ecart_si_refus=0,
        ecarts_si_meurtre=(),
        d_avant=dict.fromkeys(range(4), 0),
    )
    cible = banquet(Carte(0, Role.NOBLE, 0), Position.ESTIME, 1)
    accompagne = EvenementCiblage(
        index=2,
        tour=0,
        joueur=1,
        assassin=banquet(Carte(1, Role.ASSASSIN, 1), Position.ESTIME, 1),
        cibles=(cible,),
        victime=cible,
        refus=False,
        ecart_si_refus=0,
        ecarts_si_meurtre=(2,),
        d_avant=dict.fromkeys(range(4), 0),
    )
    trace = _trace([], [isole, isole, accompagne])
    choisi = B.b4(trace)
    litteral = B.b4(trace, denominateur="tous_noeuds")
    assert (choisi.numerateur, choisi.denominateur) == (0, 1)
    assert (litteral.numerateur, litteral.denominateur) == (2, 3)
    assert choisi.valeur == 0.0 and litteral.valeur == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------------
# B6 -- le plancher de nullite
# ---------------------------------------------------------------------------------


def test_la_distance_tv_est_strictement_positive_entre_deux_moities_du_meme_tour():
    """Deux echantillons de la MEME loi ne rendent pas zero : B6 a un plancher.

    Sans ce plancher publie, une distance de B6 « non nulle » ne temoigne de rien.
    """
    engine = Engine(INSTANCE)
    traces = [
        jouer(engine, seed, [Aleatoire(random.Random(seed * 3 + s)) for s in range(3)])
        for seed in range(120)
    ]
    moyenne, quantile = B.plancher_tv(traces, tour=0, graine=7)
    assert moyenne > 0.0
    assert quantile >= moyenne


def test_la_distance_tv_refuse_un_echantillon_vide():
    """Un tour jamais joue ne se compare pas : la distance n'existe pas."""
    with pytest.raises(ValueError, match="vide"):
        B.distance_tv({}, {("a",): 1})


# ---------------------------------------------------------------------------------
# Coherence structurelle des denominateurs sur de vraies parties
# ---------------------------------------------------------------------------------


def test_les_denominateurs_valent_ce_que_les_regles_imposent():
    """`joueurs x tours` poses, et autant de noeuds de ciblage que d'Assassins poses.

    Un denominateur qui derive est la premiere facon de rendre un taux incomparable ; il
    se verifie contre l'arithmetique du paragraphe 3.2, pas contre le code.
    """
    engine = Engine(INSTANCE)
    attendu = INSTANCE.joueurs * INSTANCE.tours
    for seed in range(20):
        trace = jouer(engine, seed, [Greedy()] * 3)
        assert len(trace.poses) == attendu
        assassins = sum(
            1
            for pose in trace.poses
            for carte in (pose.banquet, pose.propre, pose.adverse)
            if carte.carte.role is Role.ASSASSIN
        )
        assert len(trace.ciblages) == assassins
        assert B.b1(trace).denominateur == attendu
        assert B.b7(trace).denominateur == attendu

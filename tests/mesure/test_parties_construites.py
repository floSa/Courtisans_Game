"""Le compteur, sur trois parties dont les douze cartes du banquet sont ecrites a la main.

Les tests de `test_retournement.py` verifient les quatre definitions sur des suites de
statuts fabriquees. Ceux-ci verifient qu'une **vraie partie**, jouee par le moteur, produit
bien la suite de statuts qu'on a calculee de tete a partir des cartes posees.

Sans eux, le compteur pourrait etre juste sur des suites inventees et faux sur le jeu :
c'est le trou exact -- une mesure correcte sur un support qui n'est pas celui qu'on croit --
qui a coute trois mois au projet.

Rappel de ce qui bouge l'influence d'une famille (paragraphe 2.2 des regles) :

- une carte posee **au banquet**, en Estime `+valeur`, en Disgrace `-valeur` ;
- une carte du banquet **tuee**, qui sort du decompte.

Rien d'autre. Les cartes de domaine ne changent aucun statut, donc les vingt-quatre cartes
que le script ne designe pas sont sans effet sur les attendus de ce fichier.
"""

from __future__ import annotations

from dataclasses import replace

from courtisans.cards import Position, Role
from courtisans.rules import Statut
from mesure.instance import ENTRAINEMENT_3J
from mesure.partie import ComptageInvisible, Grain, Vue, compter_invisible, observer
from mesure.retournement import Retournements
from tests.mesure.scenario import TourScripte, etat_scripte, politique_scriptee

IND = Statut.INDIFFERENTE
LUM = Statut.LUMIERE
OBS = Statut.OBSCURITE

ESTIME = Position.ESTIME
DISGRACE = Position.DISGRACE

#: L'instance mesuree, importee et non redefinie : deux definitions finissent par ne plus
#: etre d'accord (paragraphe 2 des conventions).
CONFIG = ENTRAINEMENT_3J


def _jouer(script: list[TourScripte]):
    """Joue la partie scriptee de bout en bout et rend son observation."""
    return observer(etat_scripte(CONFIG, script), politique_scriptee(script))


def _sans_repetitions(suite: tuple[Statut, ...]) -> tuple[Statut, ...]:
    """La suite privee de ses repetitions consecutives."""
    compressee: list[Statut] = []
    for statut in suite:
        if not compressee or compressee[-1] is not statut:
            compressee.append(statut)
    return tuple(compressee)


# ---------------------------------------------------------------------------------
# Partie 1 -- les quatre definitions, et l'Espion invisible
# ---------------------------------------------------------------------------------

# Un tour par ligne, dans l'ordre P0, P1, P2, P0, ... Seule la carte du banquet est fixee.
#
#   tour  carte au banquet          d de sa famille apres le tour
#   T1    Noble    f0  Estime       f0 : +2   Lumiere
#   T2    Noble    f0  Disgrace     f0 :  0   Indifferente
#   T3    Neutre   f0  Disgrace     f0 : -1   Obscurite
#   T4    Neutre   f1  Estime       f1 : +1   Lumiere
#   T5    Neutre   f1  Disgrace     f1 :  0   Indifferente
#   T6    Garde    f2  Estime       f2 : +1   Lumiere
#   T7    Garde    f2  Estime       f2 : +2   Lumiere
#   T8    Espion   f3  Estime       f3 : +1   Lumiere -- invisible : c'est un dos
#   T9    Espion   f3  Disgrace     f3 :  0   Indifferente
#   T10   Neutre   f0  Estime       f0 :  0   Indifferente
#   T11   Garde    f1  Estime       f1 : +1   Lumiere
#   T12   Neutre   f2  Disgrace     f2 : +1   Lumiere
SCRIPT_1 = [
    TourScripte(0, Role.NOBLE, ESTIME),
    TourScripte(0, Role.NOBLE, DISGRACE),
    TourScripte(0, Role.NEUTRE, DISGRACE),
    TourScripte(1, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.NEUTRE, DISGRACE),
    TourScripte(2, Role.GARDE, ESTIME),
    TourScripte(2, Role.GARDE, ESTIME),
    TourScripte(3, Role.ESPION, ESTIME),
    TourScripte(3, Role.ESPION, DISGRACE),
    TourScripte(0, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.GARDE, ESTIME),
    TourScripte(2, Role.NEUTRE, DISGRACE),
]

# Treize statuts : celui du plateau vide, puis un par tour.
SUITES_1_VRAIES = (
    (IND, LUM, IND, OBS, OBS, OBS, OBS, OBS, OBS, OBS, IND, IND, IND),
    (IND, IND, IND, IND, LUM, IND, IND, IND, IND, IND, IND, LUM, LUM),
    (IND, IND, IND, IND, IND, IND, LUM, LUM, LUM, LUM, LUM, LUM, LUM),
    (IND, IND, IND, IND, IND, IND, IND, IND, LUM, IND, IND, IND, IND),
)

# Vue publique : les deux Espions de la famille 3 sont des dos, donc la famille 3 reste
# Indifferente aux yeux de tout le monde. Les trois autres familles n'ont que des cartes
# face visible au banquet : leur statut public est leur statut vrai.
SUITES_1_PUBLIQUES = (
    SUITES_1_VRAIES[0],
    SUITES_1_VRAIES[1],
    SUITES_1_VRAIES[2],
    (IND,) * 13,
)

RETOURNEMENTS_1_VRAIS = (
    Retournements(r0=True, r1=True, r2=True, r3=True),  # f0 : L, I, O puis I
    Retournements(r0=True, r1=False, r2=True, r3=False),  # f1 : L, I puis L
    Retournements(r0=True, r1=False, r2=False, r3=False),  # f2 : L, jamais quittee
    Retournements(r0=True, r1=False, r2=True, r3=True),  # f3 : L puis I
)

RETOURNEMENTS_1_PUBLICS = (
    RETOURNEMENTS_1_VRAIS[0],
    RETOURNEMENTS_1_VRAIS[1],
    RETOURNEMENTS_1_VRAIS[2],
    Retournements(r0=False, r1=False, r2=False, r3=False),  # f3 : rien ne se voit
)


def test_partie_1_les_suites_de_statuts_sont_celles_calculees_a_la_main() -> None:
    """Grain tour : treize statuts par famille, l'un apres l'autre."""
    partie = _jouer(SCRIPT_1)
    assert partie.suites[Grain.TOUR, Vue.VRAIE] == SUITES_1_VRAIES


def test_partie_1_la_vue_publique_ignore_les_deux_espions() -> None:
    """La famille 3 n'a que des dos au banquet : personne d'autre que leurs poseurs ne la
    voit changer de statut."""
    partie = _jouer(SCRIPT_1)
    assert partie.suites[Grain.TOUR, Vue.PUBLIQUE] == SUITES_1_PUBLIQUES


def test_partie_1_chaque_joueur_voit_son_propre_espion_et_pas_celui_de_l_autre() -> None:
    """Les deux Espions de la famille 3 sont poses par deux joueurs differents.

    L'ordre des tours est P0, P1, P2, P0, ... : T8 est le tour de P1, T9 celui de P2. Donc,
    sur la famille 3 :

      - P0 ne voit aucun des deux : Indifferente du debut a la fin ;
      - P1 voit le sien, en Estime : `d = +1`, Lumiere a partir de T8, et il ne voit pas
        l'Espion de P2 qui l'annule -- pour lui la famille reste en Lumiere ;
      - P2 ne voit que le sien, en Disgrace : `d = -1`, Obscurite a partir de T9.

    Aucun des trois ne voit donc le retournement que le decompte, lui, appliquera : la
    famille 3 finit Indifferente. **C'est un retournement que personne ne pouvait planifier**,
    et c'est ce que la vue publique seule n'aurait pas su etablir -- elle aurait dit
    « invisible » sans pouvoir dire « invisible de qui ».
    """
    partie = _jouer(SCRIPT_1)
    assert partie.suites[Grain.TOUR, Vue.du_joueur(0)][3] == (IND,) * 13
    assert partie.suites[Grain.TOUR, Vue.du_joueur(1)][3] == (IND,) * 8 + (LUM,) * 5
    assert partie.suites[Grain.TOUR, Vue.du_joueur(2)][3] == (IND,) * 9 + (OBS,) * 4

    for siege in range(CONFIG.joueurs):
        assert not partie.retournements_par_famille(Grain.TOUR, Vue.du_joueur(siege))[3].r2
    assert partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE)[3].r2


def test_partie_1_les_quatre_definitions_famille_par_famille() -> None:
    """Les quatre familles couvrent les quatre combinaisons qui comptent."""
    partie = _jouer(SCRIPT_1)
    assert partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE) == RETOURNEMENTS_1_VRAIS
    assert partie.retournements_par_famille(Grain.TOUR, Vue.PUBLIQUE) == RETOURNEMENTS_1_PUBLICS


def test_partie_1_agregee_a_la_partie() -> None:
    """Au niveau de la partie, les quatre definitions se declenchent -- f0 les porte toutes."""
    partie = _jouer(SCRIPT_1)
    assert partie.retournements(Grain.TOUR, Vue.VRAIE) == Retournements(
        r0=True, r1=True, r2=True, r3=True
    )


def test_partie_1_sans_meurtre_les_deux_grains_disent_la_meme_chose() -> None:
    """Aucun Assassin au banquet, aucun meurtre : le grain fin n'ajoute que des repetitions.

    Le statut d'une famille ne change qu'a la pose de la carte du banquet ; les noeuds de
    ciblage intercales n'y touchent pas.
    """
    partie = _jouer(SCRIPT_1)
    for famille in range(CONFIG.familles):
        fin = partie.suites[Grain.FIN, Vue.VRAIE][famille]
        tour = partie.suites[Grain.TOUR, Vue.VRAIE][famille]
        assert _sans_repetitions(fin) == _sans_repetitions(tour)
    assert partie.retournements(Grain.FIN, Vue.VRAIE) == partie.retournements(
        Grain.TOUR, Vue.VRAIE
    )


def test_partie_1_aucune_carte_ne_meurt() -> None:
    """Tous les Assassins refusent : la defausse reste vide."""
    assert _jouer(SCRIPT_1).morts == 0


def test_partie_1_les_trois_joueurs_jouent_quatre_tours() -> None:
    """Le plancher du paragraphe 3.4 : meme nombre de tours pour tous."""
    assert _jouer(SCRIPT_1).poses_par_joueur == (4, 4, 4)


# ---------------------------------------------------------------------------------
# Partie 2 -- le grain change la reponse du go/no-go
# ---------------------------------------------------------------------------------

# L'Assassin du banquet est le seul mecanisme capable de faire aller-retour un statut a
# l'interieur d'un meme tour : il ajoute sa propre valeur en arrivant, puis retire celle de
# sa victime. Ici, les deux se compensent exactement.
#
#   T1    Noble    f0  Disgrace     f0 : -2   Obscurite
#   T2    Neutre   f0  Estime       f0 : -1   Obscurite   (1 - 2)
#   T3    Assassin f0  Estime       f0 :  0   Indifferente a la pose  (2 - 2)
#         puis il tue le Neutre f0 d'Estime, sa seule cible
#                                   f0 : -1   Obscurite a la fin du tour
#   T4-T6   la famille 1 monte en Estime, sans jamais changer de statut
#   T7-T9   la famille 2 descend en Disgrace, sans jamais changer de statut
#   T10-T12 la famille 3 monte en Estime, sans jamais changer de statut
SCRIPT_2 = [
    TourScripte(0, Role.NOBLE, DISGRACE),
    TourScripte(0, Role.NEUTRE, ESTIME),
    TourScripte(0, Role.ASSASSIN, ESTIME, tuer_au_banquet=True),
    TourScripte(1, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.NOBLE, ESTIME),
    TourScripte(2, Role.NEUTRE, DISGRACE),
    TourScripte(2, Role.NEUTRE, DISGRACE),
    TourScripte(2, Role.NOBLE, DISGRACE),
    TourScripte(3, Role.NEUTRE, ESTIME),
    TourScripte(3, Role.GARDE, ESTIME),
    TourScripte(3, Role.NOBLE, ESTIME),
]

SUITES_2_TOUR = (
    (IND,) + (OBS,) * 12,
    (IND,) * 4 + (LUM,) * 9,
    (IND,) * 7 + (OBS,) * 6,
    (IND,) * 10 + (LUM,) * 3,
)


def test_partie_2_au_grain_tour_aucune_famille_ne_perd_son_acquis() -> None:
    """Chaque famille prend un statut et le garde : R2 est faux pour toutes les quatre."""
    partie = _jouer(SCRIPT_2)
    assert partie.suites[Grain.TOUR, Vue.VRAIE] == SUITES_2_TOUR
    assert partie.retournements(Grain.TOUR, Vue.VRAIE) == Retournements(
        r0=True, r1=False, r2=False, r3=False
    )


def test_partie_2_au_grain_fin_la_famille_0_passe_par_l_indifference() -> None:
    """Entre la pose de l'Assassin et son meurtre, la famille 0 vaut `d = 0`.

    C'est un transitoire intra-tour : il existe, le moteur le traverse, et le grain fin le
    voit. Le grain tour, lui, ne le voit pas -- et la reponse du go/no-go en depend.
    """
    partie = _jouer(SCRIPT_2)
    fin_f0 = _sans_repetitions(partie.suites[Grain.FIN, Vue.VRAIE][0])
    assert fin_f0 == (IND, OBS, IND, OBS)
    assert partie.retournements(Grain.FIN, Vue.VRAIE) == Retournements(
        r0=True, r1=False, r2=True, r3=False
    )


def test_partie_2_une_seule_carte_meurt_et_c_est_la_cible_designee() -> None:
    """Le seul meurtre du script : le Neutre de la famille 0, en Estime."""
    partie = _jouer(SCRIPT_2)
    assert partie.morts == 1
    assert partie.cartes_mortes == ((0, Role.NEUTRE),)


# ---------------------------------------------------------------------------------
# Partie 3 -- « refuser de tuer est possible »
# ---------------------------------------------------------------------------------

# Un Assassin ouvre un noeud de decision meme sans cible : ce n'est pas parce qu'il decide
# qu'il choisit. « Refuser est possible » ne compte que les noeuds ou une cible existe.
#
#   T1    Neutre   f0  Estime      Estime contient desormais le Neutre f0
#   T2    Assassin f1  Disgrace    zone Disgrace : VIDE  -> 0 cible, refus force
#   T3    Assassin f2  Estime      zone Estime : le Neutre f0 -> 1 cible, refus choisi
SCRIPT_3 = [
    TourScripte(0, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.ASSASSIN, DISGRACE),
    TourScripte(2, Role.ASSASSIN, ESTIME),
    TourScripte(1, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.NEUTRE, ESTIME),
    TourScripte(1, Role.NOBLE, ESTIME),
    TourScripte(2, Role.NEUTRE, DISGRACE),
    TourScripte(2, Role.NEUTRE, DISGRACE),
    TourScripte(2, Role.NOBLE, DISGRACE),
    TourScripte(3, Role.NEUTRE, ESTIME),
    TourScripte(3, Role.GARDE, ESTIME),
    TourScripte(3, Role.NOBLE, ESTIME),
]


def test_partie_3_les_deux_premiers_noeuds_de_ciblage_ont_0_puis_1_cible() -> None:
    """L'un ne laisse aucun choix, l'autre en laisse un. Seul le second compte.

    Le constructeur de scenario range les Assassins non designes en fin de pioche : aucun
    Assassin de remplissage n'est pose avant ces deux-la, donc ce sont bien les deux
    premiers noeuds de ciblage de la partie.
    """
    partie = _jouer(SCRIPT_3)
    assert partie.cibles_par_noeud[:2] == (0, 1)


def test_le_compteur_de_refus_possible_ignore_les_noeuds_sans_cible() -> None:
    """`noeuds_avec_cible` compte les noeuds ou le refus est un choix, pas une obligation.

    Sur une liste de cibles ecrite a la main : `(0, 1, 5, 0)` -- deux noeuds sans cible, ou
    l'Assassin ne choisit pas, et deux avec. Attendu calcule de tete : 4 noeuds, 2 a choix.

    La version precedente de ce test recalculait `sum(... if cibles >= 1)` sur la meme
    donnee que la propriete, puis comparait les deux : elle reimplementait la formule
    testee et ne pouvait pas echouer. Defaut releve par l'audit croise.
    """
    partie = replace(_jouer(SCRIPT_3), cibles_par_noeud=(0, 1, 5, 0))
    assert partie.noeuds_ciblage == 4
    assert partie.noeuds_avec_cible == 2


def test_partie_3_aucun_meurtre_car_le_script_refuse_partout() -> None:
    """Le script ne demande aucun meurtre : rien ne meurt, meme la cible disponible."""
    assert _jouer(SCRIPT_3).morts == 0


def test_partie_1_l_evenement_de_la_famille_3_n_est_vu_par_personne() -> None:
    """Le cas exact que la premiere version du rapport declarait a zero.

    Famille 3, vue vraie : `(IND x 8, LUM, IND x 4)`. La seule perte d'acquis est en `t = 9`
    -- l'Espion de P2, en Disgrace, annule celui de P1. Dans les trois vues par siege :

      - P0 ne voit aucun des deux Espions : jamais rien, donc aucun evenement ;
      - P1 ne voit que le sien : il entre en Lumiere en `t = 8` et y reste. Entrer depuis
        l'Indifference n'est pas une perte d'acquis : aucun evenement ;
      - P2 ne voit que le sien : il entre en Obscurite en `t = 9` et y reste. Idem.

    **Un evenement vrai, zero evenement vu.** Ce retournement n'est planifiable par
    personne -- pas meme par un poseur, contrairement a ce que le paragraphe 5.3 de la
    pre-inscription affirmait.
    """
    partie = _jouer(SCRIPT_1)
    vrais = partie.evenements_r2_par_famille(Grain.TOUR, Vue.VRAIE)
    assert vrais[3] == (9,)
    for siege in range(CONFIG.joueurs):
        assert partie.evenements_r2_par_famille(Grain.TOUR, Vue.du_joueur(siege))[3] == ()


def test_partie_1_les_evenements_des_quatre_familles_sont_ceux_calcules_a_la_main() -> None:
    """Quatre pertes d'acquis dans toute la partie, dont une seule invisible de tous.

    f0 `(IND, LUM, IND, OBS x 7, IND x 3)` : Lumiere annulee en `t = 2`, Obscurite annulee
    en `t = 10`. f1 `(IND x 4, LUM, IND x 6, LUM, LUM)` : Lumiere annulee en `t = 5`.
    f2 entre en Lumiere en `t = 6` et n'en sort jamais : aucun evenement. f3 : `t = 9`.
    """
    partie = _jouer(SCRIPT_1)
    assert partie.evenements_r2_par_famille(Grain.TOUR, Vue.VRAIE) == ((2, 10), (5,), (), (9,))


def test_partie_2_l_evenement_intra_tour_n_existe_qu_au_grain_fin() -> None:
    """La famille 0 ne perd son acquis qu'entre la pose de l'Assassin et son meurtre."""
    partie = _jouer(SCRIPT_2)
    assert partie.evenements_r2_par_famille(Grain.TOUR, Vue.VRAIE)[0] == ()
    assert len(partie.evenements_r2_par_famille(Grain.FIN, Vue.VRAIE)[0]) == 1


def test_le_comptage_invisible_sur_la_partie_1_construite_a_la_main() -> None:
    """Le comptage qui a fait rejeter la mesure, sur une partie dont on sait tout.

    Partie 1, vue vraie : quatre pertes d'acquis en tout -- f0 en `t = 2` et `t = 10`,
    f1 en `t = 5`, f3 en `t = 9`. Trois familles sur quatre en R2 (f2 n'en a aucune).

    Une seule de ces pertes n'est vue par aucun siege : celle de f3, ou deux Espions poses
    par deux joueurs differents s'annulent sans qu'aucun des deux ne voie la resultante.
    Donc : 3 familles en R2 dont 1 invisible, 4 evenements dont 1 invisible, et l'unique
    partie compte une fois a chaque niveau.

    **Ce test aurait fait tomber la premiere version du rapport**, qui annoncait zero.
    """
    comptage = compter_invisible([_jouer(SCRIPT_1)], CONFIG.joueurs, CONFIG.familles)
    assert comptage == ComptageInvisible(
        familles_r2=3,
        familles_invisibles=1,
        parties_avec_famille_invisible=1,
        evenements=4,
        evenements_invisibles=1,
        parties_avec_evenement_invisible=1,
    )


def test_le_comptage_invisible_ne_compte_rien_sans_espion_au_banquet() -> None:
    """Partie 3 : aucun Espion designe au banquet, donc tout se voit de tous les sieges."""
    comptage = compter_invisible([_jouer(SCRIPT_3)], CONFIG.joueurs, CONFIG.familles)
    assert comptage.familles_invisibles == 0
    assert comptage.evenements_invisibles == 0

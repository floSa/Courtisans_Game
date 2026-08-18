"""Les sept compteurs B1 a B7, chacun sur une trace construite a la main.

Ecrits AVANT les compteurs (regle 1 des conventions). Chaque attendu est calcule de tete
depuis la definition pre-inscrite au paragraphe 6 de
`mesure/phase2_hypothese_et_instrument.md`, jamais en appelant le compteur teste.

Deux choses que chaque cas verifie, en plus du numerateur :

  - **le denominateur et son grain**, parce que la faute de la phase 1 etait un chiffre juste
    dont la phrase parlait de retournements quand le calcul parlait de parties ;
  - **la vue** sur laquelle le compteur est defini, parce que la vue publique n'est la vue de
    personne et qu'un comportement qualifie une decision.
"""

from __future__ import annotations

import random

import pytest

from courtisans.cards import Position, Role
from courtisans.engine import Engine
from courtisans.rules import Statut
from mesure import comportements as comp
from mesure.instance import ENTRAINEMENT_3J
from mesure.trace import tracer
from tests.mesure.outils_comportements import (
    banquet,
    carte,
    ciblage,
    domaine,
    pose,
    statut_de,
    trace,
)

CONFIG = ENTRAINEMENT_3J


# ---------------------------------------------------------------------------------
# Le type : un chiffre porte son denominateur, son grain et sa vue
# ---------------------------------------------------------------------------------


def test_un_denominateur_nul_rend_none_et_non_zero():
    """« L'occasion ne s'est pas presentee » n'est pas « le comportement n'apparait jamais ».

    Rendre 0 sur un denominateur nul ferait lire la seconde phrase la ou seule la premiere est
    vraie. C'est la faute de la phase 1, a un cran de plus : un taux dont le denominateur est
    vide n'a pas de sujet.
    """
    vide = comp.Compte("essai", 0, 0, "parties", comp.VUE_VRAIE)
    assert vide.taux() is None
    assert "sans objet" in str(vide)
    plein = comp.Compte("essai", 1, 4, "parties", comp.VUE_VRAIE)
    assert plein.taux() == 0.25
    assert "1/4 parties" in str(plein)
    assert "vue vraie" in str(plein)


# ---------------------------------------------------------------------------------
# B1 -- le motif « nourrir puis basculer »
# ---------------------------------------------------------------------------------


def _trace_b1():
    """Le joueur 0 donne f1 au joueur 1, puis met f1 en Disgrace. f1 finit en Obscurite.

    Nœud 0, tour 1 : plateau vide, donc f1 **Indifferente** dans la vue de 0 -- ni Lumiere ni
    poison. Il pose Neutre f1 en Estime au banquet, Garde f2 chez lui, et **Noble f1 chez le
    joueur 1**. C'est l'evenement « nourrir » sur (f1, joueur 1).

    Nœud 1, tour 2 : il pose **Noble f1 en Disgrace** au banquet. C'est l'evenement
    « baisser », et son numero est superieur.

    Decompte : banquet = Neutre f1 en Estime (`+1`) et Noble f1 en Disgrace (`-2`), donc
    `d(f1) = -1` -> **Obscurite**. Le joueur 1 detient encore le Noble f1 vivant chez lui.

    Les quatre clauses tiennent, et la clause 3 tient meme dans sa version **stricte** :
    B1-motif, B1-tentative, B1-strict et B1-collectif valent tous 1 sur 1 partie.
    """
    nourrir = pose(
        numero=0,
        joueur=0,
        tour=1,
        cartes=(
            banquet(1, Role.NEUTRE, Position.ESTIME, poseur=0),
            domaine(2, Role.GARDE, proprietaire=0, poseur=0),
            domaine(1, Role.NOBLE, proprietaire=1, poseur=0),
        ),
        main=(carte(1, Role.NEUTRE), carte(2, Role.GARDE), carte(1, Role.NOBLE)),
    )
    connues_apres = nourrir.posees + nourrir.cartes_posees
    baisser = pose(
        numero=1,
        joueur=0,
        tour=2,
        cartes=(
            banquet(1, Role.NOBLE, Position.DISGRACE, poseur=0, exemplaire=1),
            domaine(3, Role.GARDE, proprietaire=0, poseur=0),
            domaine(3, Role.NEUTRE, proprietaire=1, poseur=0),
        ),
        connues=connues_apres,
        main=(carte(1, Role.NOBLE, 1), carte(3, Role.GARDE), carte(3, Role.NEUTRE)),
    )
    finales = connues_apres + baisser.cartes_posees
    return trace((nourrir, baisser), posees_finales=finales)


def test_b1_le_motif_est_compte_et_le_statut_final_est_bien_l_obscurite():
    """L'attendu de tete : `d(f1) = +1 - 2 = -1`, donc Obscurite, donc les quatre definitions."""
    une = _trace_b1()
    assert statut_de(une.posees_finales, 1) is Statut.OBSCURITE

    comptes = comp.motif_b1([une], CONFIG, sieges=[0])
    assert comptes["B1-motif"].succes == 1
    assert comptes["B1-strict"].succes == 1
    assert comptes["B1-tentative"].succes == 1
    assert comptes["B1-collectif"].succes == 1
    for compte in comptes.values():
        assert compte.total == 1
        assert compte.grain == "parties"
        assert compte.vue == comp.VUE_MIXTE


def test_b1_ne_compte_pas_si_l_adversaire_ne_detient_plus_rien_de_la_famille():
    """Clause 4 : un poison qui n'atteint personne n'est pas un retournement planifie.

    Meme trace, mais le Noble f1 du domaine du joueur 1 est absent du plateau final -- tue
    entre-temps. `d(f1)` est inchange, donc f1 est toujours en Obscurite : **seule la clause 4
    tombe**. B1-motif et B1-strict passent a 0, B1-tentative reste a 1 puisqu'elle ignore les
    clauses 3 et 4.
    """
    une = _trace_b1()
    sans_le_noble = tuple(
        posee
        for posee in une.posees_finales
        if not (posee.zone.proprietaire == 1 and posee.carte.famille == 1)
    )
    amputee = trace(une.decisions, posees_finales=sans_le_noble)
    assert statut_de(amputee.posees_finales, 1) is Statut.OBSCURITE

    comptes = comp.motif_b1([amputee], CONFIG, sieges=[0])
    assert comptes["B1-motif"].succes == 0
    assert comptes["B1-strict"].succes == 0
    assert comptes["B1-tentative"].succes == 1


def test_b1_ne_compte_pas_si_le_don_suit_la_bascule():
    """Clause 2 : l'ordre compte. Nourrir APRES avoir baisse n'est pas le meme motif.

    Les deux nœuds sont echanges. Aucun evenement « baisser » ne suit un « nourrir », donc
    aucune definition ne se satisfait -- pas meme B1-tentative.
    """
    une = _trace_b1()
    premier, second = une.decisions
    from dataclasses import replace

    echangee = trace(
        (replace(second, numero=0), replace(premier, numero=1)),
        posees_finales=une.posees_finales,
    )
    comptes = comp.motif_b1([echangee], CONFIG, sieges=[0])
    assert comptes["B1-tentative"].succes == 0
    assert comptes["B1-motif"].succes == 0


def test_b1_collectif_compte_ce_que_b1_motif_refuse():
    """Deux joueurs differents : le motif existe, l'intention non. C'est l'ecart a publier.

    Le joueur 0 nourrit f1 chez le joueur 1 ; c'est le **joueur 2** qui met f1 en Disgrace.
    B1-motif, qui exige le meme joueur aux deux bouts, vaut 0. B1-collectif vaut 1.
    """
    une = _trace_b1()
    premier, second = une.decisions
    from dataclasses import replace

    par_deux_joueurs = trace(
        (premier, replace(second, joueur=2)), posees_finales=une.posees_finales
    )
    comptes = comp.motif_b1([par_deux_joueurs], CONFIG, sieges=[0, 1, 2])
    assert comptes["B1-motif"].succes == 0
    assert comptes["B1-collectif"].succes == 1


# ---------------------------------------------------------------------------------
# B2 -- l'Assassin en zone contestee
# ---------------------------------------------------------------------------------


def _trace_b2():
    """Le joueur 0 pose un Assassin au banquet en Estime, ou trone un Neutre f2.

    Vue du poseur avant le coup : Neutre f2 en Estime, donc `d(f2) = +1`. Apres le coup, la
    zone banquet-Estime contient ce Neutre f2 et l'Assassin f0. La cible valide est le Neutre
    f2 -- ni Garde, ni l'Assassin lui-meme -- et `|d(f2)| = 1 <= 1` : **zone contestee**.
    """
    deja = (banquet(2, Role.NEUTRE, Position.ESTIME, poseur=1),)
    return trace(
        (
            pose(
                numero=0,
                joueur=0,
                tour=1,
                cartes=(
                    banquet(0, Role.ASSASSIN, Position.ESTIME, poseur=0),
                    domaine(3, Role.GARDE, proprietaire=0, poseur=0),
                    domaine(3, Role.NEUTRE, proprietaire=1, poseur=0),
                ),
                connues=deja,
                main=(carte(0, Role.ASSASSIN), carte(3, Role.GARDE), carte(3, Role.NEUTRE)),
            ),
        )
    )


def test_b2_la_zone_est_contestee_et_le_denominateur_est_les_poses_d_assassin():
    """1 sur 1 pose d'Assassin -- et le denominateur n'est PAS les parties."""
    comptes = comp.b2([_trace_b2()], CONFIG, sieges=[0])
    assert comptes["B2-contestee"].succes == 1
    assert comptes["B2-contestee"].total == 1
    assert comptes["B2-contestee"].grain == "poses d'Assassin"
    assert comptes["B2-contestee"].vue == comp.VUE_DECIDEUR
    assert comptes["B2-cibles"].succes == 1
    assert comptes["B2-banquet"].succes == 1
    assert comptes["B2-fragile-2"].succes == 1


def test_b2_une_zone_sans_cible_valide_n_est_pas_contestee():
    """Un Assassin seul dans son domaine : aucune cible, donc aucune des definitions.

    Le denominateur reste 1 -- l'Assassin a bien ete pose -- et c'est ce qui distingue « il ne
    l'a pas place en zone contestee » de « il n'a pose aucun Assassin ».
    """
    solitaire = trace(
        (
            pose(
                numero=0,
                joueur=0,
                tour=1,
                cartes=(
                    banquet(3, Role.NEUTRE, Position.ESTIME, poseur=0),
                    domaine(0, Role.ASSASSIN, proprietaire=0, poseur=0),
                    domaine(3, Role.GARDE, proprietaire=1, poseur=0),
                ),
                main=(carte(3, Role.NEUTRE), carte(0, Role.ASSASSIN), carte(3, Role.GARDE)),
            ),
        )
    )
    comptes = comp.b2([solitaire], CONFIG, sieges=[0])
    assert comptes["B2-cibles"].succes == 0
    assert comptes["B2-contestee"].succes == 0
    assert comptes["B2-contestee"].total == 1


def test_b2_la_distribution_des_quatre_destinations_somme_au_denominateur():
    """Un Assassin va dans une zone et une seule : les quatre parts somment a 1.

    Controle, pas deduction -- si la somme ne tombait pas, un Assassin serait compte deux fois
    ou pas du tout.
    """
    distribution = comp.distribution_b2([_trace_b2()], CONFIG, sieges=[0])
    assert distribution["banquet-Estime"].succes == 1
    assert sum(c.succes for c in distribution.values()) == 1
    assert {c.total for c in distribution.values()} == {1}


# ---------------------------------------------------------------------------------
# B3 -- le motif de l'alliance
# ---------------------------------------------------------------------------------


def test_b3_donner_une_famille_dont_on_est_soi_meme_porteur():
    """Le joueur 0 a un Neutre f1 chez lui et donne un Noble f1 au joueur 1.

    Les deux ont alors interet a ce que f1 finisse en Lumiere : alliance objective du
    paragraphe 2.4. Denominateur : les poses en domaine adverse, ici 1.

    **B3-simultane vaut 0** : f1 n'a aucune carte au banquet dans la vue de 0, donc elle y est
    Indifferente et non en Lumiere. C'est l'ecart entre « je donne ce que je detiens » et « je
    donne ce qui rapporte », et il se publie.
    """
    deja = (domaine(1, Role.NEUTRE, proprietaire=0, poseur=0),)
    une = trace(
        (
            pose(
                numero=0,
                joueur=0,
                tour=1,
                cartes=(
                    banquet(2, Role.GARDE, Position.ESTIME, poseur=0),
                    domaine(3, Role.GARDE, proprietaire=0, poseur=0),
                    domaine(1, Role.NOBLE, proprietaire=1, poseur=0),
                ),
                connues=deja,
                main=(carte(2, Role.GARDE), carte(3, Role.GARDE), carte(1, Role.NOBLE)),
            ),
        )
    )
    comptes = comp.motif_b3([une], CONFIG, sieges=[0])
    assert comptes["B3-expose"].succes == 1
    assert comptes["B3-expose"].total == 1
    assert comptes["B3-expose"].grain == "poses en domaine adverse"
    assert comptes["B3-expose"].vue == comp.VUE_DECIDEUR
    assert comptes["B3-simultane"].succes == 0


def test_b3_ne_compte_pas_un_don_sur_une_famille_qu_on_ne_detient_pas():
    """Sans exposition, le don n'est pas une alliance. Le denominateur reste 1."""
    une = trace(
        (
            pose(
                numero=0,
                joueur=0,
                tour=1,
                cartes=(
                    banquet(2, Role.GARDE, Position.ESTIME, poseur=0),
                    domaine(3, Role.GARDE, proprietaire=0, poseur=0),
                    domaine(1, Role.NOBLE, proprietaire=1, poseur=0),
                ),
                main=(carte(2, Role.GARDE), carte(3, Role.GARDE), carte(1, Role.NOBLE)),
            ),
        )
    )
    comptes = comp.motif_b3([une], CONFIG, sieges=[0])
    assert comptes["B3-expose"].succes == 0
    assert comptes["B3-expose"].total == 1


def test_b3_l_exposition_se_juge_sur_la_vue_du_decideur_pas_sur_la_verite():
    """Un Espion adverse de f1 pose chez moi m'expose sans que je puisse le savoir.

    C'est le cas qui separe les deux definitions : **B3-expose vaut 0** -- je ne vois pas de
    carte f1 chez moi -- et **B3-expose-vraie vaut 1**. Compter sur la verite repondrait a
    « etait-il objectivement allie », pas a « croyait-il l'etre », et B3 qualifie une decision.
    """
    espion_adverse = domaine(1, Role.ESPION, proprietaire=0, poseur=2)
    une = trace(
        (
            pose(
                numero=0,
                joueur=0,
                tour=1,
                cartes=(
                    banquet(2, Role.GARDE, Position.ESTIME, poseur=0),
                    domaine(3, Role.GARDE, proprietaire=0, poseur=0),
                    domaine(1, Role.NOBLE, proprietaire=1, poseur=0),
                ),
                connues=(),
                posees=(espion_adverse,),
                main=(carte(2, Role.GARDE), carte(3, Role.GARDE), carte(1, Role.NOBLE)),
            ),
        )
    )
    comptes = comp.motif_b3([une], CONFIG, sieges=[0])
    assert comptes["B3-expose"].succes == 0
    assert comptes["B3-expose-vraie"].succes == 1
    assert comptes["B3-expose-vraie"].vue == comp.VUE_VRAIE


# ---------------------------------------------------------------------------------
# B4 -- refuser de tuer, en trois nombres
# ---------------------------------------------------------------------------------


def _trace_b4():
    """Trois nœuds de ciblage, un par categorie, avec les valeurs ecrites a la main.

    | Nœud | Cibles | Valeurs | Action | Categorie |
    |---|---|---|---|---|
    | 0 | 1 connue | tuer 0, refuser 2 | refus | **B4-strict** : le meurtre etait pire |
    | 1 | 2 dos | tout a 5 | refus | **B4-departage** : egalite, tout-dos |
    | 2 | 1 connue | tuer 3, refuser 1 | tuer | un meurtre, non couteux |

    Donc : B4-brut = 2/3, B4-strict = 1/2, B4-departage = 1/2, B4-contre-nature = 0/2,
    B4-tout-dos = 1/3, B4-meurtre-couteux = 0/1.
    """
    cible = domaine(1, Role.NOBLE, proprietaire=0, poseur=0)
    autre = domaine(2, Role.NOBLE, proprietaire=0, poseur=0)
    return trace(
        (
            ciblage(0, 0, 1, (cible,), 0, {0: 0, 1: 2}, action=1, connues=(cible,)),
            ciblage(1, 0, 2, (), 2, {0: 5, 1: 5, 2: 5}, action=2),
            ciblage(2, 0, 3, (autre,), 0, {0: 3, 1: 1}, action=0, connues=(autre,)),
        )
    )


def test_b4_les_trois_nombres_et_leurs_denominateurs():
    """Les trois portent sur les REFUS, le taux brut sur les nœuds a >= 1 cible."""
    comptes = comp.b4([_trace_b4()], CONFIG, sieges=[0])
    assert (comptes["B4-brut"].succes, comptes["B4-brut"].total) == (2, 3)
    assert comptes["B4-brut"].grain == "nœuds de ciblage a >= 1 cible"
    assert (comptes["B4-strict"].succes, comptes["B4-strict"].total) == (1, 2)
    assert (comptes["B4-departage"].succes, comptes["B4-departage"].total) == (1, 2)
    assert (comptes["B4-contre-nature"].succes, comptes["B4-contre-nature"].total) == (0, 2)
    assert comptes["B4-strict"].grain == "refus"
    assert (comptes["B4-tout-dos"].succes, comptes["B4-tout-dos"].total) == (1, 3)
    assert (comptes["B4-meurtre-couteux"].succes, comptes["B4-meurtre-couteux"].total) == (0, 1)


def test_b4_l_identite_des_trois_est_verifiee_et_leve_si_elle_tombe():
    """`strict + departage + contre-nature = refus`. Un controle, pas une deduction."""
    comptes = comp.b4([_trace_b4()], CONFIG, sieges=[0])
    comp.verifier_b4(comptes)

    from dataclasses import replace

    fausse = dict(comptes)
    fausse["B4-strict"] = replace(comptes["B4-strict"], succes=0)
    with pytest.raises(ValueError, match="identite de B4 violee"):
        comp.verifier_b4(fausse)


def test_b4_un_refus_contre_nature_est_bien_compte_quand_il_existe():
    """Chez le greedy il vaut 0 par construction ; le compteur doit savoir le voir quand meme.

    Un zero qu'on n'imprime pas n'est pas un zero verifie. Ici un refus a valeur 1 alors qu'un
    meurtre valait 4 : le compteur doit le classer contre-nature, sinon la ligne de base de la
    phase 3 ne diagnostiquerait rien.
    """
    cible = domaine(1, Role.NOBLE, proprietaire=0, poseur=0)
    une = trace((ciblage(0, 0, 1, (cible,), 0, {0: 4, 1: 1}, action=1, connues=(cible,)),))
    comptes = comp.b4([une], CONFIG, sieges=[0])
    assert comptes["B4-contre-nature"].succes == 1
    assert comptes["B4-strict"].succes == 0
    comp.verifier_b4(comptes)


def test_b4_un_meurtre_couteux_est_compte_symetriquement():
    """Tuer alors que tout meurtre baissait l'ecart : 0 chez le greedy, mesurable en general."""
    cible = domaine(1, Role.NOBLE, proprietaire=0, poseur=0)
    une = trace((ciblage(0, 0, 1, (cible,), 0, {0: 0, 1: 2}, action=0, connues=(cible,)),))
    comptes = comp.b4([une], CONFIG, sieges=[0])
    assert (comptes["B4-meurtre-couteux"].succes, comptes["B4-meurtre-couteux"].total) == (1, 1)


def test_b4_un_noeud_sans_cible_n_entre_dans_aucun_denominateur():
    """Refuser est toujours legal, donc un nœud sans cible n'est pas un choix de refuser.

    L'inclure gonflerait le taux de refus par construction -- c'est la lecture litterale vide
    que le paragraphe 6.4 refuse.
    """
    une = trace((ciblage(0, 0, 1, (), 0, {0: 7}, action=0),))
    comptes = comp.b4([une], CONFIG, sieges=[0])
    assert comptes["B4-brut"].total == 0
    assert comptes["B4-brut"].taux() is None


# ---------------------------------------------------------------------------------
# B5 -- se mefier des Espions
# ---------------------------------------------------------------------------------


def _pose_b5(position_du_dos: Position):
    """Une majorite serree sur f1, avec un dos au banquet du cote qu'on choisit.

    Vue du joueur 0 : un Neutre f1 en Estime, donc `d(f1) = +1`. Verite : un Espion f2 au
    banquet, pose par le joueur 1, que 0 ne peut pas identifier -- c'est le dos. Sa main
    contient un Neutre f1, donc renforcer est **possible**. Il pose ce Neutre f1 en Estime :
    il renforce le cote deja favorable.

    Les familles f0 et f2 ne sont pas dans sa main ; f3 y est, mais `d(f3) = 0` donc
    `|d| != 1`. Le denominateur en couples (nœud, famille) vaut donc **1**.
    """
    visible = banquet(1, Role.NEUTRE, Position.ESTIME, poseur=1)
    dos = banquet(2, Role.ESPION, position_du_dos, poseur=1)
    return pose(
        numero=0,
        joueur=0,
        tour=1,
        cartes=(
            banquet(1, Role.NEUTRE, Position.ESTIME, poseur=0, exemplaire=1),
            domaine(3, Role.GARDE, proprietaire=0, poseur=0),
            domaine(3, Role.GARDE, proprietaire=1, poseur=0, exemplaire=1),
        ),
        connues=(visible,),
        posees=(visible, dos),
        main=(carte(1, Role.NEUTRE, 1), carte(3, Role.GARDE), carte(3, Role.GARDE, 1)),
    )


def test_b5_le_denominateur_est_un_couple_noeud_famille():
    """1 sur 1 couple. Compter par nœud melangerait des familles en situations distinctes."""
    comptes = comp.b5([trace((_pose_b5(Position.DISGRACE),))], CONFIG, sieges=[0])
    assert (comptes["B5-renfort"].succes, comptes["B5-renfort"].total) == (1, 1)
    assert comptes["B5-renfort"].grain == "couples (nœud, famille)"
    assert comptes["B5-renfort"].vue == comp.VUE_DECIDEUR


def test_b5_le_pire_cas_selectionne_d_autres_couples():
    """Le dos du cote favorable ramene la marge pire cas a 0 : le couple sort du denominateur.

    Dos en **Disgrace** : marge visible `+1`, pire cas `+1` -- les deux definitions retiennent
    le couple. Dos en **Estime**, du cote favorable : pire cas `+1 - 1 = 0`, donc `|pire| != 1`
    et **B5-pire-cas n'a plus de denominateur du tout**, alors que B5-renfort compte toujours
    1 sur 1. C'est exactement l'ecart que le paragraphe 6.5 demande de publier.
    """
    en_disgrace = comp.b5([trace((_pose_b5(Position.DISGRACE),))], CONFIG, sieges=[0])
    assert (en_disgrace["B5-renfort"].succes, en_disgrace["B5-renfort"].total) == (1, 1)
    assert (en_disgrace["B5-pire-cas"].succes, en_disgrace["B5-pire-cas"].total) == (1, 1)

    en_estime = comp.b5([trace((_pose_b5(Position.ESTIME),))], CONFIG, sieges=[0])
    assert (en_estime["B5-renfort"].succes, en_estime["B5-renfort"].total) == (1, 1)
    assert en_estime["B5-pire-cas"].total == 0
    assert en_estime["B5-pire-cas"].taux() is None


def test_b5_sans_dos_au_banquet_le_denominateur_est_vide():
    """La mefiance ne se mesure que s'il y a de quoi se mefier. Sinon : sans objet, pas zero."""
    visible = banquet(1, Role.NEUTRE, Position.ESTIME, poseur=1)
    sans_dos = pose(
        numero=0,
        joueur=0,
        tour=1,
        cartes=(
            banquet(1, Role.NEUTRE, Position.ESTIME, poseur=0, exemplaire=1),
            domaine(3, Role.GARDE, proprietaire=0, poseur=0),
            domaine(3, Role.GARDE, proprietaire=1, poseur=0, exemplaire=1),
        ),
        connues=(visible,),
        main=(carte(1, Role.NEUTRE, 1), carte(3, Role.GARDE), carte(3, Role.GARDE, 1)),
    )
    comptes = comp.b5([trace((sans_dos,))], CONFIG, sieges=[0])
    assert comptes["B5-renfort"].total == 0
    assert comptes["B5-renfort"].taux() is None


# ---------------------------------------------------------------------------------
# B6 -- jouer differemment en fin de partie
# ---------------------------------------------------------------------------------


def _au_tour(numero: int, tour: int, position: Position):
    """Une pose au banquet dans la position voulue, au tour voulu."""
    return pose(
        numero=numero,
        joueur=0,
        tour=tour,
        cartes=(
            banquet(0, Role.GARDE, position, poseur=0, exemplaire=numero % 2),
            domaine(3, Role.GARDE, proprietaire=0, poseur=0, exemplaire=numero % 2),
            domaine(3, Role.NEUTRE, proprietaire=1, poseur=0, exemplaire=numero % 2),
        ),
    )


def test_b6_les_distributions_sont_rendues_par_tour_et_jamais_agregees():
    """Tour 1 en Estime, tour 4 en Disgrace : la distance de variation totale vaut 1.

    C'est le maximum. Une distance de 1 veut dire que les deux tours n'ont aucune categorie en
    commun -- ici le banquet passe de tout-Estime a tout-Disgrace.
    """
    une = trace((_au_tour(0, 1, Position.ESTIME), _au_tour(1, 4, Position.DISGRACE)))
    distributions = comp.distributions_b6([une], CONFIG, sieges=[0])
    assert distributions[("banquet", 1)]["Estime"].succes == 1
    assert distributions[("banquet", 1)]["Disgrace"].succes == 0
    assert distributions[("banquet", 4)]["Disgrace"].succes == 1
    assert distributions[("banquet", 1)]["Estime"].total == 1

    distance = comp.distance_de_variation_totale(distributions, "banquet", 1, 4)
    assert distance == pytest.approx(1.0, abs=1e-12)


def test_b6_une_distance_sans_l_un_des_deux_tours_rend_none():
    """Un tour absent n'est pas un tour identique. Rendre 0 ferait lire « aucun changement »."""
    une = trace((_au_tour(0, 1, Position.ESTIME),))
    distributions = comp.distributions_b6([une], CONFIG, sieges=[0])
    assert comp.distance_de_variation_totale(distributions, "banquet", 1, 4) is None


def test_b6_le_don_est_classe_cadeau_neutre_ou_poison_selon_la_vue_du_poseur():
    """Les trois categories du groupe « domaine adverse », sur trois statuts differents.

    f1 en Lumiere dans sa vue -> **cadeau**. f2 sans carte au banquet -> Indifferente ->
    **neutre**. f3 en Obscurite -> **poison**.
    """
    plateau = (
        banquet(1, Role.NOBLE, Position.ESTIME, poseur=1),
        banquet(3, Role.NOBLE, Position.DISGRACE, poseur=1),
    )
    for numero, (famille, attendu) in enumerate(((1, "cadeau"), (2, "neutre"), (3, "poison"))):
        don = pose(
            numero=numero,
            joueur=0,
            tour=1,
            cartes=(
                banquet(0, Role.GARDE, Position.ESTIME, poseur=0),
                domaine(0, Role.NEUTRE, proprietaire=0, poseur=0),
                domaine(famille, Role.NEUTRE, proprietaire=1, poseur=0),
            ),
            connues=plateau,
        )
        classes = comp.distributions_b6([trace((don,))], CONFIG, sieges=[0])[
            ("domaine adverse", 1)
        ]
        assert classes[attendu].succes == 1, f"famille {famille} devait etre {attendu}"
        assert sum(c.succes for c in classes.values()) == 1


# ---------------------------------------------------------------------------------
# B7 -- ne pas defendre ce qui est deja sur
# ---------------------------------------------------------------------------------


def _pose_b7_hors_d_atteinte():
    """f1 est hors d'atteinte, et le joueur 0 la renforce quand meme.

    Les dix cartes de f1 -- 5 roles x 2 exemplaires -- sont toutes localisees :
      - **deux Gardes f1 en Estime au banquet**, donc `d(f1) = +2`. Ce sont des Gardes : un
        Assassin ne peut pas les tuer (paragraphe 4.3), donc ils ne comptent pas dans le
        materiel mobilisable ;
      - **un Neutre f1 dans sa main**, celui qu'il va poser ;
      - **les sept autres a la defausse**, donc hors du jeu (paragraphe 4.1).

    Residu de f1 : `2 - 2 - 0 - 0 = 0` pour le Garde, `2 - 0 - 1 - 1 = 0` pour le Neutre, et
    `2 - 0 - 0 - 2 = 0` pour l'Assassin, le Noble et l'Espion. **Materiel mobilisable : 0.**
    Poids de bascule : `min(0, occasions) = 0`. Et `|d(f1)| = 2 > 0` : **hors d'atteinte**.

    Il pose ce Neutre f1 **en Estime**, du cote deja favorable. C'est un gaspillage.
    """
    gardes = (
        banquet(1, Role.GARDE, Position.ESTIME, poseur=0),
        banquet(1, Role.GARDE, Position.ESTIME, poseur=1, exemplaire=1),
    )
    mortes = (
        carte(1, Role.ASSASSIN, 0),
        carte(1, Role.ASSASSIN, 1),
        carte(1, Role.NOBLE, 0),
        carte(1, Role.NOBLE, 1),
        carte(1, Role.ESPION, 0),
        carte(1, Role.ESPION, 1),
        carte(1, Role.NEUTRE, 1),
    )
    return pose(
        numero=0,
        joueur=0,
        tour=4,
        cartes=(
            banquet(1, Role.NEUTRE, Position.ESTIME, poseur=0),
            domaine(2, Role.GARDE, proprietaire=0, poseur=0),
            domaine(3, Role.GARDE, proprietaire=1, poseur=0),
        ),
        connues=gardes,
        main=(carte(1, Role.NEUTRE), carte(2, Role.GARDE), carte(3, Role.GARDE)),
        mortes=mortes,
        tours_restants=(1, 0, 0),
    )


def test_b7_une_famille_hors_d_atteinte_renforcee_est_un_gaspillage():
    """1 sur 1 pose au banquet, et l'occasion existait -- les deux se publient ensemble."""
    comptes = comp.b7([trace((_pose_b7_hors_d_atteinte(),))], CONFIG, sieges=[0])
    assert (comptes["B7-gaspillage"].succes, comptes["B7-gaspillage"].total) == (1, 1)
    assert comptes["B7-gaspillage"].grain == "poses au banquet"
    assert comptes["B7-gaspillage"].vue == comp.VUE_DECIDEUR
    assert comptes["B7-occasions"].succes == 1
    assert comptes["B7-lumiere"].succes == 1


def test_b7_la_borne_de_materiel_est_ce_qui_distingue_les_deux_definitions():
    """Sans les morts, f1 n'est plus hors d'atteinte -- et B7-lumiere compte quand meme.

    Meme position, defausse **vide**. Le residu de f1 remonte a sept cartes, soit une valeur
    mobilisable de `1 + 1 + 2 + 2 + 1 + 1 + 1 = 9`, largement superieure a `|d| = 2` : f1
    redevient atteignable, donc **B7-gaspillage tombe a 0**. B7-lumiere, qui ignore la borne,
    reste a 1. L'ecart entre les deux EST ce que la borne retire.
    """
    from dataclasses import replace

    sans_morts = replace(_pose_b7_hors_d_atteinte(), mortes=())
    comptes = comp.b7([trace((sans_morts,))], CONFIG, sieges=[0])
    assert comptes["B7-gaspillage"].succes == 0
    assert comptes["B7-occasions"].succes == 0
    assert comptes["B7-lumiere"].succes == 1
    assert comptes["B7-lumiere"].total == 1


def test_b7_renforcer_le_mauvais_cote_n_est_pas_un_gaspillage():
    """Poser en Disgrace sur une f1 en Lumiere hors d'atteinte est inutile, mais pas un renfort.

    Le compteur mesure « renforcer ce qui est deja sur », pas « jouer une carte sans effet ».
    L'occasion reste comptee -- la famille est bien hors d'atteinte -- et c'est ce qui permet de
    lire le zero comme un choix et non comme une absence de situation.
    """
    from dataclasses import replace

    a_contresens = _pose_b7_hors_d_atteinte()
    cartes = list(a_contresens.cartes_posees)
    cartes[0] = banquet(1, Role.NEUTRE, Position.DISGRACE, poseur=0)
    inverse = replace(a_contresens, cartes_posees=tuple(cartes))
    comptes = comp.b7([trace((inverse,))], CONFIG, sieges=[0])
    assert comptes["B7-gaspillage"].succes == 0
    assert comptes["B7-occasions"].succes == 1


# ---------------------------------------------------------------------------------
# Integration : la trace d'une vraie partie
# ---------------------------------------------------------------------------------


def _traces_reelles(nb: int, greedy_au_siege_0: bool):
    """`nb` parties reelles, seeds 0.., avec ou sans greedy au siege 0."""
    from agents.politique import politique_greedy
    from mesure.partie import politique_uniforme

    traces = []
    for seed in range(nb):
        alea = random.Random(700_000 + seed)
        politiques = [politique_uniforme(alea) for _ in range(CONFIG.joueurs)]
        if greedy_au_siege_0:
            politiques[0] = politique_greedy(random.Random(800_000 + seed))
        traces.append(tracer(Engine(CONFIG).reset(seed), politiques, seed=seed))
    return traces


def test_la_trace_d_une_vraie_partie_a_les_bons_comptes():
    """12 poses, 4 par siege, gains a somme nulle -- l'arithmetique de l'instance."""
    une = _traces_reelles(1, greedy_au_siege_0=True)[0]
    poses = une.poses()
    assert len(poses) == CONFIG.tours * CONFIG.joueurs == 12
    for siege in range(CONFIG.joueurs):
        assert [p.tour for p in poses if p.joueur == siege] == [1, 2, 3, 4]
    assert sum(une.gains) == pytest.approx(0.0, abs=1e-12)
    for decision in poses:
        assert len(decision.cartes_posees) == 3


def test_la_trace_refuse_un_nombre_de_politiques_qui_ne_colle_pas_aux_sieges():
    """Deux politiques pour trois sieges doit lever, pas jouer avec la derniere par defaut."""
    from mesure.partie import politique_uniforme

    une = politique_uniforme(random.Random(0))
    with pytest.raises(ValueError, match="il en faut une par siege"):
        tracer(Engine(CONFIG).reset(0), [une, une])


def test_les_sept_compteurs_tournent_sur_de_vraies_parties_et_l_identite_de_b4_tient():
    """Aucun chiffre attendu ici : c'est un controle de coherence, pas une mesure.

    Ce que le cas etablit : les compteurs acceptent des traces reelles, chaque denominateur
    colle a l'arithmetique de l'instance, les inclusions entre definitions concurrentes tiennent,
    et l'identite de B4 tient -- `tous_les_comportements` appelle `verifier_b4`, qui leve sinon.
    """
    traces = _traces_reelles(6, greedy_au_siege_0=True)
    comptes = comp.tous_les_comportements(traces, CONFIG, sieges=[0])
    assert comptes["B1-motif"].total == 6
    assert comptes["B3-expose"].total == 6 * CONFIG.tours
    assert comptes["B7-gaspillage"].total == 6 * CONFIG.tours
    assert comptes["B1-tentative"].succes >= comptes["B1-motif"].succes
    assert comptes["B1-motif"].succes >= comptes["B1-strict"].succes
    assert comptes["B2-cibles"].succes >= comptes["B2-contestee"].succes
    assert comptes["B2-fragile-2"].succes >= comptes["B2-contestee"].succes
    assert comptes["B7-lumiere"].succes >= comptes["B7-gaspillage"].succes


def test_le_greedy_ne_produit_ni_refus_contre_nature_ni_meurtre_couteux():
    """Les deux zeros de construction, confrontes a de vraies parties.

    `choisir` prend un argmax, donc un refus strictement domine est impossible -- et tuer alors
    que tout meurtre coutait l'est aussi. Un zero se confronte avant d'etre ecrit : celui de la
    phase 1 etait contredit par un test du meme livrable.
    """
    traces = _traces_reelles(12, greedy_au_siege_0=True)
    comptes = comp.b4(traces, CONFIG, sieges=[0])
    assert comptes["B4-brut"].total > 0, "sans nœud de ciblage, le cas ne testerait rien"
    assert comptes["B4-contre-nature"].succes == 0
    assert comptes["B4-meurtre-couteux"].succes == 0


def test_l_aleatoire_produit_lui_des_refus_contre_nature():
    """Le contre-cas : sans lui, les deux zeros ci-dessus pourraient venir d'un compteur mort.

    Une politique uniforme refuse sans regarder l'ecart, donc elle doit produire des refus
    strictement domines. Si ce compte etait nul aussi, c'est le compteur qu'il faudrait
    soupconner, pas le greedy.
    """
    traces = _traces_reelles(20, greedy_au_siege_0=False)
    comptes = comp.b4(traces, CONFIG, sieges=[0, 1, 2])
    assert comptes["B4-contre-nature"].succes > 0

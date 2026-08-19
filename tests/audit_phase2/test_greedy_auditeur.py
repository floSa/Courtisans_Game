"""Controles hostiles sur MON greedy, avant de juger celui du constructeur.

Un auditeur dont l'instrument est faux rejette pour de mauvaises raisons. Ces cas
verifient donc d'abord que mon greedy fait ce que le paragraphe 7.1 dit -- attendu
calcule de tete, jamais par le code -- puis qu'il est aveugle a ce qu'il doit ignorer.
"""

from __future__ import annotations

import pytest

from courtisans.cards import Carte, Position, Role
from courtisans.engine import Phase

from audit.phase2.decompte import scores
from audit.phase2.greedy import Greedy
from tests.audit_phase2.outils import INSTANCE, banquet, domaine, etat_de_ciblage, etat_de_pose


# ---------------------------------------------------------------------------------
# Deux positions symetriques : il DOIT refuser, il DOIT tuer
# ---------------------------------------------------------------------------------


def _position_ou_tuer_coute():
    """Tuer ferait passer ma famille de Lumiere a Indifferente. Attendu : refus.

    Plateau, calcule de tete :
      - Noble f0 en Estime            -> `d[f0] = +2`, f0 en Lumiere
      - Assassin f1 de J0 en Estime   -> `d[f1] = +1`
      - Neutre f0 dans le domaine J0  -> J0 marque `+1`

    Ecart de J0 : `1 - 0 = 1`. La seule cible de la zone Estime est le Noble f0 ; le tuer
    porte `d[f0]` a `0`, f0 devient Indifferente, J0 tombe a `0` et son ecart a `0`.
    Refuser vaut donc strictement mieux : `1 > 0`.
    """
    noble = Carte(0, Role.NOBLE, 0)
    assassin = Carte(1, Role.ASSASSIN, 0)
    posees = [
        banquet(noble, Position.ESTIME, poseur=1),
        banquet(assassin, Position.ESTIME, poseur=0),
        domaine(Carte(0, Role.NEUTRE, 0), proprietaire=0, poseur=2),
    ]
    pose_assassin = posees[1]
    return etat_de_ciblage(posees, pose_assassin, joueur=0), noble


def _position_ou_tuer_rapporte():
    """Tuer ferait sortir ma famille de l'Obscurite. Attendu : meurtre.

    Meme plateau, le Noble f0 mis en **Disgrace** : `d[f0] = -2`, f0 en Obscurite, donc le
    Neutre f0 du domaine de J0 lui coute `-1`. Tuer le Noble porte `d[f0]` a `0` : f0
    devient Indifferente et J0 remonte de `-1` a `0`.
    """
    noble = Carte(0, Role.NOBLE, 0)
    assassin = Carte(1, Role.ASSASSIN, 0)
    posees = [
        banquet(noble, Position.DISGRACE, poseur=1),
        banquet(assassin, Position.DISGRACE, poseur=0),
        domaine(Carte(0, Role.NEUTRE, 0), proprietaire=0, poseur=2),
    ]
    return etat_de_ciblage(posees, posees[1], joueur=0), noble


def test_les_deux_positions_ont_bien_ete_construites():
    """L'attendu calcule de tete est verifie AVANT d'interroger la politique.

    Sans ce controle, un test qui passe ne prouverait rien : il pourrait valider une
    politique correcte sur une position qui n'est pas celle qu'on croit avoir batie.
    """
    etat, noble = _position_ou_tuer_coute()
    assert etat.cibles_courantes() == (
        next(p for p in etat.vue_privilegiee().posees if p.carte == noble),
    )
    assert scores(etat.vue_privilegiee().posees, 4, 3) == [1, 0, 0]

    etat, _ = _position_ou_tuer_rapporte()
    assert scores(etat.vue_privilegiee().posees, 4, 3) == [-1, 0, 0]


@pytest.mark.parametrize("horizon", ["tour", "noeud"])
def test_le_greedy_refuse_quand_le_meurtre_lui_couterait(horizon):
    """« Le refus est une action a part entiere » (paragraphe 4.1), et il doit servir."""
    etat, _ = _position_ou_tuer_coute()
    refus = len(etat.cibles_courantes())
    assert Greedy(horizon=horizon).action(etat) == refus


@pytest.mark.parametrize("horizon", ["tour", "noeud"])
def test_le_greedy_tue_quand_le_meurtre_lui_rapporte(horizon):
    """Le controle symetrique : un greedy qui refuserait toujours passerait le precedent."""
    etat, _ = _position_ou_tuer_rapporte()
    assert Greedy(horizon=horizon).action(etat) == 0


# ---------------------------------------------------------------------------------
# L'aveuglement : deux etats qui ne different QUE par l'identite d'un dos adverse
# ---------------------------------------------------------------------------------


def _paire_differant_par_un_dos(role_place: Role = Role.ESPION):
    """Deux plateaux identiques a l'identite pres d'un Espion adverse au banquet.

    L'Espion de J1 est `f0` dans l'un, `f3` dans l'autre. Tout le reste est identique, y
    compris la taille de la pioche : un joueur qui ne triche pas voit **le meme dos**.
    """
    commun = [
        banquet(Carte(2, Role.NOBLE, 0), Position.ESTIME, poseur=2),
        domaine(Carte(2, Role.NEUTRE, 0), proprietaire=0, poseur=1),
        domaine(Carte(0, Role.NEUTRE, 1), proprietaire=1, poseur=2),
    ]
    main = [Carte(0, Role.NOBLE, 1), Carte(1, Role.GARDE, 0), Carte(3, Role.NEUTRE, 0)]
    etats = []
    for famille in (0, 3):
        dos = banquet(Carte(famille, role_place, 1), Position.DISGRACE, poseur=1)
        etats.append(
            etat_de_pose(
                [*commun, dos],
                main,
                joueur=0,
                pioche=[Carte(1, Role.NEUTRE, 1), Carte(2, Role.GARDE, 1)],
                tours_joues=1,
            )
        )
    return etats


def test_les_deux_etats_different_bien_et_seulement_par_le_dos():
    """Le montage est verifie des deux cotes : la difference existe, et elle est cachee.

    Sans cette double verification, l'aveuglement se prouverait sur deux etats identiques.
    """
    a, b = _paire_differant_par_un_dos()
    dos_a = [p for p in a.vue_privilegiee().posees if p.poseur == 1 and p.carte.face_cachee]
    dos_b = [p for p in b.vue_privilegiee().posees if p.poseur == 1 and p.carte.face_cachee]
    assert dos_a[0].carte != dos_b[0].carte  # la difference existe
    assert a.information_state_string(0) == b.information_state_string(0)  # invariant I7
    assert a.legal_actions() == b.legal_actions()


@pytest.mark.parametrize("horizon", ["tour", "noeud"])
def test_mon_greedy_joue_le_meme_coup_des_deux_cotes(horizon):
    """Si le coup differait, ma politique lirait la vue de dieu et mon audit serait nul."""
    a, b = _paire_differant_par_un_dos()
    greedy = Greedy(horizon=horizon)
    assert greedy.action(a) == greedy.action(b)


def test_mon_greedy_est_aveugle_aussi_a_un_dos_qu_il_peut_tuer():
    """Le cas le plus tentant : le dos est une **cible**, donc un objet qu'on manipule.

    Le moteur rend les cibles sous forme de `CartePosee` completes, identite comprise. Une
    politique qui lit `cible.carte.famille` choisirait ici deux indices differents.
    """
    commun = [
        banquet(Carte(2, Role.NOBLE, 0), Position.DISGRACE, poseur=2),
        domaine(Carte(2, Role.NEUTRE, 0), proprietaire=0, poseur=1),
    ]
    for horizon in ("tour", "noeud"):
        choix = []
        for famille in (0, 3):
            assassin = banquet(Carte(1, Role.ASSASSIN, 0), Position.DISGRACE, poseur=0)
            dos = banquet(Carte(famille, Role.ESPION, 1), Position.DISGRACE, poseur=1)
            etat = etat_de_ciblage([*commun, dos, assassin], assassin, joueur=0)
            assert len(etat.cibles_courantes()) == 2  # le Noble et le dos
            choix.append(Greedy(horizon=horizon).action(etat))
        assert choix[0] == choix[1], f"horizon {horizon} : le choix depend du dos"


# ---------------------------------------------------------------------------------
# La regle de departage : ce qu'elle decide a la place de la politique
# ---------------------------------------------------------------------------------


def test_le_greedy_est_indifferent_des_le_premier_tour():
    """Au premier tour, aucune carte n'est encore dans un domaine : tout vaut zero.

    Ce n'est pas un defaut de la politique, c'est une propriete du jeu -- mais elle rend
    la regle de departage decisive, et un compteur de comportement mesure alors le
    departage. Le chiffre est etabli ici pour pouvoir etre cite.
    """
    from courtisans.engine import Engine

    etat = Engine(INSTANCE).reset(0)
    assert etat.phase() is Phase.POSE
    sommet, legales = Greedy().multiplicite_exaequo(etat)
    assert legales == 24
    assert sommet == legales, "attendu : toutes les poses ex aequo au premier tour"

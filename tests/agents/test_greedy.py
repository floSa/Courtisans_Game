"""Le greedy, sur des positions ou sa regle determine son coup.

Ecrits AVANT le greedy (regle 1 des conventions). Chaque attendu est calcule de tete depuis
la regle du paragraphe 7.1 des regles -- maximiser l'ecart de score obtenu sur le tour en
cours, comme si la partie s'arretait la -- jamais en appelant la fonction testee.

Deux positions comptent plus que les autres, et elles sont pre-inscrites au paragraphe 5.6
du document d'instrument :

  R-refus   : l'unique cible est son propre Noble d'une famille en Lumiere. Tout meurtre
              lui coute 2 points, donc refuser est STRICTEMENT meilleur. C'est le cas qui
              rend B4 mesurable, et qu'aucune politique de ce projet n'avait jamais su
              produire -- l'ancien `_pick_target_heuristic` ne rendait `None` que si la
              liste de cibles etait vide.
  R-meurtre : l'unique cible est un Noble d'une famille en Obscurite pose CHEZ LUI par un
              adversaire. Le tuer lui rend 2 points, donc tuer est strictement meilleur.
              Sans ce cas, un greedy qui refuserait toujours passerait R-refus.
"""

from __future__ import annotations

import random

import pytest

from courtisans import rules
from courtisans.cards import Position, Role
from mesure.instance import ENTRAINEMENT_3J
from tests.agents.outils_greedy import au_banquet, au_domaine, perception_de_ciblage

CONFIG = ENTRAINEMENT_3J


# ---------------------------------------------------------------------------------
# L'evaluation : l'ecart de score, sur ce que le decideur connait
# ---------------------------------------------------------------------------------


def test_l_evaluation_est_l_ecart_de_score_calcule_a_la_main():
    """Un plateau de quatre cartes, dont le decompte se fait de tete.

    Banquet : Noble f1 en Estime -> `d(f1) = +2` -> Lumiere. f0, f2, f3 sans carte au
    banquet -> Indifferentes (paragraphe 5 des regles).
    Domaines : Noble f1 chez 0 -> +2 pour le joueur 0 ; Neutre f1 chez 1 -> +1 pour le
    joueur 1 ; Neutre f0 chez 2 -> 0, f0 etant Indifferente.
    Scores : (2, 1, 0). Ecart du joueur 0 : `2 - max(1, 0) = 1`.
    """
    from agents.greedy import evaluer

    connues = (
        au_banquet(1, Role.NOBLE, Position.ESTIME, poseur=1),
        au_domaine(1, Role.NOBLE, proprietaire=0, poseur=0, exemplaire=1),
        au_domaine(1, Role.NEUTRE, proprietaire=1, poseur=0),
        au_domaine(0, Role.NEUTRE, proprietaire=2, poseur=1),
    )
    assert evaluer(connues, moi=0, config=CONFIG) == 1
    assert evaluer(connues, moi=1, config=CONFIG) == -1
    assert evaluer(connues, moi=2, config=CONFIG) == -2


def test_l_evaluation_compte_en_valeur_et_non_en_nombre_de_cartes():
    """2 Nobles en Estime contre 2 cartes standard en Disgrace : `d = 4 - 2 = +2`, Lumiere.

    C'est l'exemple du paragraphe 2.2 des regles, et le defaut numero 1 de son audit : une
    famille peut avoir autant de cartes de chaque cote sans etre Indifferente.
    """
    from agents.greedy import evaluer

    connues = (
        au_banquet(0, Role.NOBLE, Position.ESTIME, poseur=1),
        au_banquet(0, Role.NOBLE, Position.ESTIME, poseur=2, exemplaire=1),
        au_banquet(0, Role.NEUTRE, Position.DISGRACE, poseur=1),
        au_banquet(0, Role.GARDE, Position.DISGRACE, poseur=2),
        au_domaine(0, Role.NEUTRE, proprietaire=0, poseur=0, exemplaire=1),
    )
    assert evaluer(connues, moi=0, config=CONFIG) == 1


def test_l_evaluation_ignore_un_dos_adverse_et_c_est_la_regle_pas_un_defaut():
    """Le greedy traite une carte cachee comme absente (paragraphe 7.1 des regles).

    Vraie influence de f1 : Noble en Estime `+2`, deux Espions caches en Disgrace `-2`,
    donc `d = 0` -> **Indifferente**, et le Noble f1 du domaine 0 ne rapporte RIEN.
    Vue du greedy : il ne voit que le Noble -> `d = +2` -> Lumiere -> il croit valoir `+2`.

    Le cas asserte les deux nombres : l'ecart que le greedy calcule, et celui que la verite
    donne. Leur difference EST la myopie que M3 mesure.
    """
    from agents.greedy import evaluer

    connues = (
        au_banquet(1, Role.NOBLE, Position.ESTIME, poseur=1),
        au_domaine(1, Role.NOBLE, proprietaire=0, poseur=0, exemplaire=1),
    )
    caches = (
        au_banquet(1, Role.ESPION, Position.DISGRACE, poseur=1),
        au_banquet(1, Role.ESPION, Position.DISGRACE, poseur=2, exemplaire=1),
    )
    assert evaluer(connues, moi=0, config=CONFIG) == 2

    verite = connues + caches
    statuts = rules.statuts(verite, CONFIG.familles)
    assert statuts[1] is rules.Statut.INDIFFERENTE
    points = rules.points(verite, statuts, CONFIG.joueurs)
    assert points == [0, 0, 0]


# ---------------------------------------------------------------------------------
# R-refus et R-meurtre : les deux positions ou la regle tranche
# ---------------------------------------------------------------------------------


def _position_r_refus():
    """L'unique cible est le propre Noble du greedy, dans une famille en Lumiere.

    Banquet : Noble f1 en Estime -> f1 Lumiere.
    Domaine 0 : Noble f1 (a lui) -> `+2` ; Assassin f0 (a lui, en resolution) -> `0`,
    f0 n'ayant aucune carte au banquet donc etant Indifferente.
    Scores (2, 0, 0), ecart `+2`. Tuer le Noble : scores (0, 0, 0), ecart `0`.
    **Refuser est strictement meilleur.**
    """
    noble = au_domaine(1, Role.NOBLE, proprietaire=0, poseur=0, exemplaire=1)
    assassin = au_domaine(0, Role.ASSASSIN, proprietaire=0, poseur=0)
    connues = (au_banquet(1, Role.NOBLE, Position.ESTIME, poseur=1), noble, assassin)
    return perception_de_ciblage(connues, assassin, (noble,)), noble


def _position_r_meurtre():
    """L'unique cible est un Noble en Obscurite pose chez le greedy par un adversaire.

    Banquet : Noble f1 en **Disgrace** -> `d(f1) = -2` -> Obscurite.
    Domaine 0 : Noble f1 pose par le joueur 1 -> `-2` pour le joueur 0, qui encaisse en
    tant que proprietaire (paragraphe 5, point 3) ; Assassin f0 a lui -> `0`.
    Scores (-2, 0, 0), ecart `-2`. Tuer le Noble : scores (0, 0, 0), ecart `0`.
    **Tuer est strictement meilleur.**
    """
    noble = au_domaine(1, Role.NOBLE, proprietaire=0, poseur=1, exemplaire=1)
    assassin = au_domaine(0, Role.ASSASSIN, proprietaire=0, poseur=0)
    connues = (au_banquet(1, Role.NOBLE, Position.DISGRACE, poseur=1), noble, assassin)
    return perception_de_ciblage(connues, assassin, (noble,)), noble


def test_r_refus_le_greedy_doit_refuser_de_tuer():
    """Le cas sans lequel B4 est inmesurable, et qu'aucune politique du projet n'a produit."""
    from agents.greedy import choisir, evaluer, evaluer_actions

    perception, _ = _position_r_refus()
    assert evaluer(perception.connues, moi=0, config=CONFIG) == 2

    valeurs = evaluer_actions(perception)
    assert valeurs == {0: 0, 1: 2}, "tuer vaut 0, refuser vaut 2"

    refus = len(perception.cibles)
    for graine in range(20):
        assert choisir(perception, random.Random(graine)) == refus


def test_r_refus_est_un_refus_strict_et_non_un_departage():
    """Refuser doit etre STRICTEMENT meilleur que tout meurtre, pas a egalite avec lui.

    La distinction est le coeur du paragraphe 6.4 : un refus a egalite n'est pas un
    comportement, c'est un tirage au sort. Sans ce cas, B4-strict pourrait valoir 0 sans
    que rien ne le signale.
    """
    from agents.greedy import evaluer_actions

    perception, _ = _position_r_refus()
    valeurs = evaluer_actions(perception)
    refus = len(perception.cibles)
    meurtres = [valeur for action, valeur in valeurs.items() if action != refus]
    assert meurtres, "la position doit offrir au moins un meurtre, sinon elle ne teste rien"
    assert all(valeur < valeurs[refus] for valeur in meurtres)


def test_r_meurtre_le_greedy_doit_tuer():
    """Le contre-cas : sans lui, un greedy qui refuse toujours passerait R-refus."""
    from agents.greedy import choisir, evaluer_actions

    perception, _ = _position_r_meurtre()
    valeurs = evaluer_actions(perception)
    assert valeurs == {0: 0, 1: -2}, "tuer vaut 0, refuser vaut -2"
    for graine in range(20):
        assert choisir(perception, random.Random(graine)) == 0


def test_tuer_un_dos_vaut_exactement_refuser():
    """Un dos vaut zero dans la vue du greedy, donc le tuer ne change pas son ecart.

    C'est la raison pour laquelle B4 publie DEUX nombres. Ici les deux actions sont a
    egalite, et le departage tranche : ce refus-la, quand il survient, est un tirage au
    sort et non un comportement.
    """
    from agents.greedy import evaluer_actions

    noble = au_domaine(1, Role.NOBLE, proprietaire=0, poseur=0, exemplaire=1)
    assassin = au_banquet(0, Role.ASSASSIN, Position.ESTIME, poseur=0)
    connues = (au_banquet(1, Role.NOBLE, Position.ESTIME, poseur=1), noble, assassin)
    perception = perception_de_ciblage(connues, assassin, (), dos_cibles=1)

    valeurs = evaluer_actions(perception)
    assert len(valeurs) == 2, "un dos et le refus"
    assert valeurs[0] == valeurs[1], "tuer un dos et refuser ont la meme valeur"


def test_le_greedy_prefere_le_meilleur_meurtre_parmi_plusieurs():
    """Trois cibles de valeurs differentes : il prend celle qui maximise l'ecart.

    Banquet : Noble f1 en Estime (f1 Lumiere), Noble f2 en Disgrace (f2 Obscurite).
    Domaine 1 -- celui d'un adversaire -- contient un Noble f1 (`+2` pour le joueur 1), un
    Neutre f1 (`+1`), un Noble f2 (`-2`), et l'Assassin f3 du greedy (`0`, f3 Indifferente) :
    le joueur 1 vaut `+1`. Domaine 2 : un Neutre f2, donc le joueur 2 vaut `-1`.
    Scores (0, 1, -1), ecart du greedy `0 - max(1, -1) = -1`.

    | Coup | Scores | Ecart du greedy |
    |---|---|---|
    | tuer le Noble f1 | (0, -1, -1) | `0 - (-1) = +1` |
    | tuer le Neutre f1 | (0, 0, -1) | `0 - 0 = 0` |
    | tuer le Noble f2 de chez 1 | (0, 3, -1) | `0 - 3 = -3` |
    | refuser | (0, 1, -1) | `-1` |

    **Le meilleur coup est de tuer le Noble f1**, valeur `+1`, et il est strict.

    Le joueur 2 a `-1` et non `0` **pour une raison** : a `0` il plafonnerait le `max` des
    adversaires, tuer le Noble f1 ne rendrait plus que `0`, et deux coups seraient a egalite.
    Mon premier attendu l'avait oublie -- l'ecart se mesure au MEILLEUR adversaire, pas a
    celui qu'on vise.
    """
    from agents.greedy import choisir, evaluer_actions

    noble_f1 = au_domaine(1, Role.NOBLE, proprietaire=1, poseur=1, exemplaire=1)
    neutre_f1 = au_domaine(1, Role.NEUTRE, proprietaire=1, poseur=2)
    noble_f2 = au_domaine(2, Role.NOBLE, proprietaire=1, poseur=0, exemplaire=1)
    assassin = au_domaine(3, Role.ASSASSIN, proprietaire=1, poseur=0)
    connues = (
        au_banquet(1, Role.NOBLE, Position.ESTIME, poseur=1),
        au_banquet(2, Role.NOBLE, Position.DISGRACE, poseur=2),
        noble_f1,
        neutre_f1,
        noble_f2,
        au_domaine(2, Role.NEUTRE, proprietaire=2, poseur=0),
        assassin,
    )
    perception = perception_de_ciblage(connues, assassin, (noble_f1, neutre_f1, noble_f2))
    assert evaluer_actions(perception) == {0: 1, 1: 0, 2: -3, 3: -1}
    for graine in range(10):
        assert choisir(perception, random.Random(graine)) == 0


def test_un_garde_n_est_jamais_une_cible():
    """Le Garde est immunise (paragraphe 4.3). C'est le moteur qui l'exclut, pas le greedy.

    Le cas verifie que la regle est bien celle du moteur et non une reimplementation : la
    liste de cibles vient de `rules.cibles_valides`, dont l'exclusion du Garde est testee
    par le controle C6.
    """
    garde = au_domaine(1, Role.GARDE, proprietaire=0, poseur=0)
    assassin = au_domaine(1, Role.ASSASSIN, proprietaire=0, poseur=0)
    cibles = rules.cibles_valides((garde, assassin), assassin)
    assert cibles == ()


# ---------------------------------------------------------------------------------
# Le departage
# ---------------------------------------------------------------------------------


def test_le_departage_aleatoire_couvre_tout_l_ensemble_des_argmax():
    """Deux dos et un refus, tous a egalite : les trois actions doivent sortir.

    Un departage par plus petit indice ne rendrait jamais que l'action 0, ce qui
    fabriquerait un artefact dans B4 et, sur les poses, dans B2, B3 et B6 -- l'indice d'une
    action de pose encodant l'assignation, la position au banquet et l'adversaire vise.
    """
    from agents.greedy import choisir

    assassin = au_banquet(0, Role.ASSASSIN, Position.ESTIME, poseur=0)
    perception = perception_de_ciblage((assassin,), assassin, (), dos_cibles=2)
    tirages = {choisir(perception, random.Random(graine)) for graine in range(200)}
    assert tirages == {0, 1, 2}


def test_le_departage_par_plus_petit_indice_est_deterministe_et_biaise():
    """La variante de robustesse : reproductible, et c'est son seul interet."""
    from agents.greedy import choisir_par_plus_petit_indice

    assassin = au_banquet(0, Role.ASSASSIN, Position.ESTIME, poseur=0)
    perception = perception_de_ciblage((assassin,), assassin, (), dos_cibles=2)
    assert choisir_par_plus_petit_indice(perception) == 0


def test_le_departage_ne_choisit_jamais_hors_des_argmax():
    """Sur R-refus, aucune graine ne doit faire tuer : l'egalite n'existe pas la."""
    from agents.greedy import choisir

    perception, _ = _position_r_refus()
    refus = len(perception.cibles)
    assert {choisir(perception, random.Random(g)) for g in range(200)} == {refus}


def test_choisir_refuse_une_action_hors_des_legales():
    """Une `Perception` incoherente doit lever, pas rendre un coup illegal."""
    from agents.perception import Perception

    perception, _ = _position_r_refus()
    from dataclasses import replace

    boiteuse: Perception = replace(perception, actions_legales=())
    from agents.greedy import choisir

    with pytest.raises(ValueError, match="aucune action legale"):
        choisir(boiteuse, random.Random(0))

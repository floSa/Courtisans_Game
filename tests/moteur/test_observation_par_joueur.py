"""Une observation appartient a un joueur -- jamais a un identifiant reserve.

Le paragraphe 4 de `03_specification_moteur.md` ecrit la signature
`information_state_string(self, player: int)`, et l'invariant I7 la lit « la vue de `p` ».
Une observation est donc **la vue d'un siege**, et `player` doit en designer un.

Or `current_player()` rend des identifiants **reserves** des qu'aucun joueur ne decide :
`JOUEUR_HASARD` sur un noeud de distribution, `JOUEUR_TERMINAL` a la fin. Passes comme
`player`, ils ne levent rien : en Python, `mains[-1]` est le dernier joueur, `mains[-4]`
est le joueur 0 quand il y en a quatre, et une position relative calculee depuis -1 ne
correspond a aucun siege. Le moteur rend alors une observation **bien formee, plausible,
qui n'est la vue de personne** -- la famille exacte de defaut qui a survecu cinq briques
d'entrainement et un rapport de 2 695 lignes (`02_audit_conformite.md`).

Ce fichier exige donc un refus explicite pour tout identifiant qui n'est pas un siege :
les deux reserves, et un indice hors bornes. Le dernier test est le garde-fou de
l'ensemble : refuser **tout** serait aussi faux, les `n` vues reelles doivent continuer
d'etre rendues, et elles doivent etre distinctes -- sinon la comparaison n'aurait rien
prouve.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    construire,
    noms,
)

#: Cartes posees a partir desquelles on considere etre « en milieu de partie » : un tour de
#: table entier, donc des mains et des domaines deja differencies d'un joueur a l'autre.
POSEES_MINIMUM = 3


def _identifiants_refuses(instance: Instance) -> list[int]:
    """Tout ce qui n'est pas un siege : les deux reserves, et les hors-bornes.

    `-1` et `-4` sont les identifiants d'OpenSpiel repris par le coeur ; `-2` couvre le
    cas ou un troisieme identifiant reserve apparaitrait ; `joueurs` est le premier indice
    hors bornes par le haut.
    """
    return [-1, -2, -4, instance.joueurs, instance.joueurs + 1, 99]


def _avancer_jusqu_a_un_noeud_de_chance(moteur: object, seed: int) -> object:
    """Un noeud de distribution en milieu de partie, ou les vues sont differenciees.

    La racine ne convient pas : mains vides et plateau vide, les `n` vues y sont
    identiques par symetrie, donc une observation fausse pourrait s'y confondre avec une
    vraie sans que rien ne le montre.
    """
    etat = moteur.reset_par_hasard()
    rng = random.Random(seed)
    while not etat.is_terminal():
        if (
            etat.phase().name == "CHANCE"
            and len(etat.vue_privilegiee().posees) >= POSEES_MINIMUM
        ):
            return etat
        etat.apply(rng.choice(actions_legales(etat)))
    raise AssertionError("aucun noeud de chance en milieu de partie sur cette partie")


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_un_identifiant_reserve_est_refuse_sur_un_noeud_de_chance(
    instance: Instance,
) -> None:
    """Le chemin le plus normal qui soit : `reset_par_hasard()` rend un noeud de chance."""
    _, moteur = construire(instance)
    etat = _avancer_jusqu_a_un_noeud_de_chance(moteur, seed=0)

    assert etat.phase().name == "CHANCE"
    assert etat.current_player() < 0, "un noeud de chance n'appartient a aucun joueur"

    for identifiant in _identifiants_refuses(instance):
        with pytest.raises(ValueError):
            etat.information_state_string(identifiant)
        with pytest.raises(ValueError):
            etat.information_state_tensor(identifiant)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_un_identifiant_reserve_est_refuse_au_terminal(instance: Instance) -> None:
    """Au terminal le defaut change de forme selon le nombre de joueurs -- `IndexError` a
    2 et 3 joueurs, une observation complete a 4, ou `mains[-4]` designe le joueur 0. Un
    comportement qui depend du nombre de joueurs n'est pas un comportement."""
    _, moteur = construire(instance)
    etat = moteur.reset(0)
    rng = random.Random(0)
    while not etat.is_terminal():
        etat.apply(rng.choice(actions_legales(etat)))

    assert etat.current_player() < 0

    for identifiant in _identifiants_refuses(instance):
        with pytest.raises(ValueError):
            etat.information_state_string(identifiant)
        with pytest.raises(ValueError):
            etat.information_state_tensor(identifiant)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_un_indice_hors_bornes_est_refuse_en_phase_de_decision(
    instance: Instance,
) -> None:
    """Meme la ou un joueur decide, `player` doit designer un siege existant."""
    _, moteur = construire(instance)
    etat = moteur.reset(1)

    assert etat.phase().name == "POSE"

    for identifiant in _identifiants_refuses(instance):
        with pytest.raises(ValueError):
            etat.information_state_string(identifiant)
        with pytest.raises(ValueError):
            etat.information_state_tensor(identifiant)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_les_vues_des_joueurs_sont_rendues_et_distinctes_sur_un_noeud_de_chance(
    instance: Instance,
) -> None:
    """Garde-fou : refuser tout serait aussi faux que tout accepter.

    Les `n` observations reelles doivent rester rendues sur un noeud de chance -- une
    politique doit pouvoir lire la vue d'un joueur quel que soit le noeud -- et elles
    doivent etre **distinctes** deux a deux. Sans cette distinction, exiger qu'une
    observation soit celle d'un joueur ne prouverait rien : n'importe quelle valeur
    conviendrait.
    """
    _, moteur = construire(instance)
    etat = _avancer_jusqu_a_un_noeud_de_chance(moteur, seed=0)

    chaines = [etat.information_state_string(j) for j in range(instance.joueurs)]
    tenseurs = [tuple(etat.information_state_tensor(j)) for j in range(instance.joueurs)]

    assert all(chaine for chaine in chaines)
    assert len(set(chaines)) == instance.joueurs, (
        f"{instance.nom} : {len(set(chaines))} vues distinctes pour "
        f"{instance.joueurs} joueurs"
    )
    assert len(set(tenseurs)) == instance.joueurs
    assert len({len(tenseur) for tenseur in tenseurs}) == 1, "tenseurs de tailles inegales"

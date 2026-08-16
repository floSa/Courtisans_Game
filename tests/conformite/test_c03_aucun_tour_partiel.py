"""C3 -- 01_regles.md paragraphes 3.2 et 3.4.

« Aucun tour partiel : tout tour joue comporte exactement 3 cartes. »

Trois controles, du plus local au plus global :
  - au moment de decider, le joueur a exactement 3 cartes en main (paragraphes 3.2 et 3.3) ;
  - une pose ajoute exactement 3 cartes au plateau ;
  - a la fin, il a ete pose exactement 3 x joueurs x tours cartes (paragraphe 3.4).
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    NB_PARTIES_COURT,
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    construire,
    nb_placees,
    noms,
)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c03_tout_tour_joue_comporte_exactement_trois_cartes(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_PARTIES_COURT):
        etat = moteur.reset(seed)
        rng = random.Random(seed)
        poses = 0

        while not etat.is_terminal():
            phase = etat.phase().name
            avant = nb_placees(etat.vue_privilegiee())

            if phase == "POSE":
                joueur = etat.current_player()
                main = etat.vue_privilegiee().mains[joueur]
                assert len(main) == 3, (
                    f"{instance.nom}, seed {seed} : le joueur {joueur} pose avec "
                    f"{len(main)} cartes en main"
                )

            etat.apply(rng.choice(actions_legales(etat)))

            if phase == "POSE":
                poses += 1
                apres = nb_placees(etat.vue_privilegiee())
                assert apres == avant + 3, (
                    f"{instance.nom}, seed {seed} : une pose a place {apres - avant} cartes"
                )

        assert poses == instance.joueurs * instance.tours
        assert nb_placees(etat.vue_privilegiee()) == instance.cartes_jouees, (
            f"{instance.nom}, seed {seed} : {nb_placees(etat.vue_privilegiee())} cartes "
            f"posees au lieu de 3 x {instance.joueurs} x {instance.tours} = "
            f"{instance.cartes_jouees}"
        )

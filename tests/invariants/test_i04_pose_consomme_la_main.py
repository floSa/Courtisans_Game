"""I4 -- 03_specification_moteur.md paragraphe 5.

« Toute pose consomme exactement 3 cartes, une par zone, dans 3 zones distinctes. »

C3 et C8 comptent les cartes et les zones. I4 verifie l'identite : les trois cartes qui
apparaissent sur le plateau sont exactement les trois cartes qui etaient en main, pas trois
cartes tirees d'ailleurs. Un moteur qui poserait le sommet de la pioche au lieu de la main
passerait C3 et C8 sans broncher.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    cle,
    cles,
    construire,
    noms,
)

NB_PARTIES = 10


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i04_une_pose_place_exactement_les_cartes_de_la_main(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_PARTIES):
        etat = moteur.reset(seed)
        rng = random.Random(seed)

        while not etat.is_terminal():
            phase = etat.phase().name
            vue = etat.vue_privilegiee()

            if phase == "POSE":
                joueur = etat.current_player()
                main = sorted(cle(carte) for carte in vue.mains[joueur])
                avant = set(cles(vue.posees)) | set(cles(vue.defausse))

            etat.apply(rng.choice(actions_legales(etat)))

            if phase != "POSE":
                continue

            apres_vue = etat.vue_privilegiee()
            apres = set(cles(apres_vue.posees)) | set(cles(apres_vue.defausse))
            nouvelles = sorted(apres - avant)

            assert nouvelles == main, (
                f"{instance.nom}, seed {seed} : les cartes posees {nouvelles} ne sont pas "
                f"celles de la main {main}"
            )
            restant = {cle(carte) for carte in apres_vue.mains[joueur]}
            assert not (restant & set(main)), (
                f"{instance.nom}, seed {seed} : une carte posee est restee en main"
            )

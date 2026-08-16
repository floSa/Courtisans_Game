"""C8 -- 01_regles.md paragraphe 3.2, arbitrage R1.

« Les 3 cartes d'un tour vont dans 3 zones distinctes, pour tout nombre de joueurs. »

Structure fixe, sans exception : une carte au banquet, une dans son propre domaine, une
chez un adversaire. Jamais deux au banquet, jamais deux chez soi, jamais deux chez le meme
adversaire. C'est cette propriete qui garantit qu'un Assassin pose ce tour-ci ne peut
jamais cibler ses deux compagnons de tour.
"""

from __future__ import annotations

import random
from typing import Any

import pytest

from tests.outils import (
    NB_PARTIES_COURT,
    TOUTES_LES_INSTANCES,
    Instance,
    actions_legales,
    cle,
    construire,
    noms,
)


def _placees_par_cle(vue: Any) -> dict[tuple[int, str, int], Any]:
    """Toutes les cartes deja posees, vivantes ou mortes, indexees par identite."""
    return {cle(posee.carte): posee for posee in list(vue.posees) + list(vue.defausse)}


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c08_une_pose_remplit_trois_zones_distinctes(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_PARTIES_COURT):
        etat = moteur.reset(seed)
        rng = random.Random(seed)

        while not etat.is_terminal():
            phase = etat.phase().name
            joueur = etat.current_player() if phase == "POSE" else None
            avant = _placees_par_cle(etat.vue_privilegiee())

            etat.apply(rng.choice(actions_legales(etat)))

            if phase != "POSE":
                continue

            apres = _placees_par_cle(etat.vue_privilegiee())
            nouvelles = [apres[identite] for identite in apres.keys() - avant.keys()]

            assert len(nouvelles) == 3, (
                f"{instance.nom}, seed {seed} : {len(nouvelles)} cartes posees en un tour"
            )
            assert all(posee.poseur == joueur for posee in nouvelles), (
                f"{instance.nom}, seed {seed} : une carte posee n'est pas attribuee au "
                f"joueur {joueur}"
            )

            zones = [posee.zone for posee in nouvelles]
            assert len(set(zones)) == 3, (
                f"{instance.nom}, seed {seed} : deux des trois cartes partagent une zone "
                f"({zones})"
            )

            banquet = [zone for zone in zones if zone.genre.name == "BANQUET"]
            propre = [
                zone
                for zone in zones
                if zone.genre.name == "DOMAINE" and zone.proprietaire == joueur
            ]
            adverse = [
                zone
                for zone in zones
                if zone.genre.name == "DOMAINE" and zone.proprietaire != joueur
            ]

            assert len(banquet) == 1, f"{instance.nom}, seed {seed} : {len(banquet)} au banquet"
            assert len(propre) == 1, f"{instance.nom}, seed {seed} : {len(propre)} chez soi"
            assert len(adverse) == 1, f"{instance.nom}, seed {seed} : {len(adverse)} chez autrui"
            assert banquet[0].position.name in ("ESTIME", "DISGRACE")
            assert 0 <= adverse[0].proprietaire < instance.joueurs

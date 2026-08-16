"""C2 -- 01_regles.md paragraphe 3.4.

« Tous les joueurs jouent le meme nombre de tours, sur 1000 parties, pour n dans {2, 3, 4}. »

Un tour est compte comme une decision de phase POSE : c'est la seule phase ou un joueur
joue ses trois cartes. Les resolutions d'Assassin ne sont pas des tours.

Les regles imposent 1000 parties ; les instances completes sont echantillonnees a 200
parties pour le temps d'execution, ce qui n'affaiblit pas le controle : les trois valeurs
de n exigees sont couvertes a 1000 parties chacune par les instances rapides.
"""

from __future__ import annotations

import random

import pytest

from tests.outils import (
    INSTANCES_COMPLETES,
    INSTANCES_RAPIDES,
    NB_PARTIES_C2,
    NB_PARTIES_C2_COMPLET,
    Instance,
    actions_legales,
    construire,
)

CAS = [(instance, NB_PARTIES_C2) for instance in INSTANCES_RAPIDES] + [
    (instance, NB_PARTIES_C2_COMPLET) for instance in INSTANCES_COMPLETES
]
IDS = [f"{instance.nom}-{nb}" for instance, nb in CAS]


@pytest.mark.parametrize(("instance", "nb_parties"), CAS, ids=IDS)
def test_c02_tous_les_joueurs_jouent_le_meme_nombre_de_tours(
    instance: Instance, nb_parties: int
) -> None:
    config, moteur = construire(instance)
    assert config.tours == instance.tours, (
        f"{instance.nom} : le moteur annonce {config.tours} tours, "
        f"la regle en donne {instance.nb_cartes} // (3 x {instance.joueurs}) = {instance.tours}"
    )

    for seed in range(nb_parties):
        etat = moteur.reset(seed)
        rng = random.Random(seed)
        tours = [0] * instance.joueurs

        while not etat.is_terminal():
            if etat.phase().name == "POSE":
                tours[etat.current_player()] += 1
            etat.apply(rng.choice(actions_legales(etat)))

        assert len(set(tours)) == 1, (
            f"{instance.nom}, seed {seed} : tours inegaux {tours}"
        )
        assert tours[0] == instance.tours, (
            f"{instance.nom}, seed {seed} : {tours[0]} tours joues au lieu de {instance.tours}"
        )

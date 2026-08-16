"""C14 -- 01_regles.md paragraphe 3.2.

« L'espace d'actions de pose vaut 6 x 2 x (n - 1), chaque action decodant vers une
assignation distincte. »

  - 6 = 3! assignations des trois cartes de la main aux trois zones ;
  - 2 = Estime ou Disgrace ;
  - n - 1 = quel adversaire recoit la troisieme carte.

Deuxieme controle : deux actions legales ne doivent jamais poser les memes cartes aux
memes endroits. Quand la main contient deux cartes identiques, les 6 permutations
degenerent, et les doublons doivent etre masques.
"""

from __future__ import annotations

from itertools import permutations
from typing import Any

import pytest

from tests.outils import (
    NB_PARTIES_COURT,
    TOUTES_LES_INSTANCES,
    Instance,
    cle,
    construire,
    construire_config,
    module,
    noms,
    parcourir_decisions,
)


def _signature(pose: Any) -> tuple[tuple[int, int, int], str, int]:
    return (tuple(pose.indices_main), pose.position.name, pose.adversaire_relatif)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c14_l_espace_de_pose_est_une_bijection(instance: Instance) -> None:
    config = construire_config(instance)  # ce controle ne joue pas : il n'a pas besoin du moteur
    rules = module("rules")

    assert config.actions_de_pose == instance.actions_de_pose, (
        f"{instance.nom} : {config.actions_de_pose} actions de pose au lieu de "
        f"6 x 2 x ({instance.joueurs} - 1) = {instance.actions_de_pose}"
    )

    decodees = {}
    for action in range(config.actions_de_pose):
        pose = rules.decoder_action_pose(action, config)
        assert sorted(pose.indices_main) == [0, 1, 2], (
            f"{instance.nom}, action {action} : {pose.indices_main} n'est pas une "
            f"permutation des trois cartes de la main"
        )
        assert pose.position.name in ("ESTIME", "DISGRACE")
        assert 0 <= pose.adversaire_relatif <= instance.joueurs - 2
        signature = _signature(pose)
        assert signature not in decodees, (
            f"{instance.nom} : les actions {decodees[signature]} et {action} decodent "
            f"toutes deux vers {signature}"
        )
        decodees[signature] = action

    attendues = {
        (assignation, position, adversaire)
        for assignation in permutations((0, 1, 2))
        for position in ("ESTIME", "DISGRACE")
        for adversaire in range(instance.joueurs - 1)
    }
    assert set(decodees) == attendues, (
        f"{instance.nom} : le decodage ne couvre pas exactement "
        f"assignations x positions x adversaires"
    )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c14_deux_actions_legales_ne_posent_jamais_les_memes_cartes(
    instance: Instance,
) -> None:
    config, moteur = construire(instance)
    rules = module("rules")

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_COURT):
        if etat.phase().name != "POSE":
            continue

        actions = list(etat.legal_actions())
        assert set(actions) <= set(range(config.actions_de_pose)), (
            f"{instance.nom}, seed {seed} : action de pose hors de l'espace declare"
        )

        main = etat.vue_privilegiee().mains[etat.current_player()]
        vues = {}
        for action in actions:
            pose = rules.decoder_action_pose(action, config)
            placement = (
                tuple(cle(main[indice]) for indice in pose.indices_main),
                pose.position.name,
                pose.adversaire_relatif,
            )
            assert placement not in vues, (
                f"{instance.nom}, seed {seed} : les actions {vues[placement]} et {action} "
                f"posent les memes cartes aux memes endroits -- doublon non masque"
            )
            vues[placement] = action

"""C7 -- 01_regles.md paragraphe 4.1.

« Un Assassin peut cibler un Espion cache et un autre Assassin. »

C6 verifie la formule des cibles ; C7 verifie que les deux cas interessants se produisent
reellement -- un Espion pose par un autre joueur, donc dont le tueur ignore l'identite, et
un second Assassin -- et qu'ils sont effectivement tuables. Sans ce controle d'occurrence,
une formule correcte mais jamais exercee passerait pour verifiee.

Le Garde sert ici de temoin negatif : sur le meme echantillon, aucun Garde ne doit mourir.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    construire,
    noms,
    parcourir_decisions,
    partie,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c07_un_espion_cache_et_un_autre_assassin_sont_ciblables(instance: Instance) -> None:
    _, moteur = construire(instance)
    espions_caches = 0
    autres_assassins = 0

    for _seed, etat in parcourir_decisions(moteur, NB_PARTIES_BALAYAGE):
        if etat.phase().name != "CIBLAGE":
            continue
        joueur = etat.current_player()
        for cible in etat.cibles_courantes():
            if cible.carte.role.name == "ESPION" and cible.poseur != joueur:
                espions_caches += 1
            if cible.carte.role.name == "ASSASSIN":
                autres_assassins += 1

    assert espions_caches > 0, (
        f"{instance.nom} : aucun Espion adverse jamais propose comme cible sur "
        f"{NB_PARTIES_BALAYAGE} parties"
    )
    assert autres_assassins > 0, (
        f"{instance.nom} : aucun autre Assassin jamais propose comme cible sur "
        f"{NB_PARTIES_BALAYAGE} parties"
    )


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c07_un_espion_et_un_assassin_sont_effectivement_tuables(instance: Instance) -> None:
    _, moteur = construire(instance)
    tues_par_role: dict[str, int] = {}

    for seed in range(NB_PARTIES_BALAYAGE):
        for morte in partie(moteur, seed).vue_privilegiee().defausse:
            role = morte.carte.role.name
            tues_par_role[role] = tues_par_role.get(role, 0) + 1

    assert tues_par_role.get("ESPION", 0) > 0, (
        f"{instance.nom} : aucun Espion tue -- morts par role : {tues_par_role}"
    )
    assert tues_par_role.get("ASSASSIN", 0) > 0, (
        f"{instance.nom} : aucun Assassin tue -- morts par role : {tues_par_role}"
    )
    assert tues_par_role.get("GARDE", 0) == 0, (
        f"{instance.nom} : un Garde a ete tue alors qu'il est immunise (paragraphe 4.3) -- "
        f"morts par role : {tues_par_role}"
    )

"""I1 -- 03_specification_moteur.md paragraphe 5.

« Toute carte est a exactement un endroit : pioche, main d'un joueur, plateau vivant, ou
morte. Jamais deux, jamais zero. »

Le controle est fait a CHAQUE noeud, pas seulement au debut et a la fin : une carte
dupliquee le temps d'une resolution d'Assassin, puis recollee, ne laisserait aucune trace
dans un controle aux extremites.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    cartes_presentes,
    construire,
    noms,
    paquet_attendu,
    parcourir_decisions,
    partie,
)

NB_PARTIES = 10


def _controler(vue, instance: Instance, ou: str) -> None:
    presentes = cartes_presentes(vue)
    attendues = sorted(paquet_attendu(instance))

    assert len(presentes) == len(set(presentes)), (
        f"{instance.nom}, {ou} : une carte est a deux endroits a la fois -- "
        f"{len(presentes)} emplacements pour {len(set(presentes))} cartes distinctes"
    )
    assert sorted(presentes) == attendues, (
        f"{instance.nom}, {ou} : {len(presentes)} cartes localisees au lieu de "
        f"{instance.nb_cartes}"
    )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i01_chaque_carte_est_a_exactement_un_endroit(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        _controler(etat.vue_privilegiee(), instance, f"seed {seed}, phase {etat.phase().name}")

    for seed in range(NB_PARTIES):
        _controler(partie(moteur, seed).vue_privilegiee(), instance, f"seed {seed}, terminal")


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i01_les_quatre_emplacements_sont_disjoints(instance: Instance) -> None:
    """Controle explicite du recouvrement, emplacement par emplacement."""
    _, moteur = construire(instance)

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        vue = etat.vue_privilegiee()
        emplacements = {
            "pioche": {(carte.famille, carte.role.name, carte.exemplaire) for carte in vue.pioche},
            "plateau": {
                (posee.carte.famille, posee.carte.role.name, posee.carte.exemplaire)
                for posee in vue.posees
            },
            "defausse": {
                (posee.carte.famille, posee.carte.role.name, posee.carte.exemplaire)
                for posee in vue.defausse
            },
        }
        for joueur, main in enumerate(vue.mains):
            emplacements[f"main {joueur}"] = {
                (carte.famille, carte.role.name, carte.exemplaire) for carte in main
            }

        noms_emplacements = sorted(emplacements)
        for i, gauche in enumerate(noms_emplacements):
            for droite in noms_emplacements[i + 1 :]:
                commun = emplacements[gauche] & emplacements[droite]
                assert not commun, (
                    f"{instance.nom}, seed {seed} : {len(commun)} carte(s) a la fois en "
                    f"{gauche} et en {droite} -- {sorted(commun)[:3]}"
                )

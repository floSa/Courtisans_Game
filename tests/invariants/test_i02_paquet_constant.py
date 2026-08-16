"""I2 -- 03_specification_moteur.md paragraphe 5.

« Le paquet contient toujours familles x nb_roles x exemplaires cartes. Aucune n'est
retiree avant le melange. »

I1 verifie que les cartes sont bien rangees ; I2 verifie que leur nombre ne bouge jamais et
que les flux vont dans le bon sens : la pioche ne fait que decroitre, la defausse ne fait
que croitre, une carte posee ne retourne jamais en main.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    cartes_presentes,
    cles,
    construire,
    noms,
    parcourir_decisions,
)

NB_PARTIES = 10


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i02_la_taille_du_paquet_est_celle_de_la_configuration(instance: Instance) -> None:
    config, moteur = construire(instance)

    attendu = instance.familles * len(instance.roles) * instance.exemplaires
    assert config.nb_cartes == attendu, (
        f"{instance.nom} : nb_cartes = {config.nb_cartes} au lieu de "
        f"{instance.familles} x {len(instance.roles)} x {instance.exemplaires} = {attendu}"
    )

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        total = len(cartes_presentes(etat.vue_privilegiee()))
        assert total == attendu, (
            f"{instance.nom}, seed {seed} : {total} cartes en jeu au lieu de {attendu}"
        )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i02_les_flux_de_cartes_sont_a_sens_unique(instance: Instance) -> None:
    _, moteur = construire(instance)
    seed_courant = -1
    pioche_precedente = 0
    mortes_precedentes: set = set()
    posees_precedentes: set = set()

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        vue = etat.vue_privilegiee()
        if seed != seed_courant:
            seed_courant = seed
            pioche_precedente = len(vue.pioche)
            mortes_precedentes = set()
            posees_precedentes = set()

        assert len(vue.pioche) <= pioche_precedente, (
            f"{instance.nom}, seed {seed} : la pioche a grossi, de {pioche_precedente} a "
            f"{len(vue.pioche)}"
        )
        mortes = set(cles(vue.defausse))
        assert mortes_precedentes <= mortes, (
            f"{instance.nom}, seed {seed} : une carte est sortie de la defausse"
        )
        posees = set(cles(vue.posees)) | mortes
        assert posees_precedentes <= posees, (
            f"{instance.nom}, seed {seed} : une carte posee a quitte le plateau autrement "
            f"que par la defausse"
        )
        en_main = {
            (carte.famille, carte.role.name, carte.exemplaire)
            for main in vue.mains
            for carte in main
        }
        assert not (posees & en_main), (
            f"{instance.nom}, seed {seed} : une carte posee est revenue en main"
        )

        pioche_precedente = len(vue.pioche)
        mortes_precedentes = mortes
        posees_precedentes = posees

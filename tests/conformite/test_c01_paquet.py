"""C1 -- 01_regles.md paragraphe 3.1.

« Le paquet compte familles x roles x exemplaires cartes ; aucune n'est retiree avant le
melange. »

Le controle porte sur le multiensemble de toutes les cartes presentes, ou qu'elles soient :
il ne suppose donc rien sur le moment ou la premiere main est distribuee.
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
)

SEEDS = (0, 1, 7)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c01_le_paquet_est_complet_au_debut(instance: Instance) -> None:
    config, moteur = construire(instance)

    assert config.nb_cartes == instance.nb_cartes

    for seed in SEEDS:
        etat = moteur.reset(seed)
        vue = etat.vue_privilegiee()
        presentes = sorted(cartes_presentes(vue))

        assert len(presentes) == instance.nb_cartes, (
            f"{instance.nom} : {len(presentes)} cartes en jeu au lieu de {instance.nb_cartes}"
        )
        assert presentes == sorted(paquet_attendu(instance)), (
            f"{instance.nom} : le paquet distribue n'est pas familles x roles x exemplaires"
        )
        assert len(set(presentes)) == len(presentes), (
            f"{instance.nom} : une carte apparait en double"
        )


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c01_aucune_carte_n_est_retiree_pendant_la_partie(instance: Instance) -> None:
    """Corollaire : une carte tuee reste dans le jeu, a la defausse (paragraphe 4.1)."""
    import random

    _, moteur = construire(instance)
    etat = moteur.reset(0)
    rng = random.Random(0)
    attendu = sorted(paquet_attendu(instance))

    while not etat.is_terminal():
        assert sorted(cartes_presentes(etat.vue_privilegiee())) == attendu
        etat.apply(rng.choice(list(etat.legal_actions())))

    assert sorted(cartes_presentes(etat.vue_privilegiee())) == attendu

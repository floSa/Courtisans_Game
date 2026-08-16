"""I6 -- 03_specification_moteur.md paragraphe 5.

« Une carte morte n'intervient ni dans l'influence des familles, ni dans les points. »

C9 verifie la moitie decompte. I6 verifie la moitie permanence, qui est celle qu'un moteur
peut rater sans que le score bouge tout de suite : une carte tuee ne revient jamais sur le
plateau, ne redevient jamais une cible, et le nombre de morts ne diminue jamais.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    Instance,
    cle,
    cles,
    construire,
    noms,
    parcourir_decisions,
)

NB_PARTIES = 50


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_i06_une_carte_morte_le_reste_et_n_est_plus_ciblable(instance: Instance) -> None:
    _, moteur = construire(instance)
    seed_courant = -1
    deja_mortes: set = set()
    total_morts = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES):
        if seed != seed_courant:
            seed_courant = seed
            deja_mortes = set()

        vue = etat.vue_privilegiee()
        mortes = set(cles(vue.defausse))

        assert deja_mortes <= mortes, (
            f"{instance.nom}, seed {seed} : une carte tuee a quitte la defausse -- "
            f"{sorted(deja_mortes - mortes)}"
        )
        vivantes = set(cles(vue.posees))
        assert not (mortes & vivantes), (
            f"{instance.nom}, seed {seed} : une carte morte est aussi vivante sur le plateau"
        )

        if etat.phase().name == "CIBLAGE":
            for cible in etat.cibles_courantes():
                assert cle(cible.carte) not in mortes, (
                    f"{instance.nom}, seed {seed} : une carte deja morte est proposee comme "
                    f"cible"
                )

        deja_mortes = mortes
        total_morts = max(total_morts, len(mortes))

    assert total_morts > 0, (
        f"{instance.nom} : aucune carte tuee sur {NB_PARTIES} parties, l'invariant n'est "
        f"jamais exerce"
    )

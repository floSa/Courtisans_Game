"""C4 -- 01_regles.md paragraphe 3.4.

« Le nombre de cartes restees en pioche vaut nb_cartes mod 3n. »

Corollaire teste en meme temps : ces cartes ne sont jamais piochees ni revelees, donc
elles sont encore dans la pioche a l'etat terminal, et elles n'ont jamais ete en main.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    NB_PARTIES_COURT,
    TOUTES_LES_INSTANCES,
    Instance,
    construire,
    nb_placees,
    noms,
    partie,
)


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_c04_le_reste_en_pioche_vaut_nb_cartes_modulo_3n(instance: Instance) -> None:
    _, moteur = construire(instance)
    attendu = instance.reste_en_pioche

    for seed in range(NB_PARTIES_COURT):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()

        assert len(vue.pioche) == attendu, (
            f"{instance.nom}, seed {seed} : {len(vue.pioche)} cartes en pioche au lieu de "
            f"{instance.nb_cartes} mod (3 x {instance.joueurs}) = {attendu}"
        )
        assert all(len(main) == 0 for main in vue.mains), (
            f"{instance.nom}, seed {seed} : une main n'est pas vide a la fin de la partie"
        )
        assert nb_placees(vue) + len(vue.pioche) == instance.nb_cartes

"""C9 -- 01_regles.md paragraphes 4.1 et 5.

« Une carte tuee ne compte ni dans l'influence, ni dans les points. »

Le controle est un recalcul independant : le test refait le decompte du paragraphe 5
depuis la vue de dieu, en n'utilisant que les cartes vivantes, et exige l'egalite avec
`scores()`. La variante fausse -- les morts comptent -- doit donner un resultat different
au moins une fois, faute de quoi le test ne discriminerait rien.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    construire,
    noms,
    partie,
    scores_attendus,
    scores_moteur,
    scores_si_morts_comptes,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c09_les_cartes_tuees_ne_comptent_nulle_part(instance: Instance) -> None:
    _, moteur = construire(instance)
    parties_avec_morts = 0
    parties_discriminantes = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()

        attendus = scores_attendus(vue, instance)
        assert scores_moteur(etat, instance) == attendus, (
            f"{instance.nom}, seed {seed} : scores {scores_moteur(etat, instance)} au lieu "
            f"de {attendus} (recalcul sur les seules cartes vivantes)"
        )

        if vue.defausse:
            parties_avec_morts += 1
            if scores_si_morts_comptes(vue, instance) != attendus:
                parties_discriminantes += 1

    assert parties_avec_morts > 0, (
        f"{instance.nom} : aucune carte tuee sur {NB_PARTIES_BALAYAGE} parties"
    )
    assert parties_discriminantes > 0, (
        f"{instance.nom} : compter les morts ne change jamais le score sur "
        f"{parties_avec_morts} parties avec mort -- le test ne discrimine pas"
    )

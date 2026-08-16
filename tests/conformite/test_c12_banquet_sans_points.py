"""C12 -- 01_regles.md paragraphe 5, point 5.

« Les cartes au banquet ne rapportent aucun point : elles ne servent qu'a determiner le
statut des familles. »

Variante fausse : payer au poseur la valeur de sa carte de banquet. Elle doit donner un
resultat different au moins une fois.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    au_banquet,
    construire,
    noms,
    partie,
    scores_attendus,
    scores_avec_banquet_paye,
    scores_moteur,
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c12_le_banquet_ne_rapporte_aucun_point(instance: Instance) -> None:
    _, moteur = construire(instance)
    parties_discriminantes = 0
    cartes_au_banquet = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        vue = etat.vue_privilegiee()
        cartes_au_banquet += len(au_banquet(vue.posees))

        attendus = scores_attendus(vue, instance)
        assert scores_moteur(etat, instance) == attendus, (
            f"{instance.nom}, seed {seed} : scores {scores_moteur(etat, instance)} au lieu "
            f"de {attendus} (banquet exclu du decompte des points)"
        )
        if scores_avec_banquet_paye(vue, instance) != attendus:
            parties_discriminantes += 1

    assert cartes_au_banquet > 0, f"{instance.nom} : aucune carte posee au banquet"
    assert parties_discriminantes > 0, (
        f"{instance.nom} : payer le banquet ne change jamais le score sur "
        f"{NB_PARTIES_BALAYAGE} parties -- le test ne discrimine pas"
    )

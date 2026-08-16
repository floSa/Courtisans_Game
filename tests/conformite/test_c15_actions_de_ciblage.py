"""C15 -- 01_regles.md paragraphes 3.2 et 4.1.

« En phase de ciblage, le nombre d'actions legales vaut nb_cibles + 1. »

Le « + 1 » est le refus de tuer. Les actions doivent etre exactement 0..nb_cibles, sans
trou : c'est ce qui rend le decodage indice -> cible non ambigu.
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
)


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c15_le_ciblage_offre_nb_cibles_plus_une_actions(instance: Instance) -> None:
    _, moteur = construire(instance)
    noeuds = 0
    max_cibles = 0

    for seed, etat in parcourir_decisions(moteur, NB_PARTIES_BALAYAGE):
        if etat.phase().name != "CIBLAGE":
            continue
        noeuds += 1

        cibles = etat.cibles_courantes()
        actions = sorted(etat.legal_actions())
        max_cibles = max(max_cibles, len(cibles))

        assert actions == list(range(len(cibles) + 1)), (
            f"{instance.nom}, seed {seed} : actions {actions} au lieu de "
            f"{list(range(len(cibles) + 1))} pour {len(cibles)} cible(s)"
        )

    assert noeuds > 0, f"{instance.nom} : aucun noeud de ciblage rencontre"
    assert max_cibles > 0, (
        f"{instance.nom} : aucun noeud de ciblage n'a jamais eu la moindre cible"
    )

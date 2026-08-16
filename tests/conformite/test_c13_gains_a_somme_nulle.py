"""C13 -- 01_regles.md paragraphes 5.1 et 5.2, arbitrages R5 et R6.

« La somme des gains est nulle, y compris avec des ex aequo. »

Deux controles :
  - la formule seule, sur des scores fabriques, y compris tous les cas d'ex aequo ;
  - les parties reelles : `returns()` doit valoir la formule appliquee a `scores()`, et
    des ex aequo doivent survenir au moins une fois -- sinon le cas n'est pas couvert.

Les valeurs attendues sont ecrites a la main depuis le paragraphe 5.2, jamais calculees
par le moteur.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    INSTANCES_RAPIDES,
    NB_PARTIES_BALAYAGE,
    Instance,
    construire,
    gains_attendus,
    module,
    noms,
    partie,
    scores_moteur,
)

#: (scores, gains attendus) -- paragraphe 5.2 : vainqueur unique +1 ; k ex aequo
#: +(n - k) / (k (n - 1)) ; perdant -1 / (n - 1).
CAS_DE_GAIN: list[tuple[tuple[int, ...], tuple[float, ...]]] = [
    ((7, 3), (1.0, -1.0)),
    ((4, 4), (0.0, 0.0)),
    ((5, 3, 3), (1.0, -0.5, -0.5)),
    ((5, 5, 3), (0.25, 0.25, -0.5)),
    ((4, 4, 4), (0.0, 0.0, 0.0)),
    ((9, 1, 1, 1), (1.0, -1 / 3, -1 / 3, -1 / 3)),
    ((9, 9, 1, 1), (1 / 3, 1 / 3, -1 / 3, -1 / 3)),
    ((9, 9, 9, 1), (1 / 9, 1 / 9, 1 / 9, -1 / 3)),
    ((2, 2, 2, 2), (0.0, 0.0, 0.0, 0.0)),
    ((-4, -9, -9), (1.0, -0.5, -0.5)),
]
IDS_GAIN = [str(scores) for scores, _ in CAS_DE_GAIN]


@pytest.mark.parametrize(("scores", "attendus"), CAS_DE_GAIN, ids=IDS_GAIN)
def test_c13_la_formule_de_gain_est_a_somme_nulle(
    scores: tuple[int, ...], attendus: tuple[float, ...]
) -> None:
    gains = module("rules").gains_depuis_scores(scores)

    assert gains == pytest.approx(list(attendus)), (
        f"scores {scores} : gains {gains} au lieu de {list(attendus)}"
    )
    assert sum(gains) == pytest.approx(0.0), f"scores {scores} : somme {sum(gains)} non nulle"


@pytest.mark.parametrize("instance", INSTANCES_RAPIDES, ids=noms(INSTANCES_RAPIDES))
def test_c13_les_gains_des_parties_reelles_sont_a_somme_nulle(instance: Instance) -> None:
    _, moteur = construire(instance)
    parties_avec_ex_aequo = 0

    for seed in range(NB_PARTIES_BALAYAGE):
        etat = partie(moteur, seed)
        scores = scores_moteur(etat, instance)
        gains = list(etat.returns())

        assert len(gains) == instance.joueurs
        assert sum(gains) == pytest.approx(0.0), (
            f"{instance.nom}, seed {seed} : somme des gains {sum(gains)} pour scores {scores}"
        )
        assert gains == pytest.approx(gains_attendus(scores)), (
            f"{instance.nom}, seed {seed} : gains {gains} au lieu de "
            f"{gains_attendus(scores)} pour scores {scores}"
        )
        if scores.count(max(scores)) > 1:
            parties_avec_ex_aequo += 1

    assert parties_avec_ex_aequo > 0, (
        f"{instance.nom} : aucun ex aequo sur {NB_PARTIES_BALAYAGE} parties -- le cas des "
        f"ex aequo n'est pas couvert par ce balayage"
    )

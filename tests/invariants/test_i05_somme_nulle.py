"""I5 -- 03_specification_moteur.md paragraphe 5.

« sum(returns()) == 0, quel que soit le nombre de joueurs. »

C13 couvre la formule et les ex aequo sur les instances rapides. I5 etend le controle aux
sept configurations, dont les trois completes.

La specification ne dit pas si `returns()` est defini avant l'etat terminal. Le second test
n'impose donc rien la-dessus : il verifie seulement que la somme reste nulle partout ou
l'appel aboutit. Imposer que l'appel leve serait une regle inventee, et l'adaptateur
OpenSpiel de l'etape 7 ne pourrait pas la respecter.
"""

from __future__ import annotations

import pytest

from tests.outils import (
    TOUTES_LES_INSTANCES,
    Instance,
    construire,
    gains_attendus,
    noms,
    parcourir_decisions,
    partie,
    scores_moteur,
)

NB_PARTIES = 30


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i05_la_somme_des_gains_est_nulle(instance: Instance) -> None:
    _, moteur = construire(instance)

    for seed in range(NB_PARTIES):
        etat = partie(moteur, seed)
        gains = list(etat.returns())

        assert len(gains) == instance.joueurs
        assert all(gain == gain for gain in gains), f"{instance.nom}, seed {seed} : NaN"
        assert sum(gains) == pytest.approx(0.0, abs=1e-9), (
            f"{instance.nom}, seed {seed} : somme {sum(gains)} pour les gains {gains}"
        )
        assert gains == pytest.approx(gains_attendus(scores_moteur(etat, instance)))


@pytest.mark.parametrize("instance", TOUTES_LES_INSTANCES, ids=noms(TOUTES_LES_INSTANCES))
def test_i05_la_somme_reste_nulle_a_tout_noeud_ou_elle_est_definie(
    instance: Instance,
) -> None:
    _, moteur = construire(instance)

    for seed, etat in parcourir_decisions(moteur, 5):
        try:
            gains = list(etat.returns())
        except Exception:  # noqa: BLE001 - l'appel a le droit de ne pas etre defini ici
            continue
        assert len(gains) == instance.joueurs
        assert sum(gains) == pytest.approx(0.0, abs=1e-9), (
            f"{instance.nom}, seed {seed}, phase {etat.phase().name} : somme {sum(gains)}"
        )

"""Les deux implementations de la loi binomiale, tenues d'etre d'accord.

`queue_superieure` somme des `exp(log_binomiale)` ; `masse_binomiale` recurre sur le rapport
de deux termes consecutifs depuis le mode. Deux routines numeriques pour la meme loi derivent
en silence si rien ne les compare : c'est le motif que l'audit de la phase 1 a impose sur
l'intervalle de Clopper-Pearson, quatre calculs independants qui doivent tomber sur le meme
nombre.

L'extraction depuis `mesure/rapport.py` ne devait rien changer aux chiffres de la phase 1.
`test_l_extraction_n_a_pas_bouge_l_intervalle` le verifie sur les bornes que le rapport de la
phase 1 publie.
"""

from __future__ import annotations

import pytest

from mesure.binomiale import (
    intervalle_clopper_pearson,
    log_binomiale,
    masse_binomiale,
    queue_superieure,
)


@pytest.mark.parametrize("nb", [1, 2, 5, 17, 60, 200])
@pytest.mark.parametrize("proportion", [0.01, 1 / 3, 0.5, 0.62, 0.99])
def test_les_deux_implementations_s_accordent_a_1e_12(nb: int, proportion: float):
    """Sur tout `k`, la queue de la masse recurrente egale la queue en lgamma."""
    masse = masse_binomiale(nb, proportion)
    for k in range(nb + 1):
        recurrente = sum(masse[k:])
        assert recurrente == pytest.approx(
            queue_superieure(k, nb, proportion), abs=1e-12
        ), f"desaccord en n={nb} p={proportion} k={k}"


@pytest.mark.parametrize("nb", [1, 3, 40, 500])
@pytest.mark.parametrize("proportion", [0.1, 1 / 3, 0.5])
def test_la_masse_somme_a_un(nb: int, proportion: float):
    assert sum(masse_binomiale(nb, proportion)) == pytest.approx(1.0, abs=1e-12)


def test_la_masse_est_exacte_sur_un_cas_calcule_a_la_main():
    """n = 3, p = 1/2 : la loi vaut 1/8, 3/8, 3/8, 1/8. Aucune fonction du module consultee."""
    assert masse_binomiale(3, 0.5) == pytest.approx([0.125, 0.375, 0.375, 0.125], abs=1e-15)


def test_la_masse_tient_a_dix_mille_parties_la_ou_partir_de_zero_echoue():
    """La recurrence part du mode, et c'est ce qui la rend utilisable a n = 10 000.

    Partir de `k = 0` passerait par `(1 - p)^n`, qui vaut **exactement zero** en flottant a
    cette taille : toute la loi se retrouverait normalisee a partir de rien. Le cas asserte
    les deux faits, le piege et la parade.
    """
    nb, proportion = 10_000, 1 / 3
    assert (1 - proportion) ** nb == 0.0, "le piege a disparu : revoir le commentaire"
    masse = masse_binomiale(nb, proportion)
    assert sum(masse) == pytest.approx(1.0, abs=1e-12)
    mode = int((nb + 1) * proportion)
    assert masse[mode] > 0.008
    assert masse[mode] == max(masse)


def test_la_masse_refuse_les_cas_degeneres():
    for proportion in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="0 < p < 1"):
            masse_binomiale(10, proportion)
    with pytest.raises(ValueError, match="n >= 0"):
        masse_binomiale(-1, 0.5)


def test_la_queue_traite_les_bords_de_proportion():
    """`p = 0` et `p = 1` sont des lois de Dirac : la queue les rend sans recurrence."""
    assert queue_superieure(0, 10, 0.0) == 1.0
    assert queue_superieure(1, 10, 0.0) == 0.0
    assert queue_superieure(10, 10, 1.0) == 1.0


def test_le_log_binomiale_est_le_log_du_terme():
    """n = 4, k = 2, p = 1/2 : C(4,2)/16 = 6/16 = 0,375."""
    from math import exp

    assert exp(log_binomiale(4, 2, 0.5)) == pytest.approx(0.375, abs=1e-15)


def test_l_extraction_n_a_pas_bouge_l_intervalle():
    """Les bornes que le rapport de la phase 1 publie, recalculees apres deplacement.

    Le seuil de 1/3 de la phase 1 est franchi a 295/1000 en borne haute et a 373/1000 en
    borne basse -- les quatre comparaisons du go/no-go. Si l'extraction avait deplace une
    borne, ne serait-ce que d'un ulp du cote defavorable, ces quatre assertions changeraient.
    """
    seuil = 1 / 3
    assert intervalle_clopper_pearson(294, 1000)[1] < seuil
    assert intervalle_clopper_pearson(295, 1000)[1] >= seuil
    assert intervalle_clopper_pearson(373, 1000)[0] > seuil
    assert intervalle_clopper_pearson(372, 1000)[0] <= seuil


def test_l_intervalle_de_la_phase_1_est_inchange():
    """960/1000 -> [94,12 % ; 97,42 %], le chiffre du go/no-go de la phase 1."""
    basse, haute = intervalle_clopper_pearson(960, 1000)
    assert 100 * basse == pytest.approx(94.12, abs=5e-3)
    assert 100 * haute == pytest.approx(97.42, abs=5e-3)


def test_l_intervalle_refuse_l_impossible():
    with pytest.raises(ValueError, match="au moins une"):
        intervalle_clopper_pearson(0, 0)
    for k, n in ((-1, 10), (11, 10)):
        with pytest.raises(ValueError, match="impossible"):
            intervalle_clopper_pearson(k, n)

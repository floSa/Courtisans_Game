"""Tests hostiles de l'auditeur -- axes 4 et 7 : les gardes mordent-elles vraiment ?

Le precedent qui commande cette lecture : en phase 2, un controle nomme « une fonction
publique doit se defendre » affirmait dans son corps que l'appel REUSSISSAIT. Ici je ne lis
pas les intitules : je reinjecte la faute et j'exige le rouge.
"""

from __future__ import annotations

import pytest

from mesure import comportements as comp
from mesure import phase3_audit as audit
from mesure import phase3_mesure


def compte(nom, succes, total, grain="parties", vue="publique"):
    return comp.Compte(nom, succes, total, grain, vue)


def comparaison(nom, a, b, ecart=0.0, detectable=1.0, separable=False, exclu=None):
    return phase3_mesure.Comparaison(
        nom=nom, agent=a, base=b, ecart=ecart, detectable=detectable,
        separable=separable, exclu=exclu,
    )


# ---------------------------------------------------------------------------------------
# 1. Les gardes de grain MORDENT -- confirme
# ---------------------------------------------------------------------------------------


def test_ecart_de_taux_leve_quand_les_grains_different() -> None:
    with pytest.raises(comp.GrainsIncomparables):
        comp.ecart_de_taux(
            compte("B1", 10, 100, "parties (au moins un des 3 sieges mesures)"),
            compte("B1", 10, 100, "parties (le siege mesure)"),
        )


def test_ecart_de_taux_ne_leve_pas_au_meme_grain() -> None:
    assert comp.ecart_de_taux(compte("B1", 10, 100), compte("B1", 20, 100)) == pytest.approx(-0.1)


def test_cumuler_leve_quand_les_grains_different() -> None:
    with pytest.raises(comp.GrainsIncomparables):
        comp.cumuler(compte("B2", 1, 2, "poses au banquet"), compte("B2", 1, 2, "parties"))


# ---------------------------------------------------------------------------------------
# 2. `verifier_inclusion_b1` : elle mord sur l'inclusion... mais PAS sur le grain
# ---------------------------------------------------------------------------------------


def test_l_inclusion_b1_mord_aux_DEUX_grains() -> None:
    for suffixe in ("", "-par-partie"):
        comptes = {
            f"B1-collectif{suffixe}": compte(f"B1-collectif{suffixe}", 5, 100),
            f"B1-motif{suffixe}": compte(f"B1-motif{suffixe}", 9, 100),
        }
        with pytest.raises(ValueError, match="inclusion tombee"):
            comp.verifier_inclusion_b1(comptes)


def test_l_inclusion_b1_compare_des_NUMERATEURS_sans_regarder_les_grains() -> None:
    """Constat de l'auditeur : la garde compare `succes < succes` sans passer par la garde
    de grain. Deux comptes de grains differents s'y comparent donc en silence."""
    comptes = {
        "B1-collectif": compte("B1-collectif", 50, 100, "parties (au moins un des 3 sieges)"),
        "B1-motif": compte("B1-motif", 40, 24_000, "familles x parties"),
    }
    comp.verifier_inclusion_b1(comptes)  # ne leve pas, alors que les grains different


# ---------------------------------------------------------------------------------------
# 3. Deux des dix controles de l'auto-audit NE PEUVENT PAS echouer
# ---------------------------------------------------------------------------------------


def test_R4_les_zeros_est_toujours_concluant_quoi_qu_on_lui_donne() -> None:
    """`passe=True` est ecrit en dur. On lui donne le pire cas imaginable."""
    pire = [
        comparaison("tout-a-zero", compte("a", 0, 500), compte("b", 0, 500)),
        comparaison("tout-a-cent", compte("a", 500, 500), compte("b", 500, 500)),
    ]
    controle = audit.controle_zeros(pire)
    assert controle.passe, "il devrait etre concluant -- c'est justement le probleme"
    assert "2 valeur(s) extreme(s)" in controle.preuve


def test_R4_ne_regarde_QUE_l_agent_et_ignore_les_zeros_de_la_LIGNE_DE_BASE() -> None:
    """Les deux zeros absolus publies par le rapport sont du cote de la ligne de base."""
    lignes = [
        comparaison("B4-contre-nature", compte("a", 1368, 3814), compte("b", 0, 1967)),
        comparaison("B4-meurtre-couteux", compte("a", 298, 8131), compte("b", 0, 10382)),
    ]
    controle = audit.controle_zeros(lignes)
    assert controle.passe
    assert "0 valeur(s) extreme(s) chez l'agent -- aucune" in controle.preuve


def test_R5_l_unite_est_toujours_concluant_meme_sur_un_facteur_dix() -> None:
    class FausseMesure:
        comportements = {"X": compte("X", 5, 1000, "poses")}
        nb_parties = 100

    controle = audit.controle_unite_avant_valeur(
        FausseMesure(), {"X": compte("X", 5, 100, "poses")}, 100
    )
    assert controle.passe, "un facteur dix sur l'unite le laisse concluant"
    assert "10.000 vs 1.000" in controle.preuve


# ---------------------------------------------------------------------------------------
# 4. Le marqueur « hors budget » de `comparer` est du code mort
# ---------------------------------------------------------------------------------------


def test_aucune_ligne_ne_peut_etre_exclue_pour_HORS_BUDGET_quel_que_soit_le_budget() -> None:
    """La pre-inscription annonce huit lignes exclues « hors budget ». `comparer` passe
    `ecart=None` a `budget_d_un_compteur`, donc `parties` vaut `None`, donc `hors_budget`
    vaut `False` -- toujours, et meme a un budget d'UNE partie."""
    agent = {"X": compte("X", 5, 6000), "Y": compte("Y", 3000, 6000)}
    base = {"X": compte("X", 4, 6000), "Y": compte("Y", 3100, 6000)}
    for budget in (1, 10, 1000, 6000):
        lignes = phase3_mesure.comparer(agent, base, 6000, 6000, budget=budget)
        motifs = {c.exclu for c in lignes if c.exclu is not None}
        assert not any(m and "hors budget" in m for m in motifs), (budget, motifs)

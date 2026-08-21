"""L'auto-audit : chaque controle doit pouvoir ECHOUER.

Un controle qui ne peut pas echouer ne prouve rien. C'est la lecon que le greedy a laissee --
chacune de ses trois preuves est assortie d'un cas qui verifie que le piege mord -- et elle
vaut mot pour mot ici : `mesure/phase3_audit.py` est ecrit avant le resultat, donc personne ne
peut savoir qu'il mord tant qu'on ne le lui a pas fait faire.

Ces cas cassent donc chaque controle a la main, et exigent qu'il le dise.
"""

from __future__ import annotations

import dataclasses

from mesure import phase2, phase3, phase3_mesure
from mesure import phase3_audit as audit


def _mesure(donnes: int = 8) -> phase3_mesure.Mesure:
    """Une mesure minuscule : c'est la STRUCTURE des controles qu'on teste, pas leur valeur."""
    return phase3_mesure.mesurer(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=donnes,
        intitule="1 greedy contre 2 greedys (support de test)",
        depart=phase3_mesure.DEPART_CAMPAGNE_FINALE,
    )


def test_le_controle_de_somme_nulle_mord_sur_un_gain_falsifie():
    """Si I5 tombait, le niveau nul du seuil n'aurait plus de valeur connue."""
    mesure = _mesure()
    assert audit.controle_somme_nulle(mesure, mesure.campagne).passe

    trace = mesure.campagne.traces[0][0]
    faussee = dataclasses.replace(trace, gains=(1.0, 1.0, 1.0))
    campagne_faussee = dataclasses.replace(
        mesure.campagne,
        traces=((faussee,) + mesure.campagne.traces[0][1:],) + mesure.campagne.traces[1:],
    )
    controle = audit.controle_somme_nulle(mesure, campagne_faussee)
    assert not controle.passe
    assert "3.000e+00" in controle.preuve, controle.preuve


def test_le_controle_de_plan_equilibre_mord_sur_un_siege_double():
    """Le desequilibre deplacerait le niveau nul d'un ecart entre sieges -- +0,5735 mesure."""
    mesure = _mesure()
    assert audit.controle_plan_equilibre(mesure.campagne).passe

    desequilibre = dataclasses.replace(
        mesure.campagne,
        sieges_mesures=((0, 0, 1),) + mesure.campagne.sieges_mesures[1:],
    )
    controle = audit.controle_plan_equilibre(desequilibre)
    assert not controle.passe
    assert "1 desequilibrees" in controle.preuve, controle.preuve


def test_le_controle_de_denominateur_mord_sur_un_compte_falsifie():
    """`parties = donnes x sieges`, reconstruit et non recopie."""
    mesure = _mesure()
    assert audit.controle_denominateur(mesure).passe
    faussee = dataclasses.replace(mesure, nb_parties=mesure.nb_parties + 1)
    assert not audit.controle_denominateur(faussee).passe


def test_le_controle_des_populations_mord_sur_un_doublon_et_sur_un_nom_muet():
    """Deux compositions de meme nom se liraient comme une seule dans le rapport."""
    mesure = _mesure()
    autre = dataclasses.replace(mesure, intitule="1 agent contre 2 aleatoires")
    assert audit.controle_populations_nommees([mesure, autre]).passe

    doublon = audit.controle_populations_nommees([mesure, mesure])
    assert not doublon.passe
    assert "doublons" in doublon.preuve

    muet = dataclasses.replace(mesure, intitule="la campagne")
    resultat = audit.controle_populations_nommees([muet, autre])
    assert not resultat.passe
    assert "sans composition" in resultat.preuve


def test_le_controle_de_grain_mord_sur_deux_grains_differents():
    """La faute bloquante du tour 1 de la phase 2, avec inversion de signe sur B1."""
    from mesure import comportements as comp

    compte = comp.Compte(nom="B1-motif", succes=5, total=10, grain="couples", vue="decideur")
    autre_grain = comp.Compte(
        nom="B1-motif", succes=5, total=10, grain="parties", vue="decideur"
    )
    bonne = phase3_mesure.Comparaison(
        nom="B1-motif", agent=compte, base=compte, ecart=0.0,
        detectable=0.1, separable=False, exclu=None,
    )
    assert audit.controle_grains([bonne]).passe

    mauvaise = dataclasses.replace(bonne, base=autre_grain)
    controle = audit.controle_grains([mauvaise])
    assert not controle.passe
    assert "B1-motif" in controle.preuve


def test_le_controle_de_grain_ignore_les_lignes_EXCLUES():
    """Une ligne non comparee n'a pas a coincider : l'exiger ferait echouer a tort."""
    from mesure import comportements as comp

    compte = comp.Compte(nom="B4-tout-dos", succes=1, total=10, grain="a", vue="decideur")
    autre = comp.Compte(nom="B4-tout-dos", succes=1, total=10, grain="b", vue="decideur")
    exclue = phase3_mesure.Comparaison(
        nom="B4-tout-dos", agent=compte, base=autre, ecart=None,
        detectable=None, separable=False, exclu="texte de la definition",
    )
    assert audit.controle_grains([exclue]).passe


def test_le_controle_des_seeds_mord_sur_le_defaut_QU_IL_A_TROUVE():
    """Le defaut reel, rejoue : les compositions du pool tombaient dans l'entrainement.

    La premiere version de `phase3_mesure` partait a 30 000 et decalait le pool de +100 000 et
    +200 000. L'entrainement part a 100 000 et consomme une donne par partie : a 229 parties
    par seconde pendant 7 200 secondes, il monte a environ 1 749 000. Le cas verifie que le
    controle **voit** ce chevauchement.
    """
    bon = audit.controle_seeds_disjoints(
        donnes_verdict=2_000, donnes_pool=500, nb_checkpoints=8,
        parties_entrainement=1_800_000,
    )
    assert bon.passe, bon.preuve

    # Le defaut d'origine : on remet le depart et les decalages fautifs.
    original = (
        phase3_mesure.DEPART_CAMPAGNE_FINALE,
        phase3_mesure.DECALAGE_POOL_ALEATOIRE,
        phase3_mesure.DECALAGE_POOL_CHECKPOINTS,
    )
    try:
        phase3_mesure.DEPART_CAMPAGNE_FINALE = 30_000
        phase3_mesure.DECALAGE_POOL_ALEATOIRE = 100_000
        phase3_mesure.DECALAGE_POOL_CHECKPOINTS = 200_000
        casse = audit.controle_seeds_disjoints(
            donnes_verdict=2_000, donnes_pool=500, nb_checkpoints=8,
            parties_entrainement=1_800_000,
        )
    finally:
        (
            phase3_mesure.DEPART_CAMPAGNE_FINALE,
            phase3_mesure.DECALAGE_POOL_ALEATOIRE,
            phase3_mesure.DECALAGE_POOL_CHECKPOINTS,
        ) = original
    assert not casse.passe
    assert "entrainement" in casse.preuve and "CHEVAUCHEMENTS" in casse.preuve


def test_le_controle_de_bootstrap_distingue_un_tirage_par_donne_d_un_tirage_par_partie():
    """Un bootstrap qui tirerait des parties rendrait un effet de plan de 1,0 par construction.

    Le cas construit des donnes **fortement correlees** -- toutes les parties d'une donne ont
    le meme gain -- et exige que les deux routes vers l'effet de plan le voient. Sur des
    donnes ainsi construites, l'effet doit etre tres au-dessus de 1.
    """
    import random as alea_module

    from mesure import bootstrap as boot

    correlees = [[1.0, 1.0, 1.0] if i % 2 else [-1.0, -1.0, -1.0] for i in range(40)]
    effet = boot.bootstrap_par_donne(
        correlees, 2_000, alea_module.Random(0)
    ).effet
    rho = boot.correlation_intra_donne(correlees)
    assert rho is not None and rho > 0.9, rho
    assert effet > 2.0, (
        f"effet de plan {effet:.4f} sur des donnes parfaitement correlees : le bootstrap ne "
        f"tire pas des donnes, ou l'effet de plan n'est pas calcule sur la bonne unite."
    )


def test_le_controle_du_niveau_nul_tourne_sur_les_seeds_DU_VERDICT():
    """Un niveau nul verifie ailleurs ne dit rien ici : c'est un autre echantillon."""
    controle = audit.controle_niveau_nul(
        donnes=20, depart=phase3_mesure.DEPART_CAMPAGNE_FINALE
    )
    assert str(phase3_mesure.DEPART_CAMPAGNE_FINALE) in controle.preuve
    assert "IC 99 %" in controle.preuve


def test_l_audit_complet_rend_un_controle_par_question_et_aucune_preuve_vide():
    """Une preuve qui dirait « OK » ne serait pas une preuve. Chacune porte un chiffre."""
    mesure = _mesure()
    base = phase3_mesure.ligne_de_base_trois_greedys_un_siege(donnes=8)
    comparaisons = phase3_mesure.comparer(
        mesure.comportements, base, mesure.nb_parties, 24, budget=24
    )
    controles = audit.auditer(
        mesure=mesure,
        campagne=mesure.campagne,
        pool=[mesure],
        comparaisons=comparaisons,
        base=base,
        nb_parties_base=24,
        donnes_calibration=8,
        donnes_pool=500,
        nb_checkpoints=8,
        parties_entrainement=1_800_000,
    )
    assert len(controles) == 10
    assert {c.code for c in controles} == {"Q1", "Q2", "Q3", "R1", "R2", "R3", "R4", "R5"}
    for controle in controles:
        assert controle.preuve.strip(), controle.intitule
        assert controle.preuve.strip().upper() not in {"OK", "PASSE", "VRAI"}
        assert any(caractere.isdigit() for caractere in controle.preuve), (
            f"« {controle.intitule} » : sa preuve ne porte aucun chiffre"
        )


def test_le_budget_de_la_phase_2_n_est_pas_deplace_par_la_phase_3():
    """La phase 3 passe son budget en argument ; elle ne deplace pas l'etalon d'un livrable."""
    assert phase2.BUDGET_PHASE_3 == 1_000

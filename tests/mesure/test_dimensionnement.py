"""Les chiffres de plan de la phase 2, verifies un par un.

Chaque cas asserte un nombre **cite dans `mesure/phase2_hypothese_et_instrument.md`**. Un
plan ecrit avant la mesure n'a de valeur que si ses chiffres sont reconstructibles : sans
ces cas, rien n'empecherait un seuil de deriver silencieusement entre le document et le
compte rendu.

Les attendus sont calcules **hors du module teste** -- a la main, ou par une formule
independante ecrite dans le cas lui-meme -- jamais en appelant la fonction qu'ils
verifient.
"""

from __future__ import annotations

from statistics import NormalDist

import pytest

from mesure import dimensionnement as dim


def test_le_plan_de_la_campagne_a_fait_10_002_parties():
    """1 667 x 6. 10 000 n'est pas divisible par 6 (paragraphe 1.1)."""
    assert dim.parties(dim.DONNES_CAMPAGNE_A, dim.REPLICATS_CAMPAGNE_A) == 10_002
    assert 10_000 % dim.REPLICATS_CAMPAGNE_A != 0


def test_le_plan_de_la_campagne_b_fait_le_meme_compte():
    """3 334 x 3 = 10 002 : les deux campagnes sont comparables partie pour partie."""
    assert dim.parties(dim.DONNES_CAMPAGNE_B, dim.ASSIGNATIONS_CAMPAGNE_B) == 10_002


def test_le_niveau_neutre_de_la_part_fractionnee_est_exact():
    """1/3, et non une valeur estimee : les parts fractionnees somment a 1 par partie."""
    assert dim.part_neutre(3) == pytest.approx(1 / 3, abs=1e-15)
    assert dim.part_neutre(2) == 0.5
    assert dim.part_neutre(4) == 0.25


def test_le_niveau_neutre_refuse_un_seul_siege():
    with pytest.raises(ValueError, match="au moins 2 sieges"):
        dim.part_neutre(1)


def test_l_ecart_type_par_partie_vaut_47_14_points():
    """sqrt(1/3 x 2/3) = sqrt(2)/3. Calcule ici sans passer par le module."""
    attendu = 2**0.5 / 3
    assert dim.ecart_type_par_partie(1 / 3) == pytest.approx(attendu, abs=1e-15)
    assert 100 * attendu == pytest.approx(47.1405, abs=1e-4)


def test_l_erreur_type_vaut_0_4714_point_a_10_002_parties():
    """Le chiffre du paragraphe 2.3, et celui que l'enonce de la phase 2 cite a 0,471."""
    valeur = dim.erreur_type(1 / 3, 10_002)
    assert 100 * valeur == pytest.approx(0.4714, abs=1e-4)


def test_l_erreur_type_decroit_en_racine_de_n():
    """Quadrupler les parties divise l'erreur-type par deux, exactement."""
    petite = dim.erreur_type(1 / 3, 2_500)
    grande = dim.erreur_type(1 / 3, 10_000)
    assert petite / grande == pytest.approx(2.0, abs=1e-12)


def test_les_trois_seuils_de_m1():
    """38,00 % du protocole, 34,55 % non corrige, 34,72 % avec Bonferroni sur 3 sieges."""
    plan = dim.plan_m1()
    assert plan.nb_parties == 10_002
    assert 100 * plan.seuil_protocole == pytest.approx(38.0, abs=1e-9)
    assert 100 * plan.seuil_non_corrige == pytest.approx(34.55, abs=5e-3)
    assert 100 * plan.seuil_bonferroni == pytest.approx(34.72, abs=5e-3)
    assert plan.seuil_non_corrige < plan.seuil_bonferroni < plan.seuil_protocole


def test_le_seuil_du_protocole_est_a_9_9_erreurs_type():
    """C'est le defaut signale : il ne discrimine rien de ce qui est deja certain."""
    plan = dim.plan_m1()
    assert plan.ecarts_types_du_protocole == pytest.approx(9.90, abs=5e-3)


def test_un_siege_a_35_pourcent_est_certain_et_passe_le_seuil_du_protocole():
    """3,54 erreurs-type -- statistiquement etabli -- et pourtant sous 38 %."""
    ecarts = dim.ecarts_types(0.35, 1 / 3, 10_002)
    assert ecarts == pytest.approx(3.536, abs=5e-3)
    assert ecarts > dim.quantile_bilateral(dim.RISQUE, 3)
    assert 0.35 < dim.plan_m1().seuil_protocole


def test_la_correction_de_bonferroni_elargit_le_quantile():
    """Trois sieges testes a 1 % chacun donneraient un risque global de ~3 %."""
    nominal = dim.quantile_bilateral(0.01)
    corrige = dim.quantile_bilateral(0.01, 3)
    assert nominal == pytest.approx(NormalDist().inv_cdf(1 - 0.005), abs=1e-12)
    assert corrige == pytest.approx(NormalDist().inv_cdf(1 - 0.01 / 3 / 2), abs=1e-12)
    assert corrige > nominal


def test_le_quantile_refuse_un_risque_hors_bornes():
    for risque in (0.0, 1.0, -0.5, 2.0):
        with pytest.raises(ValueError, match="risque"):
            dim.quantile_bilateral(risque)
    with pytest.raises(ValueError, match="au moins une comparaison"):
        dim.quantile_bilateral(0.01, 0)


def test_l_effet_du_seuil_du_protocole_est_etabli_des_1456_parties():
    """4,667 points, 80 % de puissance, Bonferroni sur 3 sieges : 1 455,55 arrondi au superieur.

    Lecture : 10 002 parties sont sept fois plus que ce seuil-la ne demande, et c'est ce
    surplus que le seuil de 38 % gaspille.
    """
    ecart = 0.38 - 1 / 3
    sigma = dim.ecart_type_par_partie(1 / 3)
    assert dim.parties_pour_puissance(ecart, sigma, dim.RISQUE, dim.PUISSANCE, 3) == 1456


def test_un_ecart_de_1_67_point_demande_plus_que_la_campagne():
    """11 412 parties pour un siege a 35 % : 10 002 ne suffisent pas tout a fait.

    11 411,50 arrondi au superieur : une taille d'echantillon se plafonne, sinon la
    puissance annoncee n'est pas atteinte.
    """
    ecart = 0.35 - 1 / 3
    sigma = dim.ecart_type_par_partie(1 / 3)
    assert dim.parties_pour_puissance(ecart, sigma, dim.RISQUE, dim.PUISSANCE, 3) == 11_412


def test_la_puissance_contre_un_siege_a_35_pourcent_vaut_72_6_pourcent():
    """A ecrire a cote du resultat : une absence de detection n'est pas une absence d'effet."""
    ecart = 0.35 - 1 / 3
    sigma = dim.ecart_type_par_partie(1 / 3)
    valeur = dim.puissance_atteinte(ecart, sigma, 10_002, dim.RISQUE, 3)
    assert 100 * valeur == pytest.approx(72.6, abs=0.1)


def test_puissance_et_taille_sont_coherentes():
    """A la taille rendue pour 80 %, la puissance atteinte doit valoir au moins 80 %.

    Controle croise des deux fonctions : elles inversent la meme formule, une divergence
    signalerait une faute dans l'une des deux.
    """
    sigma = dim.ecart_type_par_partie(1 / 3)
    for ecart in (0.005, 0.0167, 0.03, 0.04667):
        taille = dim.parties_pour_puissance(ecart, sigma, dim.RISQUE, dim.PUISSANCE, 3)
        atteinte = dim.puissance_atteinte(ecart, sigma, taille, dim.RISQUE, 3)
        assert atteinte >= dim.PUISSANCE
        precedente = dim.puissance_atteinte(ecart, sigma, taille - 1, dim.RISQUE, 3)
        assert precedente < dim.PUISSANCE


def test_la_taille_pour_puissance_refuse_un_ecart_nul_ou_negatif():
    sigma = dim.ecart_type_par_partie(1 / 3)
    for ecart in (0.0, -0.01):
        with pytest.raises(ValueError, match="strictement positif"):
            dim.parties_pour_puissance(ecart, sigma, dim.RISQUE, dim.PUISSANCE)
    with pytest.raises(ValueError, match="puissance"):
        dim.parties_pour_puissance(0.01, sigma, dim.RISQUE, 1.0)


def test_l_ecart_type_est_connu_a_0_707_pourcent_pres_a_10_002_parties():
    """1 / sqrt(2 n). C'est ce qui rend M2 decide bien avant la fin de la campagne."""
    assert 100 * dim.erreur_relative_ecart_type(10_002) == pytest.approx(0.707, abs=1e-3)


def test_200_parties_suffisent_pour_5_pourcent_relatif():
    """1 / (2 x 0,05^2) = 200. M2 est decide des 200 parties, a 5 % relatif pres."""
    assert dim.parties_pour_erreur_relative(0.05) == 200
    assert dim.erreur_relative_ecart_type(200) == pytest.approx(0.05, abs=1e-12)


def test_l_appariement_divise_les_parties_par_un_sur_un_moins_rho():
    """Le facteur annonce au paragraphe 1 du protocole -- « cinq a dix » -- est rho in [0,8 ; 0,9].

    Verifie ici comme une propriete du plan, pas comme une mesure : c'est M2 qui dira ce que
    rho vaut, et si l'affirmation du protocole tient.
    """
    sans = dim.parties_pour_contraste_apparie(0.1, 0.7, 0.0, dim.RISQUE, dim.PUISSANCE)
    for rho, facteur in ((0.8, 5), (0.9, 10)):
        avec = dim.parties_pour_contraste_apparie(0.1, 0.7, rho, dim.RISQUE, dim.PUISSANCE)
        assert avec == pytest.approx(sans / facteur, rel=0.02)


def test_le_contraste_apparie_refuse_une_correlation_hors_bornes():
    """A rho = 1 aucun nombre de parties ne conclut : la fonction doit le dire, pas diviser."""
    for rho in (1.0, 1.5, -0.1):
        with pytest.raises(ValueError, match="correlation d'appariement"):
            dim.parties_pour_contraste_apparie(0.1, 0.7, rho, dim.RISQUE, dim.PUISSANCE)


def test_les_bornes_de_proportion_sont_gardees():
    for proportion in (-0.1, 1.1):
        with pytest.raises(ValueError, match="proportion"):
            dim.ecart_type_par_partie(proportion)
    for nb in (0, -1):
        with pytest.raises(ValueError, match="au moins une partie"):
            dim.erreur_type(1 / 3, nb)
        with pytest.raises(ValueError, match="au moins une partie"):
            dim.erreur_relative_ecart_type(nb)


def test_le_rapport_de_plan_cite_les_trois_seuils_et_ne_joue_aucune_partie():
    """Le texte doit porter les trois seuils : le compte rendu les cite tels quels."""
    texte = dim.rapport_de_plan()
    for attendu in ("38.0000 %", "34.5475 %", "34.7169 %", "10002", "9.90"):
        assert attendu in texte, f"{attendu} absent du rapport de plan"
    assert "Aucune partie jouee" in texte

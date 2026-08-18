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
from mesure.binomiale import masse_binomiale


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


def test_les_trois_calculs_de_taille_a_38_pourcent():
    """1 456, 1 475, 1 531 : trois methodes, trois nombres, et c'est le point.

    L'ecart entre les deux normales -- 19 parties -- vient du seul choix de l'ecart-type au
    terme de puissance. Il a ete decouvert par un desaccord entre deux implementations, et ce
    cas est ce qui empeche qu'il se reproduise en silence.
    """
    p0, p1 = 1 / 3, 0.38
    sous_h0 = dim.parties_pour_puissance_proportion(
        p0, p1, dim.RISQUE, dim.PUISSANCE, 3, dim.Variance.SOUS_H0
    )
    sous_h1 = dim.parties_pour_puissance_proportion(
        p0, p1, dim.RISQUE, dim.PUISSANCE, 3, dim.Variance.SOUS_H1
    )
    exacte = dim.parties_pour_puissance_exacte(p0, p1, dim.RISQUE, dim.PUISSANCE, 3)
    assert sous_h0 == 1456
    assert sous_h1 == 1475
    assert exacte.franchissement == 1501
    assert exacte.dernier_creux == 1530
    assert exacte.stable == 1531


def test_les_trois_calculs_de_taille_a_35_pourcent():
    """11 412, 11 472, 11 629 -- et 10 002 parties ne suffisent a aucun des trois."""
    p0, p1 = 1 / 3, 0.35
    sous_h0 = dim.parties_pour_puissance_proportion(
        p0, p1, dim.RISQUE, dim.PUISSANCE, 3, dim.Variance.SOUS_H0
    )
    sous_h1 = dim.parties_pour_puissance_proportion(
        p0, p1, dim.RISQUE, dim.PUISSANCE, 3, dim.Variance.SOUS_H1
    )
    exacte = dim.parties_pour_puissance_exacte(p0, p1, dim.RISQUE, dim.PUISSANCE, 3)
    assert sous_h0 == 11_412
    assert sous_h1 == 11_472
    assert exacte.franchissement == 11_539
    assert exacte.dernier_creux == 11_628
    assert exacte.stable == 11_629
    assert 10_002 < min(sous_h0, sous_h1, exacte.stable)


def test_l_ancienne_formule_est_bien_celle_qui_sous_estime():
    """`parties_pour_puissance` avec sigma sous H0 rend exactement `Variance.SOUS_H0`.

    C'est l'identite qui documente la faute : le chiffre annonce en etape 1 venait de cette
    forme, et il n'etait pas faux -- il etait sous-specifie.
    """
    p0 = 1 / 3
    sigma = dim.ecart_type_par_partie(p0)
    for p1 in (0.35, 0.38, 0.40):
        ancienne = dim.parties_pour_puissance(p1 - p0, sigma, dim.RISQUE, dim.PUISSANCE, 3)
        nommee = dim.parties_pour_puissance_proportion(
            p0, p1, dim.RISQUE, dim.PUISSANCE, 3, dim.Variance.SOUS_H0
        )
        assert ancienne == nommee


def test_sous_h1_majore_sous_h0_quand_l_alternative_approche_un_demi():
    """`sqrt(p1 q1) > sqrt(p0 q0)` des que `p1` est plus proche de 0,5 que `p0`.

    Et l'inegalite s'inverse de l'autre cote : a `p1 = 0,20`, plus loin de 0,5 que 1/3,
    c'est `SOUS_H0` qui majore. Le cas asserte les deux sens, sinon il ne demontre rien de
    la formule -- seulement du cas particulier qui nous occupe.
    """
    p0 = 1 / 3
    args = (dim.RISQUE, dim.PUISSANCE, 3)
    for p1 in (0.35, 0.38, 0.45):
        assert dim.parties_pour_puissance_proportion(
            p0, p1, *args, dim.Variance.SOUS_H1
        ) > dim.parties_pour_puissance_proportion(p0, p1, *args, dim.Variance.SOUS_H0)
    assert dim.ecart_type_par_partie(0.20) < dim.ecart_type_par_partie(p0)


def test_l_exact_majore_les_deux_normales():
    """Le test exact est conservateur : la queue atteinte est sous le risque nominal.

    Une implementation qui rendrait un exact **inferieur** a une normale aurait une valeur
    critique trop petite, donc un risque reel superieur a celui annonce.
    """
    p0 = 1 / 3
    for p1 in (0.35, 0.38, 0.42):
        exacte = dim.parties_pour_puissance_exacte(p0, p1, dim.RISQUE, dim.PUISSANCE, 3)
        for variance in dim.Variance:
            normale = dim.parties_pour_puissance_proportion(
                p0, p1, dim.RISQUE, dim.PUISSANCE, 3, variance
            )
            assert exacte.stable > normale, f"exact sous la normale {variance} a p1={p1}"


def test_la_dent_de_scie_est_reelle_et_non_un_artefact_de_recherche():
    """A 1 530 la puissance passe SOUS 80 %, a 1 531 elle ne redescend plus.

    C'est ce qui interdit de publier le premier franchissement : a 1 501 la cible est
    atteinte, a 1 502 elle ne l'est plus. Un `n` publie doit tenir pour lui-meme **et** pour
    tout ce qui le suit.
    """
    p0, p1 = 1 / 3, 0.38
    args = (p0, p1, dim.RISQUE, 3)
    assert dim.puissance_exacte(1501, *args) >= dim.PUISSANCE
    assert dim.puissance_exacte(1502, *args) < dim.PUISSANCE
    assert dim.puissance_exacte(1530, *args) < dim.PUISSANCE
    for nb in range(1531, 1631):
        assert dim.puissance_exacte(nb, *args) >= dim.PUISSANCE, f"creux en n={nb}"


def test_la_puissance_exacte_a_10_002_parties_vaut_71_5_pourcent():
    """Contre un siege a 35 %. La normale annonce 72,6 %, elle est anti-conservatrice.

    C'est ce chiffre-la que le compte rendu ecrit a cote du resultat : une absence de
    detection n'est pas une absence d'effet.
    """
    p0, p1 = 1 / 3, 0.35
    exacte = dim.puissance_exacte(10_002, p0, p1, dim.RISQUE, 3)
    normale = dim.puissance_atteinte(
        p1 - p0, dim.ecart_type_par_partie(p0), 10_002, dim.RISQUE, 3
    )
    assert 100 * exacte == pytest.approx(71.5, abs=0.1)
    assert 100 * normale == pytest.approx(72.6, abs=0.1)
    assert exacte < normale


def test_un_siege_a_38_pourcent_est_certain_a_10_002_parties():
    """Puissance exacte de 100 % : l'effet que le seuil du protocole designe ne s'y rate pas.

    Le seuil est donc mal place non pas parce que l'echantillon est petit, mais parce qu'il
    ne signale que ce qui est deja hors de doute.
    """
    exacte = dim.puissance_exacte(10_002, 1 / 3, 0.38, dim.RISQUE, 3)
    assert exacte > 0.9999


def test_la_valeur_critique_tient_le_risque_sans_l_atteindre():
    """`P(K >= c)` sous H0 est sous le plafond, `P(K >= c-1)` le depasse. Aucun `c` ne l'egale."""
    p0 = 1 / 3
    plafond = dim.RISQUE / 3 / 2
    for nb in (500, 1531, 10_002):
        critique = dim.valeur_critique(nb, p0, dim.RISQUE, 3)
        masse = masse_binomiale(nb, p0)
        assert sum(masse[critique:]) <= plafond
        assert sum(masse[critique - 1 :]) > plafond


def test_la_valeur_critique_a_10_002_parties():
    """3 474 succes sur 10 002, soit 34,73 % -- le seuil Bonferroni de 34,72 %, au compte pres.

    L'accord entre le seuil normal et la valeur critique exacte est le controle croise qui
    lie les paragraphes 2.3 et 2.4 : ils decrivent le meme test.
    """
    critique = dim.valeur_critique(10_002, 1 / 3, dim.RISQUE, 3)
    assert critique == 3474
    assert 100 * critique / 10_002 == pytest.approx(34.73, abs=5e-3)
    assert 100 * dim.plan_m1().seuil_bonferroni == pytest.approx(34.72, abs=5e-3)


def test_le_balayage_exact_refuse_une_alternative_sous_l_attendu():
    with pytest.raises(ValueError, match="alternative superieure"):
        dim.parties_pour_puissance_exacte(1 / 3, 0.30, dim.RISQUE, dim.PUISSANCE, 3)
    with pytest.raises(ValueError, match="alternative superieure"):
        dim.parties_pour_puissance_exacte(1 / 3, 1 / 3, dim.RISQUE, dim.PUISSANCE, 3)


def test_la_taille_par_proportion_refuse_un_ecart_nul():
    with pytest.raises(ValueError, match="ecart nul"):
        dim.parties_pour_puissance_proportion(
            1 / 3, 1 / 3, dim.RISQUE, dim.PUISSANCE
        )
    with pytest.raises(ValueError, match="puissance"):
        dim.parties_pour_puissance_proportion(1 / 3, 0.38, dim.RISQUE, 0.0)


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


def test_le_rapport_de_plan_porte_chaque_nombre_avec_sa_formule():
    """Un `n` sans sa formule n'est pas reconstructible. Le rapport doit rendre les deux."""
    texte = dim.rapport_de_plan()
    for attendu in (
        "38.0000 %",
        "34.5475 %",
        "34.7169 %",
        "10002",
        "9.90",
        "**1456** parties",
        "**1475** parties",
        "**exact binomial, stable : 1531 parties**",
        "**11412** parties",
        "**11472** parties",
        "**exact binomial, stable : 11629 parties**",
        "z_risque = 2.935199",
        "z_puissance = 0.841621",
        "sqrt(p0 q0) = 0.471405",
        "sqrt(p1 q1) = 0.485386",
        "0.00166667 par queue",
        "rejet si K >= ",
        "dent de scie de 30 unites",
        "dent de scie de 90 unites",
        "sous H0 aux deux termes",
        "sous H1 au terme de puissance",
    ):
        assert attendu in texte, f"{attendu} absent du rapport de plan"
    assert "Aucune partie jouee" in texte

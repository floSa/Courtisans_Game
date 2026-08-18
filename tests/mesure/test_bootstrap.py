"""Le bootstrap par donne, sur des donnees dont on connait la reponse d'avance.

L'effet de plan est le chiffre qui remplace un raisonnement : j'avais affirme, a l'etape 0,
que la correlation intra-donne « sous-estime » l'erreur iid, sans l'avoir etabli. Ces cas
etablissent que **l'effet peut aller dans les deux sens**, sur des donnees construites, avant
qu'aucune partie ne soit jouee.

Trois regimes, tous verifies :

  - **donnes a un seul replicat** -> les parties sont independantes -> effet ~ 1 ;
  - **replicats identiques dans chaque donne** -> correlation intra-donne de 1 -> effet ~ m,
    le nombre de replicats. Le bootstrap **gonfle** ;
  - **replicats en miroir dans chaque donne** -> chaque donne a exactement la meme moyenne ->
    variance bootstrap nulle -> effet ~ 0. Le bootstrap **reduit**.

Le troisieme regime est celui qui interdit d'annoncer le sens de l'effet sans l'avoir mesure.
"""

from __future__ import annotations

import random

import pytest

from mesure.bootstrap import bootstrap_par_donne, correlation_intra_donne

REPETITIONS = 2_000


def _donnes_independantes(nb: int, alea: random.Random) -> list[list[float]]:
    """`nb` donnes d'un seul replicat : aucune structure a exploiter."""
    return [[alea.gauss(0.0, 1.0)] for _ in range(nb)]


def _replicats_identiques(nb: int, replicats: int, alea: random.Random) -> list[list[float]]:
    """Chaque donne rend `replicats` fois la meme valeur : correlation intra-donne de 1."""
    return [[alea.gauss(0.0, 1.0)] * replicats for _ in range(nb)]


def _replicats_en_miroir(nb: int, alea: random.Random) -> list[list[float]]:
    """Chaque donne rend `+x` et `-x` : sa moyenne est nulle, quelle que soit la donne."""
    valeurs = []
    for _ in range(nb):
        tirage = alea.gauss(0.0, 1.0)
        valeurs.append([tirage, -tirage])
    return valeurs


def test_des_parties_independantes_donnent_un_effet_de_plan_voisin_de_un():
    """Un replicat par donne : le bootstrap par donne EST le bootstrap par partie."""
    observations = _donnes_independantes(400, random.Random(1))
    effet = bootstrap_par_donne(observations, REPETITIONS, random.Random(2))
    assert effet.nb_donnes == 400
    assert effet.nb_parties == 400
    assert effet.effet == pytest.approx(1.0, abs=0.15)
    assert effet.n_effectif == pytest.approx(400, rel=0.15)


def test_des_replicats_identiques_gonflent_la_variance_du_facteur_des_replicats():
    """Correlation intra-donne de 1 : l'effet de plan vaut le nombre de replicats.

    Six replicats identiques ne portent qu'une information : la taille d'echantillon effective
    doit retomber au nombre de DONNES, pas au nombre de parties.
    """
    observations = _replicats_identiques(300, 6, random.Random(3))
    effet = bootstrap_par_donne(observations, REPETITIONS, random.Random(4))
    assert effet.nb_parties == 1_800
    assert effet.effet == pytest.approx(6.0, rel=0.2)
    assert effet.n_effectif == pytest.approx(300, rel=0.2)


def test_des_replicats_en_miroir_reduisent_la_variance():
    """L'effet de plan peut etre **inferieur a 1**, et c'est ce qui interdit d'annoncer son sens.

    Chaque donne a une moyenne exactement nulle, donc rechantillonner des donnes ne fait pas
    bouger la moyenne : la variance bootstrap est nulle a la precision machine, alors que la
    variance iid ne l'est pas du tout.
    """
    observations = _replicats_en_miroir(300, random.Random(5))
    effet = bootstrap_par_donne(observations, REPETITIONS, random.Random(6))
    assert effet.variance_iid > 0
    assert effet.variance_bootstrap == pytest.approx(0.0, abs=1e-24)
    assert effet.effet < 1e-12
    assert effet.n_effectif > effet.nb_parties


def test_l_intervalle_de_percentiles_encadre_la_moyenne_observee():
    """Sur des donnes independantes centrees, l'intervalle a 99 % doit contenir 0."""
    observations = _donnes_independantes(600, random.Random(7))
    effet = bootstrap_par_donne(observations, REPETITIONS, random.Random(8))
    basse, haute = effet.intervalle
    assert basse < effet.moyenne < haute
    assert basse < 0.0 < haute


def test_le_bootstrap_est_reproductible_au_bit_pres():
    """Meme graine, memes chiffres. Sans quoi aucun resultat de campagne n'est reproductible."""
    observations = _replicats_identiques(50, 6, random.Random(9))
    premier = bootstrap_par_donne(observations, 500, random.Random(10))
    second = bootstrap_par_donne(observations, 500, random.Random(10))
    assert premier == second


def test_le_bootstrap_refuse_le_vide_et_les_parametres_absurdes():
    observations = _donnes_independantes(10, random.Random(11))
    with pytest.raises(ValueError, match="aucune observation"):
        bootstrap_par_donne([], REPETITIONS, random.Random(12))
    with pytest.raises(ValueError, match="aucune observation"):
        bootstrap_par_donne([[], []], REPETITIONS, random.Random(12))
    with pytest.raises(ValueError, match="au moins 2 rechantillons"):
        bootstrap_par_donne(observations, 1, random.Random(12))
    with pytest.raises(ValueError, match="risque"):
        bootstrap_par_donne(observations, REPETITIONS, random.Random(12), risque=0.0)


# ---------------------------------------------------------------------------------
# La correlation intra-donne
# ---------------------------------------------------------------------------------


def test_la_correlation_vaut_un_sur_des_replicats_identiques():
    """Six copies de la meme valeur : toute la variance est inter-donnes."""
    observations = _replicats_identiques(200, 6, random.Random(13))
    assert correlation_intra_donne(observations) == pytest.approx(1.0, abs=1e-9)


def test_la_correlation_est_nulle_quand_les_replicats_ne_partagent_rien():
    """Six tirages independants par donne : aucune structure, `rho` voisin de 0."""
    alea = random.Random(14)
    observations = [[alea.gauss(0.0, 1.0) for _ in range(6)] for _ in range(400)]
    rho = correlation_intra_donne(observations)
    assert rho == pytest.approx(0.0, abs=0.05)


def test_la_correlation_est_negative_sur_des_replicats_en_miroir():
    """`rho` peut etre **negatif**, et le facteur `1 / (1 - rho)` devient donc < 1.

    C'est le troisieme regime, celui qui interdit de supposer le sens de l'effet : un plan
    apparie peut, sur certaines statistiques, demander PLUS de parties qu'un plan non apparie.
    """
    observations = _replicats_en_miroir(300, random.Random(15))
    rho = correlation_intra_donne(observations)
    assert rho is not None
    assert rho < -0.9


def test_le_facteur_de_gain_du_protocole_correspond_a_rho_entre_0_8_et_0_9():
    """« Diviser par cinq a dix » implique `rho` dans `[0,8 ; 0,9]`. Verifie ici comme algebre.

    Le cinquieme trou du protocole est ce chiffre-la : l'affirmation du paragraphe 1 n'est
    appuyee par aucune mesure du depot. Ce cas etablit seulement l'equivalence entre les deux
    formulations ; c'est M2 qui dira ce que `rho` vaut.
    """
    for rho, facteur in ((0.8, 5.0), (0.9, 10.0)):
        assert 1 / (1 - rho) == pytest.approx(facteur, abs=1e-12)


def test_la_correlation_rend_none_quand_elle_n_est_pas_definie():
    """Une seule donne, ou un seul replicat : `rho` n'existe pas. `None`, jamais 0."""
    assert correlation_intra_donne([[1.0, 2.0]]) is None
    assert correlation_intra_donne([[1.0], [2.0], [3.0]]) is None
    assert correlation_intra_donne([[1.0, 1.0], [1.0, 1.0]]) is None


def test_la_correlation_refuse_des_donnes_de_tailles_inegales():
    """La formule suppose des groupes equilibres. L'appliquer autrement rendrait un faux."""
    with pytest.raises(ValueError, match="meme taille"):
        correlation_intra_donne([[1.0, 2.0], [3.0]])


def test_correlation_et_effet_de_plan_racontent_la_meme_chose():
    """Controle croise : `effet ~ 1 + (m - 1) rho`, la formule de l'effet de grappe.

    Les deux quantites sont calculees par des chemins independants -- une decomposition de
    variance pour `rho`, un rechantillonnage pour l'effet. Qu'elles coincident est ce qui
    etablit qu'aucune des deux n'est fausse ; verifier chacune separement ne le montrerait pas.
    """
    alea = random.Random(16)
    replicats = 6
    observations = []
    for _ in range(500):
        commun = alea.gauss(0.0, 1.0)
        observations.append(
            [0.7 * commun + 0.3 * alea.gauss(0.0, 1.0) for _ in range(replicats)]
        )
    rho = correlation_intra_donne(observations)
    effet = bootstrap_par_donne(observations, REPETITIONS, random.Random(17))
    attendu = 1 + (replicats - 1) * rho
    assert effet.effet == pytest.approx(attendu, rel=0.15)

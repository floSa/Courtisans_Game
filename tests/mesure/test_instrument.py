"""L'instrument lui-meme : l'intervalle de confiance, et la reproductibilite des parties.

L'intervalle de Clopper-Pearson decide du go/no-go -- c'est lui qui dit si la proportion
mesuree est au-dessus du seuil, en dessous, ou indecise. Un intervalle faux rendrait une
conclusion fausse sur des comptes justes.
"""

from __future__ import annotations

import random
from dataclasses import replace

from courtisans.engine import Engine
from mesure.partie import Grain, Vue, observer, politique_uniforme
from mesure.rapport import CONFIG, DECALAGE_POLITIQUE, intervalle_clopper_pearson, jouer_campagne


def test_intervalle_sur_zero_succes() -> None:
    """`k = 0` : borne basse nulle, borne haute `1 - (alpha/2)^(1/n)`, calculable a la main.

    Avec `alpha = 0.01` et `n = 10` : `1 - 0.005^0.1 = 1 - 0.58866... = 0.41133...`
    """
    basse, haute = intervalle_clopper_pearson(0, 10)
    assert basse == 0.0
    assert abs(haute - (1 - 0.005**0.1)) < 1e-9


def test_intervalle_sur_que_des_succes() -> None:
    """`k = n` : borne haute a 1, borne basse `(alpha/2)^(1/n) = 0.58866...`"""
    basse, haute = intervalle_clopper_pearson(10, 10)
    assert haute == 1.0
    assert abs(basse - 0.005**0.1) < 1e-9


def test_l_intervalle_contient_toujours_la_proportion_observee() -> None:
    for k in (0, 1, 17, 333, 500, 999, 1000):
        basse, haute = intervalle_clopper_pearson(k, 1000)
        assert basse <= k / 1000 <= haute


def test_l_intervalle_retrecit_quand_l_effectif_grandit() -> None:
    largeurs = []
    for n in (100, 1000, 10000):
        basse, haute = intervalle_clopper_pearson(n // 3, n)
        largeurs.append(haute - basse)
    assert largeurs[0] > largeurs[1] > largeurs[2]


def test_la_bande_d_indecision_a_1000_parties_est_celle_annoncee() -> None:
    """`hypothese_et_instrument.md` paragraphe 4.2 annonce [0.295 ; 0.372] autour de 1/3.

    Cette bande a ete calculee avant la mesure par la loi binomiale exacte : la mesure
    tranche des que la proportion observee en sort. Ce test verifie que l'intervalle du
    rapport dit exactement la meme chose -- 294 succes sont decisifs, 295 non ; 373 sont
    decisifs, 372 non.
    """
    seuil = 1 / 3
    assert intervalle_clopper_pearson(294, 1000)[1] < seuil
    assert intervalle_clopper_pearson(295, 1000)[1] >= seuil
    assert intervalle_clopper_pearson(373, 1000)[0] > seuil
    assert intervalle_clopper_pearson(372, 1000)[0] <= seuil


def test_une_partie_est_reproductible_depuis_son_seed() -> None:
    """Meme seed, meme partie : c'est la condition pour qu'un chiffre soit rejouable.

    La duree mesuree est exclue de la comparaison : c'est du temps mural, il ne se reproduit
    pas et il n'entre dans aucun chiffre du go/no-go.
    """
    moteur = Engine(CONFIG)
    premieres = [
        replace(
            observer(
                moteur.reset(7), politique_uniforme(random.Random(DECALAGE_POLITIQUE + 7)), 7
            ),
            duree_s=0.0,
        )
        for _ in range(2)
    ]
    assert premieres[0] == premieres[1]


def test_deux_seeds_donnent_deux_parties() -> None:
    """Sinon le seed ne servirait a rien et les 1 000 parties n'en seraient qu'une."""
    parties = jouer_campagne(nb_parties=5, depart=0)
    scores = {partie.scores for partie in parties}
    assert len(scores) > 1


def test_toutes_les_parties_ont_la_forme_attendue() -> None:
    """Les invariants d'arithmetique de l'instance, sur un petit echantillon."""
    for partie in jouer_campagne(nb_parties=20, depart=0):
        assert partie.poses_par_joueur == (CONFIG.tours,) * CONFIG.joueurs
        assert partie.cartes_non_piochees == CONFIG.reste_en_pioche
        assert abs(sum(partie.gains)) < 1e-9
        for suite in partie.suites[Grain.TOUR, Vue.VRAIE]:
            assert len(suite) == CONFIG.joueurs * CONFIG.tours + 1

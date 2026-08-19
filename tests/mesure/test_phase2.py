"""Le plan des deux campagnes, et les deux statistiques de siege.

Ce qui est verifie ici n'est pas un resultat mais un **instrument** : que les campagnes jouent
bien ce que le paragraphe 9 de la pre-inscription annonce, que les plages de seeds de politique
sont disjointes, et que les deux statistiques de siege ont les niveaux neutres qu'on leur
prete.

Le dernier point est le plus important. Le protocole ecrit son seuil en parts de victoire ;
y repondre avec une statistique dont le niveau neutre n'est pas exactement `1/3` rendrait le
seuil ininterpretable. La part **fractionnee** somme a 1 a chaque partie, donc son attendu par
siege vaut `1/3` exactement ; la part **stricte** ne somme pas a 1, et son attendu est inconnu
avant mesure.
"""

from __future__ import annotations

import random

import pytest

from mesure import phase2
from mesure.instance import ENTRAINEMENT_3J

CONFIG = ENTRAINEMENT_3J


# ---------------------------------------------------------------------------------
# Les deux statistiques, et leurs niveaux neutres
# ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("scores", "fractionnee", "stricte"),
    [
        ((5, 2, 1), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((5, 5, 1), (0.5, 0.5, 0.0), (0.0, 0.0, 0.0)),
        ((4, 4, 4), (1 / 3, 1 / 3, 1 / 3), (0.0, 0.0, 0.0)),
        ((-1, -3, -3), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        ((0, 0, -2), (0.5, 0.5, 0.0), (0.0, 0.0, 0.0)),
    ],
)
def test_les_deux_parts_de_victoire_sur_des_scores_calcules_a_la_main(
    scores, fractionnee, stricte
):
    """Cinq configurations, ex aequo compris. Les egalites sont conservees (paragraphe 5.1)."""
    assert phase2.part_de_victoire_fractionnee(scores) == pytest.approx(fractionnee)
    assert phase2.part_de_victoire_stricte(scores) == pytest.approx(stricte)


def test_la_part_fractionnee_somme_a_un_a_chaque_partie():
    """C'est ce qui rend son niveau neutre EXACT, et non estime.

    Sur mille triplets de scores tires au hasard, ex aequo compris, la somme doit valoir 1.
    C'est la propriete qui autorise a comparer une part fractionnee a `1/3` ; sans elle, le
    seuil du protocole n'aurait pas de reference.
    """
    alea = random.Random(4242)
    for _ in range(1_000):
        scores = tuple(alea.randint(-8, 8) for _ in range(CONFIG.joueurs))
        assert sum(phase2.part_de_victoire_fractionnee(scores)) == pytest.approx(1.0)


def test_la_part_stricte_ne_somme_pas_a_un_et_ne_peut_donc_pas_servir_de_seuil():
    """Sur une partie a ex aequo elle vaut 0 partout : son attendu par siege n'est pas `1/3`.

    Le cas asserte les deux faits qui l'excluent comme seuil -- la somme tombe a 0 sur un
    ex aequo, et son attendu vaut `(1 - P(ex aequo)) / 3`, donc il depend d'une quantite
    inconnue avant mesure.
    """
    assert sum(phase2.part_de_victoire_stricte((4, 4, 4))) == 0.0
    assert sum(phase2.part_de_victoire_stricte((4, 4, 1))) == 0.0
    assert sum(phase2.part_de_victoire_stricte((4, 2, 1))) == 1.0


# ---------------------------------------------------------------------------------
# Le plan des campagnes
# ---------------------------------------------------------------------------------


def test_la_campagne_a_joue_six_replicats_par_donne():
    """Six parties par donne, sur la meme pioche, avec six aleas de politique distincts.

    La pioche identique se verifie sur les cartes jamais piochees et sur les mains initiales :
    c'est ce qui fait de la donne une unite de bootstrap.
    """
    groupes = phase2.campagne_a(4)
    assert len(groupes) == 4
    for indice, groupe in enumerate(groupes):
        assert groupe.seed == phase2.DEPART_A + indice
        assert len(groupe.traces) == 6
        assert [t.replicat for t in groupe.traces] == list(range(6))
        assert {t.seed for t in groupe.traces} == {groupe.seed}
        # tous les sieges sont mesures : la ligne de base du hasard porte sur les trois
        assert set(groupe.sieges_mesures) == {tuple(range(CONFIG.joueurs))}


def test_les_replicats_d_une_donne_ne_donnent_pas_tous_la_meme_partie():
    """Sinon l'appariement serait vide au sens fort et le bootstrap n'aurait rien a mesurer.

    Meme pioche, politiques tirees differemment : les scores doivent differer sur au moins une
    donne. Si les six replicats coincidaient, la campagne A ne serait que 1 667 parties.
    """
    groupes = phase2.campagne_a(6)
    assert any(len({t.scores for t in groupe.traces}) > 1 for groupe in groupes)


def test_la_campagne_b_fait_tourner_le_greedy_sur_les_trois_sieges():
    """Trois parties par donne, le greedy en siege 0 puis 1 puis 2.

    C'est ce qui **neutralise l'avantage de siege par construction** : la moyenne du greedy sur
    les trois parties d'une donne ne contient plus d'effet de siege, quel que soit cet effet.
    """
    groupes = phase2.campagne_b(3)
    for groupe in groupes:
        assert len(groupe.traces) == CONFIG.joueurs
        assert list(groupe.sieges_mesures) == [(0,), (1,), (2,)]


def test_la_campagne_b_a_deux_greedys_mesure_les_deux_sieges_non_aleatoires():
    """A deux greedys, la variable permutee est le siege de l'ALEATOIRE, et on mesure les autres."""
    groupes = phase2.campagne_b(2, nb_greedys=2)
    for groupe in groupes:
        assert list(groupe.sieges_mesures) == [(1, 2), (0, 2), (0, 1)]


def test_la_campagne_b_refuse_une_composition_impossible():
    """A 0 greedy il n'y a rien a mesurer ; au-dela de 3 il n'y a pas assez de sieges.

    **La garde a ete scindee.** Elle refusait aussi `nb_greedys=3` en disant « la mesure n'a plus
    d'objet » : c'est vrai de **M3**, ou trois greedys identiques rendent un tiers de part de
    victoire par symetrie, et faux de **M4**, ou les compteurs de comportement gardent tout leur
    sens. La garde confondait une **mesure** avec une **phase**. Elle ne juge plus que la
    composition ; c'est `mesurer_m3` qui refuse ce qui n'a pas d'objet pour lui.
    """
    for nb in (0, 4, -1):
        with pytest.raises(ValueError, match="1 a 3 greedys"):
            phase2.campagne_b(1, nb_greedys=nb)


def test_la_campagne_b_accepte_trois_greedys_pour_m4():
    """L'autre branche de la garde scindee. Une garde qui ne laisse rien passer ne prouve rien.

    A trois greedys il n'y a plus de siege a permuter : les trois parties d'une donne ne diffèrent
    que par l'alea de **departage** du greedy, ce qui en fait trois replicats sur la meme pioche --
    exactement la structure de la campagne A, et c'est ce qui rend leurs `-par-partie`
    comparables.

    Les **trois** sieges sont mesures, puisque les trois sont des greedys.
    """
    groupes = phase2.campagne_b(2, nb_greedys=3)
    for groupe in groupes:
        assert len(groupe.traces) == CONFIG.joueurs
        assert list(groupe.sieges_mesures) == [(0, 1, 2)] * CONFIG.joueurs


def test_m3_refuse_une_population_a_trois_greedys():
    """M3 n'a pas d'objet a trois greedys, et c'est LUI qui doit le dire.

    Trois politiques identiques rendent, **par symetrie**, un tiers de part de victoire et un gain
    moyen nul : le chiffre existerait, il ne mesurerait rien. Le message doit dire pourquoi, pas
    seulement refuser.
    """
    groupes = phase2.campagne_b(2, nb_greedys=3)
    with pytest.raises(ValueError, match="symetrie"):
        phase2.mesurer_m3(groupes, "trois greedys", random.Random(0), nb_greedys=3)


def test_m3_accepte_les_deux_compositions_qui_ont_un_objet():
    """L'autre branche : a 1 et a 2 greedys, M3 mesure et rend un resultat.

    A 2 greedys la part de victoire mesuree reste sous celle de la composition de reference --
    deux greedys se prennent des points l'un a l'autre --, mais elle a un **sens**, et c'est la
    seule chose que la garde doit laisser passer.
    """
    for nb in (1, 2):
        groupes = phase2.campagne_b(2, nb_greedys=nb)
        resultat = phase2.mesurer_m3(groupes, f"{nb} greedy(s)", random.Random(0), nb_greedys=nb)
        assert resultat.nb_parties > 0


def test_les_plages_de_seeds_de_politique_sont_disjointes():
    """Le paragraphe 9 l'affirme ; ce cas le verifie au lieu de le supposer.

    Aucune partie ne doit partager son alea de politique avec une autre, sinon deux mesures
    seraient correlees sans qu'aucun chiffre ne le dise. Les quatre plages sont reconstruites
    ici a partir des seuls decalages nommes, pour le plan complet.
    """
    from mesure import dimensionnement as dim

    plages: dict[str, set[int]] = {}
    donnes_a = dim.DONNES_CAMPAGNE_A
    plages["A"] = {
        phase2.DECALAGE_POLITIQUE_A + 6 * donne + replicat
        for donne in range(phase2.DEPART_A, phase2.DEPART_A + donnes_a)
        for replicat in range(6)
    }
    plages["A controle"] = {
        phase2.DECALAGE_POLITIQUE_A + 6 * donne + replicat
        for donne in range(
            phase2.DEPART_A_CONTROLE, phase2.DEPART_A_CONTROLE + donnes_a
        )
        for replicat in range(6)
    }
    donnes_b = dim.DONNES_CAMPAGNE_B
    plages["B"] = {
        phase2.DECALAGE_POLITIQUE_B + CONFIG.joueurs * donne + siege
        for donne in range(phase2.DEPART_B, phase2.DEPART_B + donnes_b)
        for siege in range(CONFIG.joueurs)
    }
    plages["B 2 greedys"] = {
        phase2.DECALAGE_POLITIQUE_2_GREEDYS + CONFIG.joueurs * donne + siege
        for donne in range(phase2.DEPART_B, phase2.DEPART_B + donnes_b)
        for siege in range(CONFIG.joueurs)
    }
    noms = sorted(plages)
    for premier in range(len(noms)):
        for second in range(premier + 1, len(noms)):
            commun = plages[noms[premier]] & plages[noms[second]]
            assert not commun, (
                f"les plages « {noms[premier]} » et « {noms[second]} » partagent "
                f"{len(commun)} seed(s) de politique"
            )
    assert len(plages["A"]) == 6 * donnes_a
    assert len(plages["B"]) == CONFIG.joueurs * donnes_b


def test_les_campagnes_sont_reproductibles_au_bit_pres():
    """Deux appels identiques donnent les memes scores. Sans quoi aucun chiffre n'est rejouable."""
    premier = phase2.campagne_b(3)
    second = phase2.campagne_b(3)
    for un, deux in zip(premier, second, strict=True):
        assert [t.scores for t in un.traces] == [t.scores for t in deux.traces]


# ---------------------------------------------------------------------------------
# Les mesures, sur une campagne minuscule
# ---------------------------------------------------------------------------------


def test_m1_conserve_les_deux_controles_de_somme():
    """Les gains somment a 0, les parts fractionnees a 1. Deux controles, pas deux deductions."""
    groupes = phase2.campagne_a(10)
    resultats = phase2.mesurer_m1(groupes, random.Random(1))
    assert len(resultats) == CONFIG.joueurs
    assert sum(r.gain.moyenne for r in resultats) == pytest.approx(0.0, abs=1e-12)
    assert sum(r.part_fractionnee.moyenne for r in resultats) == pytest.approx(1.0, abs=1e-12)
    for resultat in resultats:
        assert resultat.gain.nb_donnes == 10
        assert resultat.gain.nb_parties == 60


def test_m2_rend_une_correlation_definie_et_les_criteres_de_la_phase_1():
    """`rho` doit exister -- six replicats par donne -- et les criteres doivent etre calculables."""
    resultat = phase2.mesurer_m2(phase2.campagne_a(10))
    assert resultat.nb_parties == 60
    assert all(r is not None for r in resultat.correlation_gain)
    assert all(e > 0 for e in resultat.ecarts_types_score)
    assert 0.0 <= resultat.trois_ex_aequo <= 1.0


def test_m3_mesure_bien_le_siege_du_greedy_et_pas_un_autre():
    """Le gain rendu par siege ne doit etre defini que pour les sieges effectivement occupes.

    A un greedy tournant sur les trois sieges, les trois valeurs existent. Le controle porte sur
    le fait qu'elles sont calculees sur les parties ou le greedy occupait CE siege, donc un tiers
    des parties chacune.
    """
    groupes = phase2.campagne_b(9)
    resultat = phase2.mesurer_m3(groupes, "essai", random.Random(2), nb_greedys=1)
    assert resultat.nb_parties == 27
    assert len(resultat.par_siege) == CONFIG.joueurs
    assert all(valeur == valeur for valeur in resultat.par_siege)  # noqa: PLR0124 - non-NaN


def test_m4_additionne_les_denominateurs_sans_melanger_les_sieges():
    """Le greedy change de siege d'une partie a l'autre : les compteurs doivent se cumuler.

    Denominateur attendu de B3 : une pose en domaine adverse par tour et par siege mesure, donc
    `parties x tours` -- et non `parties x tours x joueurs`, qui melangerait les adversaires.
    """
    groupes = phase2.campagne_b(9)
    comptes = phase2.mesurer_m4(groupes)
    assert comptes["B1-motif"].total == 27
    assert comptes["B3-expose"].total == 27 * CONFIG.tours
    assert comptes["B7-gaspillage"].total == 27 * CONFIG.tours


def test_b6_rend_une_distance_pour_chaque_groupe_de_categories():
    """Les trois groupes doivent etre renseignes, et la distance vivre dans `[0, 1]`."""
    from mesure import comportements as comp

    distances = phase2.mesurer_b6(phase2.campagne_b(12))
    assert set(distances) == set(comp.GROUPES_B6)
    for valeur in distances.values():
        assert valeur is None or 0.0 <= valeur <= 1.0


def test_le_tableau_de_dimensionnement_decroit_avec_l_ecart_et_l_appariement():
    """Plus l'ecart est grand, moins de parties ; et l'appariement en demande toujours moins."""
    lignes = phase2.tableau_de_dimensionnement(0.7, 0.5, (0.05, 0.10, 0.20))
    tailles_sans = [sans for _, sans, _ in lignes]
    assert tailles_sans == sorted(tailles_sans, reverse=True)
    for _, sans, avec in lignes:
        assert avec <= sans


def test_l_ecart_detectable_decroit_en_racine_de_n():
    """Quadrupler les parties divise par deux l'ecart detectable, exactement.

    C'est la lecture inverse du tableau de M2, celle qui repond a la question du protocole :
    son seuil de phase 3 est-il atteignable a 1 000 parties appariees ?
    """
    petit = phase2.ecart_detectable(0.7, 0.5, 1_000)
    grand = phase2.ecart_detectable(0.7, 0.5, 4_000)
    assert petit / grand == pytest.approx(2.0, abs=1e-12)
    assert phase2.ecart_detectable(0.7, 0.9, 1_000) < petit


def test_l_ecart_detectable_refuse_une_correlation_de_un():
    """A `rho = 1` les deux politiques sont indistinguables sur une donne : la borne s'applique.

    `ecart_detectable` borne `rho` a 0,999 plutot que de rendre 0, ce qui ferait lire « tout est
    detectable ». Le cas verifie que la borne mord.
    """
    borne = phase2.ecart_detectable(0.7, 1.0, 1_000)
    assert borne > 0.0
    assert borne == pytest.approx(phase2.ecart_detectable(0.7, 0.999, 1_000), abs=1e-15)


def test_une_correlation_negative_ne_fait_pas_exploser_le_dimensionnement():
    """`rho` peut etre negatif ; le tableau doit alors retomber sur le cas non apparie.

    Sans ce plancher, un `rho` mesure a `-0,3` rendrait un nombre de parties INFERIEUR au cas
    non apparie, ce qui ferait croire l'appariement gratuit alors qu'il ne l'est pas sur cette
    statistique-la.
    """
    lignes = phase2.tableau_de_dimensionnement(0.7, -0.4, (0.10,))
    _, sans, avec = lignes[0]
    assert avec == sans


# ---------------------------------------------------------------------------------
# Le budget : UNE fonction, appelee par les trois tables
# ---------------------------------------------------------------------------------
#
# La colonne « parties pour l'etablir » est la seule du rapport qui traduise un ecart en budget.
# Elle apparait dans trois tables, elle etait deduite sur place dans chacune, et l'une des trois
# s'est trompee d'un facteur trois. Ces cas tiennent la fonction unique et l'invariant qui rend
# l'erreur impossible.


def _compte(nom, succes, total, grain):
    from mesure import comportements as comp

    return comp.Compte(nom, succes, total, grain, comp.VUE_DECIDEUR)


def test_les_observations_par_partie_ne_dependent_pas_du_nombre_de_sieges_agreges():
    """**Le cas qui aurait attrape le facteur trois.**

    Un compteur `-par-partie` rend **une** observation de Bernoulli par partie -- « au moins un
    des trois sieges » est un seul booleen --, et cela **quel que soit** le nombre de sieges
    agreges : l'agregation est DANS son numerateur, pas dans son denominateur. Son nombre
    d'observations par partie vaut donc `1,0` a un siege comme a trois.

    Un compteur au grain du **couple** `(partie, siege)`, lui, en rend autant que de sieges
    mesures : `1,0` a un siege, `3,0` a trois.

    La table de la troisieme population divisait en plus par le nombre de sieges, ce qui comptait
    trois fois la meme partie et gonflait cinq budgets d'un facteur exactement trois.
    """
    parties = 10_002
    for sieges in (1, 3):
        par_partie = _compte(
            "B1-motif-par-partie",
            8254,
            parties,
            f"parties (au moins un des {sieges} sieges mesures)",
        )
        assert phase2.observations_par_partie(par_partie, parties) == 1.0, sieges

    un_siege = _compte("B1-motif", 4794, parties, "couples (partie, siege)")
    trois_sieges = _compte("B1-collectif", 21538, 3 * parties, "couples (partie, siege)")
    assert phase2.observations_par_partie(un_siege, parties) == 1.0
    assert phase2.observations_par_partie(trois_sieges, parties) == 3.0


def test_un_compteur_par_partie_dont_le_total_n_est_pas_le_nombre_de_parties_leve():
    """L'invariant qui rend le facteur trois impossible, asserte au lieu d'etre suppose.

    Le denominateur d'un compteur `-par-partie` **est** le nombre de parties, par construction.
    Si les deux divergent, ou le compteur ou le nombre de parties passe est faux, et dans les deux
    cas tout budget calcule ensuite est faux sans que rien ne le signale.
    """
    faux = _compte(
        "B1-motif-par-partie", 100, 3 * 10_002, "parties (au moins un des 3 sieges mesures)"
    )
    with pytest.raises(ValueError, match="par-partie"):
        phase2.observations_par_partie(faux, 10_002)
    with pytest.raises(ValueError, match="nombre de parties"):
        phase2.observations_par_partie(
            _compte("B1-motif", 1, 10, "couples (partie, siege)"), 0
        )


def test_le_budget_reproduit_trois_lignes_deja_auditees():
    """La fonction unique doit rendre, au chiffre pres, ce que le paragraphe 6 publie deja.

    Trois lignes auditees et reconstruites par l'humain : `B1-motif` **418**, `B3-expose` **72**,
    `B7-gaspillage` **320 163**. Si la fonction unique s'en ecartait, la centraliser aurait
    change des chiffres publies -- ce qui n'est pas une refactorisation.
    """
    parties = 10_002
    b1 = _compte("B1-motif", 4794, parties, "couples (partie, siege)")
    b3 = _compte("B3-expose", 13309, 4 * parties, "poses en domaine adverse")
    b7 = _compte("B7-gaspillage", 61, 4 * parties, "poses au banquet")

    assert phase2.budget_d_un_compteur(b1, parties, 4794 / parties - 10836 / 30006).parties == 418
    assert (
        phase2.budget_d_un_compteur(b3, parties, 13309 / 40008 - 56075 / 120024).parties == 72
    )
    budget_b7 = phase2.budget_d_un_compteur(b7, parties, 61 / 40008 - 203 / 120024)
    assert budget_b7.parties == 320_163
    # Les deux marqueurs calcules, sur la ligne qui les porte tous les deux.
    assert budget_b7.aveugle_par_le_bas is True
    assert budget_b7.hors_budget is True


def test_le_budget_de_la_troisieme_population_n_est_pas_divise_par_trois():
    """Les six lignes corrigees, dont une que l'audit n'avait pas listee.

    Valeurs reconstruites independamment par l'humain sur quatre des cinq lignes `-par-partie` :
    1 295, 299, 239, 280. La cinquieme, `B1-strict-par-partie`, vaut **10 400** sur les comptes
    bruts ; l'humain publie 10 396, obtenu avec l'ecart arrondi a `2,33` point au lieu de
    `2,329534`. C'est exactement le defaut qu'il signale lui-meme sur deux autres lignes, et les
    comptes bruts font foi.

    La sixieme ligne est `B1-collectif` au grain du **couple**, que l'audit n'a pas listee : elle
    etait fausse pour la meme raison mais avec une valeur juste differente -- son denominateur par
    partie vaut **3,0** et non 1,0 -- et elle passe de 2 234 a **745**.
    """
    parties = 10_002
    attendus = {
        "B1-collectif-par-partie": (9327, 8990, 1295),
        "B1-motif-par-partie": (8254, 7191, 299),
        "B1-tentative-par-partie": (9412, 8674, 239),
        "B1-strict-par-partie": (5917, 5684, 10400),
        "B1-savoir-commun-par-partie": (8289, 7199, 280),
    }
    for nom, (trois, hasard, attendu) in attendus.items():
        compte = _compte(nom, trois, parties, "parties (au moins un des 3 sieges mesures)")
        ecart = trois / parties - hasard / parties
        assert phase2.budget_d_un_compteur(compte, parties, ecart).parties == attendu, nom

    collectif = _compte("B1-collectif", 21538, 3 * parties, "couples (partie, siege)")
    ecart = 21538 / 30006 - 20157 / 30006
    resultat = phase2.budget_d_un_compteur(collectif, parties, ecart)
    assert resultat.par_partie == 3.0
    assert resultat.parties == 745


def test_le_marqueur_hors_budget_se_calcule_sur_le_budget_de_la_phase_3():
    """Strictement additif : un marqueur, aucun chiffre deplace.

    Un lecteur de la phase 3 doit voir d'un coup d'œil quels compteurs peuvent le servir a
    **1 000 parties**, sans recalculer. `B1-motif` a 418 parties est dans le budget ;
    `B1-collectif-par-partie` a 1 295 en sort.
    """
    parties = 10_002
    dedans = phase2.budget_d_un_compteur(
        _compte("B1-motif", 4794, parties, "couples (partie, siege)"),
        parties,
        4794 / parties - 10836 / 30006,
    )
    dehors = phase2.budget_d_un_compteur(
        _compte(
            "B1-collectif-par-partie", 9327, parties, "parties (au moins un des 3 sieges mesures)"
        ),
        parties,
        9327 / parties - 8990 / parties,
    )
    assert (dedans.parties, dedans.hors_budget) == (418, False)
    assert (dehors.parties, dehors.hors_budget) == (1295, True)
    assert phase2.BUDGET_PHASE_3 == 1_000


def test_un_ecart_nul_ou_absent_ne_rend_aucun_budget():
    """Aucun nombre de parties n'etablit un ecart nul.

    Et un ecart **absent** n'est pas un ecart de zero : les deux rendent `None`, jamais un
    nombre.
    """
    parties = 10_002
    compte = _compte("B1-motif", 4794, parties, "couples (partie, siege)")
    for ecart in (None, 0.0):
        resultat = phase2.budget_d_un_compteur(compte, parties, ecart)
        assert resultat.parties is None
        assert resultat.hors_budget is False

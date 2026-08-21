"""La mesure finale de la phase 3 : la ligne de base regeneree, et les gardes de grain.

Ce fichier ne teste **aucun chiffre de performance** : ceux-la viennent du run. Il teste que
la comparaison ne peut pas se faire de travers, et c'est tout ce qui compte avant d'avoir un
resultat -- une comparaison fausse rend un chiffre juste sur une population qui n'est pas la
sienne, et c'est le mode de defaut de ce projet.
"""

from __future__ import annotations

import pytest

from mesure import comportements as comp
from mesure import phase2, phase3
from mesure import phase3_mesure as mesure


def test_la_traduction_vers_les_groupes_de_la_phase_2_compte_UN_siege_par_trace():
    """`Groupe.sieges_mesures` porte un TUPLE par trace, pas un entier.

    Un entier passerait silencieusement dans `tous_les_comportements` et compterait autre
    chose : `sieges=list(3)` leverait, mais `sieges=list((3,))` ne leve pas et ne compte pas
    la meme population. Le cas verifie la forme, pas seulement la valeur.
    """
    campagne = phase3.jouer_composition(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=3,
        intitule="controle de traduction",
    )
    groupes = mesure.groupes_pour_m4(campagne)
    assert len(groupes) == 3
    for groupe, donne in zip(groupes, campagne.donnes, strict=True):
        assert groupe.seed == donne
        assert len(groupe.sieges_mesures) == phase3.CONFIG.joueurs
        for sieges in groupe.sieges_mesures:
            assert isinstance(sieges, tuple), f"{sieges!r} n'est pas un tuple"
            assert len(sieges) == 1, "la phase 3 compte UN siege par partie"
        # Les trois sieges sont couverts exactement une fois sur la donne.
        assert sorted(s for (s,) in groupe.sieges_mesures) == [0, 1, 2]


def test_la_ligne_de_base_regeneree_porte_le_grain_a_UN_siege():
    """Le libelle du grain porte le nombre de sieges agreges, et il doit dire « 1 ».

    C'est la parade posee au tour 2 de la phase 2 : le grain porte le nombre de sieges, la ou
    les deux libelles etaient auparavant identiques. Sans elle, `ecart_de_taux` comparerait
    « au moins un des 3 sieges » a « au moins un des 1 sieges » sans rien dire.
    """
    base = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    assert "1 sieges" in base["B1-motif-par-partie"].grain, base["B1-motif-par-partie"].grain
    assert base["B1-motif-par-partie"].total == 30 * phase3.CONFIG.joueurs


def test_la_ligne_de_base_a_TROIS_sieges_a_un_grain_DIFFERENT_et_la_garde_leve():
    """La raison d'etre de la regeneration, verifiee plutot qu'affirmee.

    La colonne « 3 greedys » de la phase 2 agrege trois sieges mesures. Comparer ses lignes
    `-par-partie` a celles de la phase 3 melangerait deux grains -- exactement le defaut
    bloquant du tour 1 de la phase 2, avec inversion de signe. `ecart_de_taux` doit LEVER.
    """
    un_siege = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    trois_sieges = phase2.mesurer_m4(phase2.campagne_b(30, nb_greedys=3))

    with pytest.raises(comp.GrainsIncomparables):
        comp.ecart_de_taux(
            un_siege["B1-motif-par-partie"], trois_sieges["B1-motif-par-partie"]
        )
    # Au grain du couple `(partie, siege)`, la comparaison EXISTE : l'unite comptee est la meme.
    assert comp.ecart_de_taux(un_siege["B1-motif"], trois_sieges["B1-motif"]) is not None


def test_les_deux_grains_ne_disent_pas_la_meme_chose_et_l_ecart_est_MASSIF():
    """Si les deux grains coincidaient, la regeneration ne servirait a rien.

    MESURE sur 60 donnes : `B1-motif-par-partie` vaut 44,44 % a un siege compte et 82,78 % a
    trois. Ce n'est pas une nuance -- c'est presque le double, et c'est ce que « au moins un
    des N sieges » fait quand N change.
    """
    un_siege = mesure.ligne_de_base_trois_greedys_un_siege(donnes=60)
    trois_sieges = phase2.mesurer_m4(phase2.campagne_b(60, nb_greedys=3))
    a = un_siege["B1-motif-par-partie"].taux()
    b = trois_sieges["B1-motif-par-partie"].taux()
    assert a is not None and b is not None
    assert b > a * 1.5, (
        f"les deux grains donnent {a:.4f} et {b:.4f} : ils ne different presque pas, et la "
        f"regeneration ne servirait a rien. Relire avant de conclure."
    )
    # Au grain du couple, en revanche, les deux mesurent la meme chose : ils doivent etre
    # proches. Ce sont les memes parties, un tiers des observations contre trois tiers.
    couple_a = un_siege["B1-motif"].taux()
    couple_b = trois_sieges["B1-motif"].taux()
    assert abs(couple_a - couple_b) < 0.10


def test_l_inclusion_B1_est_rejouee_sur_la_population_regeneree_aux_deux_grains():
    """Le controle dont la chute a deja revele un compteur faux.

    `ligne_de_base_trois_greedys_un_siege` l'appelle, et `verifier_inclusion_b1` **leve**. Le
    cas verifie que l'inclusion tient sur la population regeneree, aux deux grains, et que la
    garde mord si on la lui casse.
    """
    base = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    comp.verifier_inclusion_b1(base)  # ne leve pas

    casse = dict(base)
    collectif = casse["B1-collectif"]
    casse["B1-collectif"] = comp.Compte(
        nom=collectif.nom,
        succes=0,
        total=collectif.total,
        grain=collectif.grain,
        vue=collectif.vue,
    )
    with pytest.raises(ValueError):
        comp.verifier_inclusion_b1(casse)


def test_comparer_exclut_par_le_TEXTE_independamment_du_budget():
    """`B4-tout-dos` entre dans le budget a 6 000 parties -- et reste exclu.

    Les deux criteres sont **independants**, et confondre les deux serait relire une exclusion
    au lieu de la calculer.
    """
    base = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    comparaisons = {c.nom: c for c in mesure.comparer(base, base, 90, 90, budget=6_000)}
    for nom in mesure.EXCLUS_PAR_LE_TEXTE:
        assert comparaisons[nom].exclu is not None
        assert "texte" in comparaisons[nom].exclu, comparaisons[nom].exclu


def test_comparer_ne_declare_separable_aucune_ligne_quand_on_compare_une_population_a_ELLE_MEME():
    """Le controle de nullite : zero ecart, donc zero ligne separable. Sinon la mesure ment.

    C'est le plus simple des controles et c'est celui qui attrape une erreur de signe, un
    denominateur croise, ou une comparaison decalee d'une ligne.
    """
    base = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    comparaisons = mesure.comparer(base, base, 90, 90, budget=6_000)
    assert comparaisons, "aucune ligne comparee"
    for comparaison in comparaisons:
        assert comparaison.ecart == 0.0 or comparaison.ecart is None, comparaison.nom
        assert not comparaison.separable, comparaison.nom


def test_le_denominateur_errone_est_attrape_par_la_garde_DEJA_EXISTANTE():
    """Le controle du facteur trois existe deja, a un seul site : on l'exerce, on ne le double pas.

    **Une premiere version de `phase3_mesure` ajoutait sa propre garde pour ca.** Elle etait
    redondante : `phase2.observations_par_partie` **leve** deja, avec un message plus precis,
    et c'est la parade que l'audit du tour 2 de la phase 2 a imposee apres qu'un facteur trois
    indu eut survecu a deux verifications. Ecrire une seconde garde pour la meme regle est ce
    que le paragraphe 2 des conventions interdit -- deux definitions finissent par ne plus etre
    d'accord.

    Le cas verifie donc que la garde **existante** mord, et que `comparer` la traverse.
    """
    base = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)

    # La garde existante, exercee directement.
    assert phase2.observations_par_partie(base["B1-motif-par-partie"], 90) == 1.0
    with pytest.raises(ValueError, match="denominateur EST le nombre de parties"):
        phase2.observations_par_partie(base["B1-motif-par-partie"], 30)

    # Et `comparer` la traverse : un `nb_parties` errone y fait tomber la mesure.
    with pytest.raises(ValueError, match="denominateur EST le nombre de parties"):
        mesure.comparer(base, base, 30, 90, budget=6_000)


def test_le_grain_est_attrape_par_ecart_de_taux_et_le_denominateur_par_une_AUTRE_garde():
    """Deux gardes, deux fautes differentes : le cas le fige.

    Sans lui, un lecteur pourrait retirer l'une en croyant que l'autre la couvre. Le grain --
    « au moins un des 1 sieges » contre « des 3 sieges » -- passe **inapercu** de la garde des
    denominateurs, puisque les deux rendent exactement 1,0 observation par partie : la
    difference est dans le NUMERATEUR.
    """
    un_siege = mesure.ligne_de_base_trois_greedys_un_siege(donnes=30)
    trois_sieges = phase2.mesurer_m4(phase2.campagne_b(30, nb_greedys=3))

    # La garde des denominateurs ne dit RIEN de ce cas : 1,0 des deux cotes.
    assert phase2.observations_par_partie(un_siege["B1-motif-par-partie"], 90) == 1.0
    assert phase2.observations_par_partie(trois_sieges["B1-motif-par-partie"], 90) == 1.0
    # C'est `ecart_de_taux` qui leve.
    with pytest.raises(comp.GrainsIncomparables):
        comp.ecart_de_taux(
            un_siege["B1-motif-par-partie"], trois_sieges["B1-motif-par-partie"]
        )


def test_mesurer_rend_une_composition_NOMMEE_et_remesure_sigma():
    """Un resultat qui ne nomme pas sa composition n'est pas auditable.

    Et `sigma` est **remesure** sur la composition reelle : celui de la pre-inscription est
    mesure sous l'hypothese nulle, et l'ecart entre le SUPPOSE et le MESURE doit etre un
    chiffre.
    """
    resultat = mesure.mesurer(
        agent=phase3.greedy_de_reference,
        adversaire=phase3.greedy_de_reference,
        donnes=20,
        intitule="1 greedy contre 2 greedys (controle)",
        depart=phase3.DEPART_DONNE.__add__(500_000),
    )
    assert "greedy" in resultat.intitule
    assert resultat.verdict.intitule == resultat.intitule
    assert resultat.dimensionnement.intitule == resultat.intitule
    assert resultat.nb_parties == resultat.nb_donnes * phase3.CONFIG.joueurs == 60
    assert resultat.dimensionnement.sigma_gain > 0
    assert set(resultat.comportements) >= {"B1-motif", "B4-brut", "B7-gaspillage"}

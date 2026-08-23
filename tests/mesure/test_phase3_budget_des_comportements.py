"""Le recalcul des marqueurs de M4 au budget de la phase 3.

Le rapport de la phase 2 marque 19 lignes hors budget et 2 aveugles par le bas, **calculees
sur 1 000 parties**. La phase 3 s'en donne 6 000. Ces cas verifient que le recalcul est un
recalcul, et non une reecriture :

1. il **retrouve** les chiffres publies au budget publie -- sinon rien de ce qu'il dit ailleurs
   ne vaut ;
2. la garde **leve** quand il ne les retrouve pas ;
3. les deux marqueurs bougent dans le **bon sens** avec le budget ;
4. il compte des **noms**, pas un total : un compteur publie deux fois dans le rapport n'entre
   qu'une fois.
"""

from __future__ import annotations

import dataclasses

import pytest

from mesure import phase2
from mesure import phase3_budget_des_comportements as budget


def test_la_reconstruction_retrouve_les_chiffres_publies_par_la_phase_2():
    """19 hors budget et 2 aveugles a 1 000 parties. Le controle qui rend le reste lisible."""
    lignes = budget.lignes_de_budget(6_000)
    budget.verifier_contre_la_phase_2(lignes)  # leve si ca ne tombe pas juste

    assert len(lignes) == 34
    assert sum(1 for x in lignes if x.hors_budget_1000) == budget.HORS_BUDGET_PUBLIE == 19
    assert sum(1 for x in lignes if x.aveugle_1000) == budget.AVEUGLES_PUBLIES == 2


def test_la_garde_leve_si_la_reconstruction_ne_tombe_pas_juste():
    """Une garde qui ne mord pas ne garde rien : on la fait mordre.

    Le cas fabrique une reconstruction fausse -- une ligne retiree, puis un marqueur retourne --
    et exige que la garde le dise, avec le compte attendu dans son message.
    """
    lignes = budget.lignes_de_budget(6_000)

    with pytest.raises(ValueError, match="33 compteurs reconstruits"):
        budget.verifier_contre_la_phase_2(lignes[:-1])

    fausses = list(lignes)
    premier_hors = next(i for i, x in enumerate(fausses) if x.hors_budget_1000)
    fausses[premier_hors] = dataclasses.replace(
        fausses[premier_hors], hors_budget_1000=False
    )
    with pytest.raises(ValueError, match="18 hors budget"):
        budget.verifier_contre_la_phase_2(fausses)


def test_les_marqueurs_bougent_dans_le_bon_sens_avec_le_budget():
    """Plus de parties ne peut pas rendre une ligne MOINS separable. C'est monotone.

    Le cas verifie la monotonie ligne a ligne, pas seulement sur le total : un total peut rester
    stable en masquant deux mouvements de sens contraire.
    """
    for gros in (2_000, 6_000, 20_000):
        for ligne in budget.lignes_de_budget(gros):
            if ligne.hors_budget_6000:
                assert ligne.hors_budget_1000, (
                    f"{ligne.nom} est hors budget a {gros} parties mais dans le budget a "
                    f"1 000 : plus de parties a rendu la ligne moins separable"
                )
            if ligne.aveugle_6000:
                assert ligne.aveugle_1000, (
                    f"{ligne.nom} est aveugle par le bas a {gros} parties mais pas a 1 000"
                )
            if ligne.detectable_1000 is not None and ligne.detectable_6000 is not None:
                assert ligne.detectable_6000 <= ligne.detectable_1000


def test_a_6000_parties_B7_cesse_d_etre_aveugle_par_le_bas():
    """Le resultat qui change une instruction, et il est verifie plutot qu'affirme.

    Le prompt de la phase 3 dit « n'annonce aucune difference sur ces lignes », et c'est juste
    **au budget de 1 000 parties**. Le critere etant calcule ligne a ligne, il change avec le
    budget : a 6 000 parties, un agent a zero exact EST separable du greedy sur les deux lignes
    de `B7-gaspillage`.

    Ce que ca ne change pas : `B7-occasions` vaut 1,22 % des poses au banquet. B7 devient
    separable par le bas, il ne devient pas informatif sur le jeu.
    """
    lignes = {x.nom: x for x in budget.lignes_de_budget(6_000)}
    for nom in ("B7-gaspillage", "B7-gaspillage-vraie"):
        ligne = lignes[nom]
        assert ligne.aveugle_1000, f"{nom} n'etait pas aveugle a 1 000 parties"
        assert not ligne.aveugle_6000, f"{nom} est encore aveugle a 6 000 parties"
        assert ligne.detectable_6000 < ligne.taux, (
            f"{nom} : detectable {ligne.detectable_6000:.4%} contre taux {ligne.taux:.4%}"
        )
    # Et les deux restent hors budget pour l'ecart greedy-hasard : deux criteres distincts.
    assert lignes["B7-gaspillage"].hors_budget_6000
    assert lignes["B7-gaspillage-vraie"].hors_budget_6000


def test_les_huit_lignes_hors_budget_a_6000_parties_sont_NOMMEES():
    """Un compte n'est pas une liste de noms -- la faute sortie cinq fois en phase 2.

    Les huit sont ecrites ici. Si le recalcul en designe d'autres, ce cas tombe en disant
    lesquelles, et le rapport doit etre relu avant d'etre corrige.
    """
    attendues = {
        "B2-banquet",
        "B2-destination/banquet-Disgrace",
        "B2-destination/domaine adverse",
        "B4-departage",
        "B5-renfort",
        "B7-gaspillage",
        "B7-gaspillage-vraie",
        "B7-occasions",
    }
    trouvees = {x.nom for x in budget.lignes_de_budget(6_000) if x.hors_budget_6000}
    assert trouvees == attendues, (
        f"le lot hors budget a change.\n  en trop : {sorted(trouvees - attendues)}\n"
        f"  manquantes : {sorted(attendues - trouvees)}"
    )


def test_aucun_compteur_n_est_compte_deux_fois():
    """Le rapport publie certaines lignes dans deux tables : le doublon ne doit pas entrer."""
    noms = [x.nom for x in budget.lignes_de_budget(6_000)]
    assert len(noms) == len(set(noms)), (
        f"doublons : {sorted(n for n in set(noms) if noms.count(n) > 1)}"
    )


def test_le_budget_de_la_phase_2_reste_celui_qu_elle_a_publie():
    """`BUDGET_PHASE_3` du module de la phase 2 n'est pas modifie par la phase 3.

    Le changer ferait bouger le rapport livre de la phase 2, qui est un livrable audite et
    accepte. La phase 3 passe son budget **en argument** ; elle ne deplace pas l'etalon.
    """
    assert phase2.BUDGET_PHASE_3 == 1_000

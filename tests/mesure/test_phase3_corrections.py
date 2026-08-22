"""Les corrections du tour 2, chacune avec ce qui l'empeche de se defaire.

Un defaut corrige sans parade revient : c'est la seule regle du paragraphe 0.2 que ce projet
ait verifiee cinq fois. Chaque cas ci-dessous reinjecte la faute et exige le rouge.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from mesure import bootstrap as boot
from mesure import comportements as comp
from mesure import phase3_courbe, phase3_mesure


def compte(nom: str, succes: int, total: int, grain: str = "parties") -> comp.Compte:
    return comp.Compte(nom, succes, total, grain, "publique")


# ---------------------------------------------------------------------------------------
# L'ecart apparie -- le socle qui manquait
# ---------------------------------------------------------------------------------------


def test_l_ecart_apparie_voit_un_progres_que_deux_intervalles_de_NIVEAU_ne_voient_pas():
    """**Le coeur du bloquant 1.** Deux series bruitees mais appariees : leurs niveaux ont des
    intervalles qui se recouvrent largement, et pourtant l'ecart est etabli.

    C'est pour cela qu'on ne lit pas un ecart au recouvrement de deux intervalles de niveau --
    le recouvrement ignore la correlation que l'appariement rend forte.
    """
    alea = random.Random(1)
    fond = [alea.uniform(0.0, 1.0) for _ in range(600)]
    avant = [x for x in fond]
    apres = [x + 0.03 for x in fond]

    ecart = boot.bootstrap_apparie_par_donne(avant, apres, 2_000, random.Random(2), risque=0.01)
    assert ecart.etabli, ecart.intervalle
    assert ecart.moyenne == pytest.approx(0.03, abs=1e-9)

    # Les intervalles des deux NIVEAUX, eux, se recouvrent presque entierement.
    niveau_avant = boot.bootstrap_par_donne([[x] for x in avant], 2_000, random.Random(3))
    niveau_apres = boot.bootstrap_par_donne([[x] for x in apres], 2_000, random.Random(4))
    assert niveau_avant.intervalle[1] > niveau_apres.intervalle[0], (
        "les deux niveaux devraient se recouvrir : sans cela le cas ne montre rien"
    )


def test_l_ecart_apparie_ne_voit_PAS_un_progres_sous_le_bruit():
    """L'autre erreur : il ne doit pas etablir ce qui n'est pas la."""
    alea = random.Random(5)
    avant = [alea.uniform(0.0, 1.0) for _ in range(600)]
    apres = [alea.uniform(0.0, 1.0) for _ in range(600)]
    ecart = boot.bootstrap_apparie_par_donne(avant, apres, 2_000, random.Random(6), risque=0.01)
    assert not ecart.etabli, ecart.intervalle


def test_l_ecart_apparie_REFUSE_deux_series_de_longueurs_differentes():
    """Apparier au rang deux series inegales comparerait deux donnes differentes en silence."""
    with pytest.raises(ValueError, match="MEMES donnes"):
        boot.bootstrap_apparie_par_donne([0.1, 0.2], [0.1], 100, random.Random(0))


# ---------------------------------------------------------------------------------------
# La courbe : elle refuse de publier un ecart qu'elle ne peut pas calculer
# ---------------------------------------------------------------------------------------


def test_la_courbe_REFUSE_de_deduire_un_ecart_de_deux_NIVEAUX():
    """La parade du bloquant 1 : sans serie par donne, aucun ecart n'est publie -- au lieu
    d'etre devine a partir des niveaux, ce qui est exactement ce qui a mal tourne."""
    jalons = [
        {"numero": 1, "part_fractionnee": 0.57},
        {"numero": 2, "part_fractionnee": 0.70},
    ]
    with pytest.raises(ValueError, match="ne se reconstruit pas"):
        phase3_courbe.ecarts(jalons, 1, 0.01)


def test_la_courbe_refuse_une_portee_nulle():
    with pytest.raises(ValueError, match="au moins 1"):
        phase3_courbe.ecarts([{"numero": 1, "parts_par_donne": [0.5]}], 0, 0.01)


def test_la_courbe_du_RUN_REEL_dit_ce_que_le_rapport_publie():
    """Les chiffres du tour 2, refaits ici : l'agent apprend, mais aucun pas isole n'est etabli."""
    journal = Path("models/phase3/journal.jsonl")
    if not journal.exists():
        pytest.skip("le journal du run n'est pas dans le depot")
    jalons = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
    if not all(j.get("parts_par_donne") for j in jalons):
        pytest.skip("journal sans serie par donne")
    risque = 0.01 / 8

    extremes = phase3_courbe.ecart_des_extremes(jalons, risque)
    assert extremes.etabli, extremes.intervalle
    assert extremes.moyenne > 0.10, extremes.moyenne

    consecutifs = phase3_courbe.ecarts(jalons, 1, risque)
    assert len(consecutifs) == 7
    assert not any(e.etabli for e in consecutifs), (
        "un pas consecutif est etabli : la phrase « il progressait encore au dernier » "
        "redeviendrait defendable, et le rapport doit alors etre relu"
    )
    assert not consecutifs[-1].etabli


def test_completer_le_journal_est_idempotente():
    journal = Path("models/phase3/journal.jsonl")
    if not journal.exists():
        pytest.skip("le journal du run n'est pas dans le depot")
    avant = journal.read_text(encoding="utf-8")
    if "parts_par_donne" not in avant:
        pytest.skip("journal pas encore complete")
    from agents.campagne import DONNES_GARDE_FOU

    phase3_courbe.completer(Path("models/phase3"), DONNES_GARDE_FOU)
    assert journal.read_text(encoding="utf-8") == avant


# ---------------------------------------------------------------------------------------
# L'ecart detectable a DEUX echantillons -- defaut 8
# ---------------------------------------------------------------------------------------


def test_le_detectable_a_deux_echantillons_corrige_B4_strict():
    """Le chiffre exact que l'audit a recalcule : 2,37 pt publie contre 3,96 pt reel."""
    detectable = phase3_mesure.ecart_detectable_deux_echantillons(
        compte("B4-strict", 391, 3814, "refus"), 6000,
        compte("B4-strict", 622, 1967, "refus"), 6000,
        6000,
    )
    assert detectable == pytest.approx(0.0396, abs=0.0002), detectable


def test_le_detectable_a_deux_echantillons_retombe_sur_la_formule_de_la_phase_2_a_effectifs_EGAUX():
    """L'unite avant la valeur : a effectifs et taux egaux, les deux formules coincident."""
    from mesure import phase2

    a = compte("X", 3000, 6000)
    detectable = phase3_mesure.ecart_detectable_deux_echantillons(a, 6000, a, 6000, 6000)
    reference = phase2.ecart_de_taux_detectable(0.5, 1.0, 6000)
    assert detectable == pytest.approx(reference, rel=1e-9)


def test_le_detectable_rend_None_sur_un_taux_degenere():
    """Un zero exact a une variance binomiale nulle : la formule normale rendrait « tout est
    detectable », ce qui est exactement faux. Il se traite par sa borne exacte."""
    assert (
        phase3_mesure.ecart_detectable_deux_echantillons(
            compte("X", 0, 1967, "refus"), 6000, compte("X", 100, 3814, "refus"), 6000, 6000
        )
        is None
    )


def test_aucune_ligne_ne_change_de_STATUT_avec_la_formule_corrigee():
    """L'audit l'a verifie sur les 34 lignes ; ce cas le fige sur les cinq lignes concernees."""
    lignes = [
        # nom, agent (succes/total), base (succes/total), separable attendu
        ("B4-strict", (391, 3814), (622, 1967), True),
        ("B4-departage", (2055, 3814), (1345, 1967), True),
        ("B4-contre-nature", (1368, 3814), (1, 1967), True),
        ("B4-meurtre-couteux", (298, 8131), (1, 10382), True),
        ("B5-renfort", (2270, 12454), (1746, 13159), True),
    ]
    for nom, (sa, na), (sb, nb), attendu in lignes:
        resultat = phase3_mesure.comparer(
            {nom: compte(nom, sa, na, "occasions")},
            {nom: compte(nom, sb, nb, "occasions")},
            6000, 6000, budget=6000,
        )[0]
        if resultat.exclu is not None:
            continue
        assert resultat.separable is attendu, (nom, resultat.ecart, resultat.detectable)


# ---------------------------------------------------------------------------------------
# La regle « hors budget » -- defaut 6
# ---------------------------------------------------------------------------------------


def test_une_ligne_non_separable_publie_le_nombre_de_parties_qu_il_faudrait():
    """La regle pre-inscrite etait une branche inatteignable ; elle devient un nombre lisible."""
    resultat = phase3_mesure.comparer(
        {"X": compte("X", 3000, 6000)}, {"X": compte("X", 3010, 6000)}, 6000, 6000, budget=6000
    )[0]
    assert not resultat.separable
    assert resultat.parties_requises is not None
    assert resultat.parties_requises > 6000, resultat.parties_requises


def test_une_ligne_separable_ne_publie_PAS_de_parties_requises():
    resultat = phase3_mesure.comparer(
        {"X": compte("X", 1000, 6000)}, {"X": compte("X", 3000, 6000)}, 6000, 6000, budget=6000
    )[0]
    assert resultat.separable
    assert resultat.parties_requises is None


def test_parties_requises_et_separable_sont_le_MEME_critere():
    """`parties_requises > budget` doit equivaloir a `|ecart| < detectable`. Deux ecritures du
    meme critere qui divergeraient rendraient le tableau incoherent avec lui-meme."""
    for succes_base in range(2900, 3101, 20):
        resultat = phase3_mesure.comparer(
            {"X": compte("X", 3000, 6000)},
            {"X": compte("X", succes_base, 6000)},
            6000, 6000, budget=6000,
        )[0]
        if resultat.ecart == 0 or resultat.exclu is not None:
            continue
        if resultat.separable:
            assert resultat.parties_requises is None
        else:
            assert resultat.parties_requises is not None
            assert resultat.parties_requises > 6000, (succes_base, resultat.parties_requises)


# ---------------------------------------------------------------------------------------
# La garde de grain de l'inclusion B1 -- defaut 12
# ---------------------------------------------------------------------------------------


def test_l_inclusion_b1_LEVE_desormais_sur_deux_grains_differents():
    """Elle ne consultait `grain` que pour composer son message d'erreur."""
    with pytest.raises(comp.GrainsIncomparables):
        comp.verifier_inclusion_b1(
            {
                "B1-collectif": compte("B1-collectif", 50, 100, "parties (3 sieges)"),
                "B1-motif": compte("B1-motif", 40, 24_000, "familles x parties"),
            }
        )


def test_l_inclusion_b1_mord_toujours_sur_l_inclusion_elle_meme():
    """La garde neuve ne doit pas avoir desactive celle qui marchait."""
    with pytest.raises(ValueError, match="inclusion tombee"):
        comp.verifier_inclusion_b1(
            {
                "B1-collectif": compte("B1-collectif", 5, 100),
                "B1-motif": compte("B1-motif", 9, 100),
            }
        )


def test_l_inclusion_b1_laisse_passer_une_population_saine_aux_deux_grains():
    comp.verifier_inclusion_b1(
        {
            "B1-collectif": compte("B1-collectif", 50, 100),
            "B1-motif": compte("B1-motif", 40, 100),
            "B1-collectif-par-partie": compte("B1-collectif-par-partie", 50, 100),
            "B1-motif-par-partie": compte("B1-motif-par-partie", 40, 100),
        }
    )

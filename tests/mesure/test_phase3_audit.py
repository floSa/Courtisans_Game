"""L'auto-audit : chaque controle doit pouvoir ECHOUER -- ou dire qu'il ne le peut pas.

Un controle qui ne peut pas echouer ne prouve rien. C'est la lecon que le greedy a laissee --
chacune de ses trois preuves est assortie d'un cas qui verifie que le piege mord -- et elle
vaut mot pour mot ici : `mesure/phase3_audit.py` est ecrit avant le resultat, donc personne ne
peut savoir qu'il mord tant qu'on ne le lui a pas fait faire.

**Ce fichier ne tenait pas cette promesse, et l'audit du tour 1 l'a montre.** Il cassait six
controles sur dix. Des quatre autres : deux passaient un `True` **litteral** -- aucune entree
ne pouvait les faire tomber --, un eprouvait `bootstrap_par_donne` sur des donnees fabriquees
sans jamais toucher le controle, et le dernier verifiait la **forme** de la preuve. Le compte
rendu affirmait pourtant que **chacun** des dix etait verifie capable d'echouer.

Trois choses ici, donc :

  - les **huit** controles eprouvables sont casses, chacun par reinjection de la faute qu'il
    pretend attraper ;
  - les **deux** releves sont verifies **relevés** -- ils listent, et le disent ;
  - `test_aucun_controle_eprouve_ne_passe_un_booleen_litteral` **lit l'AST du module** : c'est
    la parade qui empeche le defaut de revenir, la ou une docstring ne l'empechait pas.
"""

from __future__ import annotations

import dataclasses
import random

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
        detectable=0.1, separable=False, parties_requises=None, exclu=None,
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
        detectable=None, separable=False, parties_requises=None,
        exclu="texte de la definition",
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


# ---------------------------------------------------------------------------------------
# Les quatre controles que l'audit du tour 1 a trouves NON casses
# ---------------------------------------------------------------------------------------


def test_aucun_controle_eprouve_ne_passe_un_booleen_litteral():
    """**La parade.** Un `True` en dur dans un `_epreuve` fait un controle qui ne peut pas
    echouer, et c'est exactement ce que R4 et R5 faisaient. Une docstring ne l'empeche pas ;
    l'AST, si.
    """
    import ast
    import pathlib

    source = pathlib.Path(audit.__file__).read_text(encoding="utf-8")
    arbre = ast.parse(source)
    fautifs = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        nom = getattr(noeud.func, "id", None)
        if nom != "_epreuve":
            continue
        # `_epreuve(code, intitule, passe, preuve)` : le troisieme argument est le predicat.
        if len(noeud.args) >= 3 and isinstance(noeud.args[2], ast.Constant):
            if isinstance(noeud.args[2].value, bool):
                fautifs.append(f"ligne {noeud.lineno} : passe={noeud.args[2].value!r}")
    assert not fautifs, (
        "un controle eprouve porte un booleen litteral, donc il ne peut pas echouer : "
        + " ; ".join(fautifs)
        + ". Utiliser `_releve` si le controle liste sans juger."
    )


def test_le_controle_du_niveau_nul_MORD_sur_un_instrument_decalibre():
    """La faute que ce controle pretend attraper : un niveau nul qui n'est pas a zero.

    On met a la place du greedy une politique qui n'est PAS l'egale de ses deux adversaires --
    l'uniforme. L'esperance du gain mesure n'est alors plus nulle, et le controle doit le voir.
    Au tour 1, ce controle n'etait eprouve que sur la **forme** de sa preuve.
    """
    bon = audit.controle_niveau_nul(donnes=20, depart=phase3_mesure.DEPART_CAMPAGNE_FINALE)
    assert bon.passe, bon.preuve
    assert bon.statut == "concluant"

    casse = audit.controle_niveau_nul(
        donnes=20,
        depart=phase3_mesure.DEPART_CAMPAGNE_FINALE,
        agent=phase3.uniforme,
    )
    assert not casse.passe, casse.preuve
    assert casse.statut == "en echec"


def test_le_controle_de_bootstrap_MORD_si_le_bootstrap_tirait_des_PARTIES(monkeypatch):
    """La faute exacte : un bootstrap qui tirerait des parties rend un effet de plan de 1,0.

    Au tour 1, le cas eprouvait `boot.bootstrap_par_donne` sur des donnees fabriquees -- utile,
    mais il ne faisait jamais tomber le controle lui-meme.

    Le support est construit a la main et porte la structure de la composition reelle : les
    trois sieges d'une donne se partagent une somme nulle, donc `rho` y est **negatif** et
    l'effet de plan franchement sous 1. C'est cette structure que le controle doit voir
    disparaitre si le bootstrap se met a tirer des parties.
    """
    from mesure import bootstrap as boot

    class SupportConstruitALaMain:
        """Ce que `controle_bootstrap_par_donne` regarde, et rien de plus."""

        replicats_par_donne = 3

        def gains_par_donne(self):
            # Somme nulle dans chaque donne -- `rho` negatif --, plus une derive lente entre
            # donnes pour que l'effet de plan ne soit pas EXACTEMENT nul : la composition
            # reelle est a 0,887, pas a 0.
            alea = random.Random(4)
            groupes = []
            for _ in range(200):
                a = alea.uniform(-1.0, 1.0)
                b = alea.uniform(-1.0, 1.0)
                groupes.append([a, b, -(a + b)])
            return groupes

    support = SupportConstruitALaMain()
    bon = audit.controle_bootstrap_par_donne(support)
    assert bon.passe, bon.preuve

    vrai = boot.bootstrap_par_donne

    def tire_des_parties(observations, repetitions, alea, risque=0.01):
        """La faute reinjectee : chaque partie devient sa propre donne."""
        plates = [[valeur] for groupe in observations for valeur in groupe]
        return vrai(plates, repetitions, alea, risque)

    monkeypatch.setattr(audit.boot, "bootstrap_par_donne", tire_des_parties)
    casse = audit.controle_bootstrap_par_donne(support)
    assert not casse.passe, casse.preuve
    assert casse.statut == "en echec"


def test_R4_est_un_RELEVE_et_regarde_les_DEUX_cotes():
    """Il ne peut pas echouer -- il liste --, et il doit le dire. Et il ne voyait que l'agent :
    les deux zeros absolus que le rapport publie sont du cote de la ligne de base."""

    def compte(nom, succes, total):
        from mesure import comportements as comp

        return comp.Compte(nom, succes, total, "refus", "publique")

    def comparaison(nom, a, b):
        return phase3_mesure.Comparaison(
            nom=nom, agent=a, base=b, ecart=0.0, detectable=1.0,
            separable=False, parties_requises=None, exclu=None,
        )

    lignes = [
        comparaison("B4-contre-nature", compte("a", 1368, 3814), compte("b", 0, 1967)),
        comparaison("B4-meurtre-couteux", compte("a", 298, 8131), compte("b", 0, 10382)),
    ]
    controle = audit.controle_zeros(lignes)
    assert controle.statut == "releve"
    assert not controle.eprouve
    assert "2 valeur(s) extreme(s)" in controle.preuve, controle.preuve
    assert "B4-contre-nature [ligne de base]" in controle.preuve, controle.preuve
    assert "B4-meurtre-couteux [ligne de base]" in controle.preuve, controle.preuve


def test_R5_est_un_RELEVE_et_le_dit():
    """Un facteur dix sur l'unite le laissait « concluant » au tour 1. Il liste, et il le dit."""
    from mesure import comportements as comp

    class FausseMesure:
        comportements = {"X": comp.Compte("X", 5, 1000, "poses", "publique")}
        nb_parties = 100

    controle = audit.controle_unite_avant_valeur(
        FausseMesure(), {"X": comp.Compte("X", 5, 100, "poses", "publique")}, 100
    )
    assert controle.statut == "releve"
    assert "10.000 vs 1.000" in controle.preuve, controle.preuve


def test_R2_voit_le_doublon_de_nom_QUI_A_ECHAPPE_au_tour_1():
    """La composition du garde-fou portait le meme nom qu'une ligne du pool, et R2 ne voyait
    rien parce qu'il ne s'appliquait qu'au pool."""
    from agents import campagne as campagne_module

    mesure = _mesure()
    homonyme = dataclasses.replace(mesure, intitule=campagne_module.intitule_du_garde_fou())
    assert audit.controle_populations_nommees([mesure], []).passe
    casse = audit.controle_populations_nommees(
        [homonyme], [campagne_module.intitule_du_garde_fou()]
    )
    assert not casse.passe, casse.preuve
    assert "doublons" in casse.preuve, casse.preuve


def test_les_intitules_du_depot_sont_deux_a_deux_DISTINCTS():
    """**La parade du defaut 5.** Deux campagnes differentes ne peuvent plus porter le meme nom
    sans que ce cas ne tombe -- il lit les litteraux de tout le code de mesure, pas seulement
    ceux qu'un appelant a pense passer a R2.
    """
    import ast
    import pathlib

    vus: dict[str, list[str]] = {}
    for chemin in sorted(
        list(pathlib.Path("mesure").glob("*.py")) + list(pathlib.Path("agents").glob("*.py"))
    ):
        arbre = ast.parse(chemin.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.Call):
                continue
            for motcle in noeud.keywords:
                if motcle.arg != "intitule":
                    continue
                if isinstance(motcle.value, ast.Constant) and isinstance(
                    motcle.value.value, str
                ):
                    vus.setdefault(motcle.value.value, []).append(
                        f"{chemin}:{motcle.value.lineno}"
                    )
    doublons = {nom: ou for nom, ou in vus.items() if len(ou) > 1}
    assert not doublons, (
        "deux campagnes portent le meme intitule, donc deux populations differentes se "
        f"liraient comme une seule : {doublons}"
    )


def test_l_audit_complet_separe_les_EPROUVES_des_RELEVES():
    """« Dix controles, aucun en echec » comptait deux controles qui ne pouvaient pas tomber."""
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
    assert {c.statut for c in controles} <= set(audit.STATUTS)
    eprouves = [c for c in controles if c.eprouve]
    releves = [c for c in controles if not c.eprouve]
    assert len(eprouves) == 8, [c.code for c in eprouves]
    assert {c.code for c in releves} == {"R4", "R5"}, [c.code for c in releves]


def test_un_statut_inconnu_est_refuse():
    """Un troisieme degre de reussite invente en passant ne doit pas s'installer."""
    import pytest

    with pytest.raises(ValueError, match="statut"):
        audit.Controle(code="Q1", intitule="x", statut="presque", preuve="1")

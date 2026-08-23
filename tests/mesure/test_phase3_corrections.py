"""Les corrections du tour 2, chacune avec ce qui l'empeche de se defaire.

Un defaut corrige sans parade revient : c'est la seule regle du paragraphe 0.2 que ce projet
ait verifiee cinq fois. Chaque cas ci-dessous reinjecte la faute et exige le rouge.
"""

from __future__ import annotations

import json
import re
import random
from pathlib import Path

import pytest

from agents import campagne
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
    # Demande au module qui le fixe, jamais recopie : le tour 2 ecrivait `0.01 / 8` ici, un
    # `8` qui n'aurait plus rien voulu dire si le nombre de checkpoints changeait.
    risque = 0.01 / campagne.CHECKPOINTS_ATTENDUS

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
    """Le chiffre exact que l'audit a recalcule : 2,37 pt publie contre 3,96 pt reel.

    **Les comptes sont ceux que `test_les_comptes_de_ce_fichier_sont_CEUX_DU_RAPPORT_PUBLIE`
    va relire dans le rapport**, pas des nombres choisis ici : c'est la parade du defaut B, et
    elle couvre ce cas-ci autant que le sien.
    """
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


def test_les_cinq_lignes_aux_effectifs_INEGAUX_avec_leurs_comptes_REELS():
    """Les cinq lignes dont les deux cotes n'ont pas le meme denominateur, **telles qu'elles
    sont dans `mesure/resultats/phase3.md`** -- et le tour 2 les avait maquillees.

    **Ce cas s'appelait « aucune ligne ne change de statut », et il ecrivait `1` la ou la
    mesure dit `0`.** Sur les deux seules lignes qui changent de statut, et sur elles seules.
    Avec le `1`, les deux redevenaient separables par la formule normale et le cas passait au
    vert : un cas dont on choisit les donnees pour qu'il passe ne teste rien. C'est la meme
    famille que le test de la phase 2 dont le nom disait « refuse » quand le corps affirmait
    que l'appel reussissait, a ceci pres qu'ici l'assertion etait juste et l'**entree**
    falsifiee -- ce qui est plus difficile a voir en relisant.

    Le nom aussi est corrige, parce qu'il portait la conclusion fausse. **Deux lignes changent
    de statut** : `B4-contre-nature` et `B4-meurtre-couteux` sortent de la regle normale, qui
    ne sait pas traiter leur zero, et sont tranchees par leurs bornes exactes. Elles restent
    separables -- mais par une AUTRE regle, et le tableau doit le dire.
    """
    lignes = [
        # nom, agent (succes/total), base (succes/total), separable, regle
        ("B4-strict", (391, 3814), (622, 1967), True, phase3_mesure.REGLE_DETECTABLE),
        ("B4-departage", (2055, 3814), (1345, 1967), True, phase3_mesure.REGLE_DETECTABLE),
        ("B4-contre-nature", (1368, 3814), (0, 1967), True, phase3_mesure.REGLE_BORNES_EXACTES),
        ("B4-meurtre-couteux", (298, 8131), (0, 10382), True, phase3_mesure.REGLE_BORNES_EXACTES),
        ("B5-renfort", (2270, 12454), (1746, 13159), True, phase3_mesure.REGLE_DETECTABLE),
    ]
    for nom, (sa, na), (sb, nb), attendu, regle in lignes:
        resultat = phase3_mesure.comparer(
            {nom: compte(nom, sa, na, "occasions")},
            {nom: compte(nom, sb, nb, "occasions")},
            6000, 6000, budget=6000,
        )[0]
        if resultat.exclu is not None:
            continue
        assert resultat.separable is attendu, (nom, resultat.ecart, resultat.detectable)
        assert resultat.regle == regle, (nom, resultat.regle)


def test_la_borne_exacte_d_un_zero_est_celle_de_CLOPPER_PEARSON():
    """Les deux chiffres que le pilote a recalcules de son cote, au quatrieme decimal.

    La borne se lit sans table : la probabilite de n'observer aucun succes sur `n` tirages de
    taux `p` vaut `(1-p)**n`, et la borne est le `p` qui l'egale au risque. Le cas la verifie
    dans les deux sens -- par la formule fermee ET par la definition qu'elle resout.
    """
    for total, attendu in ((1967, 0.002338), (10382, 0.0004435)):
        borne = phase3_mesure.borne_haute_exacte_d_un_zero(total)
        assert borne == pytest.approx(attendu, rel=1e-3), (total, borne)
        # La definition : a cette borne, ne rien observer a exactement 1 % de chance.
        assert (1 - borne) ** total == pytest.approx(0.01, rel=1e-9)


def test_les_bornes_exactes_REFUSENT_un_effectif_nul():
    """Zero succes sur zero occasion n'est pas un taux nul : c'est une absence d'occasion, et
    elle ne se borne pas. Rendre 100 % ferait lire « le taux peut valoir n'importe quoi », ce
    qui est vrai mais s'ecrit en refusant de repondre."""
    with pytest.raises(ValueError, match="strictement positif"):
        phase3_mesure.borne_haute_exacte_d_un_zero(0)
    with pytest.raises(ValueError, match="strictement positif"):
        phase3_mesure.borne_basse_exacte_d_un_cent(0)
    with pytest.raises(ValueError, match=r"\]0 ; 1\["):
        phase3_mesure.borne_haute_exacte_d_un_zero(100, risque=0.0)


def test_les_QUATRE_cas_de_taux_degenere_sont_tranches():
    """**Aucun des quatre ne doit repartir « non conclu »**, parce que le rendu leve dessus.

    Le cas des DEUX cotes au meme bout est celui qui a failli manquer : un comportement
    qu'aucun des deux joueurs ne manifeste jamais est parfaitement banal, son ecart vaut zero,
    et le laisser « non conclu » aurait fait tomber la generation du rapport entier.
    """
    un_seul = phase3_mesure.separer_un_taux_degenere(
        compte("X", 1368, 3814), compte("X", 0, 1967)
    )
    assert un_seul is not None and un_seul.disjoints and un_seul.cote == "ligne de base"

    meme_bout = phase3_mesure.separer_un_taux_degenere(
        compte("X", 0, 500), compte("X", 0, 700)
    )
    assert meme_bout is not None and not meme_bout.disjoints, meme_bout

    opposes = phase3_mesure.separer_un_taux_degenere(
        compte("X", 0, 500), compte("X", 700, 700)
    )
    assert opposes is not None and opposes.disjoints, opposes

    assert phase3_mesure.separer_un_taux_degenere(
        compte("X", 100, 500), compte("X", 200, 700)
    ) is None, "aucun cote degenere : cette regle ne doit pas s'appliquer"


def test_comparer_ne_rend_JAMAIS_une_ligne_non_conclue_sur_un_taux_degenere():
    """La parade du defaut A, du cote de `comparer` : les quatre cas sortent avec une regle.

    `separable is None` avec `exclu is None` est l'etat que le rendu refuse d'imprimer. Ce cas
    exige qu'aucune combinaison de taux degeneres ne l'atteigne -- c'est la garantie qui rend
    la levee du rendu tenable au lieu d'etre une bombe a retardement.
    """
    supports = [
        ((1368, 3814), (0, 1967)),     # un seul cote, un zero
        ((0, 1967), (1368, 3814)),     # un seul cote, l'autre sens
        ((0, 500), (0, 700)),          # les deux au meme bout
        ((500, 500), (700, 700)),      # les deux a cent
        ((0, 500), (700, 700)),        # bouts opposes
        ((3814, 3814), (1368, 3814)),  # un cent contre un taux ordinaire
    ]
    for (sa, na), (sb, nb) in supports:
        resultat = phase3_mesure.comparer(
            {"X": compte("X", sa, na, "occasions")},
            {"X": compte("X", sb, nb, "occasions")},
            6000, 6000, budget=6000,
        )[0]
        assert resultat.exclu is None
        assert resultat.separable is not None, (
            f"({sa}/{na}) contre ({sb}/{nb}) repart non conclue, regle {resultat.regle!r} : "
            f"le rendu du rapport leverait dessus"
        )
        assert resultat.regle == phase3_mesure.REGLE_BORNES_EXACTES, resultat.regle


def test_le_rendu_LEVE_sur_une_ligne_qu_aucune_regle_n_a_tranchee():
    """**La parade du defaut A, du cote du rendu.** « Non separable a ce budget » est une
    conclusion : rien ne la publie sans l'avoir calculee.

    Le cas fabrique l'etat interdit a la main -- il n'est plus atteignable par `comparer`, et
    c'est justement ce qu'on veut verifier ailleurs -- et exige que le rendu tombe dessus au
    lieu de lui donner un verdict par defaut.
    """
    from mesure import rapport_phase3

    non_conclue = phase3_mesure.Comparaison(
        nom="B4-invente",
        agent=compte("B4-invente", 1368, 3814, "occasions"),
        base=compte("B4-invente", 0, 1967, "occasions"),
        ecart=0.3587,
        detectable=None,
        separable=None,
        regle=phase3_mesure.REGLE_AUCUNE,
        borne_exacte=None,
        parties_requises=None,
        exclu=None,
    )
    with pytest.raises(ValueError, match="aucune regle n'a tranche"):
        rapport_phase3.section_comportements([], [non_conclue], 6000)


def _zeros_sans_verdict_calcule(texte: str) -> list[str]:
    """Les lignes a zero absolu du tableau du paragraphe 5 dont le verdict n'a pas ete calcule.

    **Le tableau du paragraphe 5 seul**, reconnu a ses six colonnes. Le paragraphe 6 reprend
    les memes compteurs sur quatre colonnes et sans verdict de separabilite : les y chercher
    accuse a cote, et une parade qui accuse a cote finit par etre desactivee.
    """
    fautives: list[str] = []
    for ligne in texte.splitlines():
        if not ligne.startswith("| `B") or " 0.00 % (0/" not in ligne:
            continue
        if len(ligne.split("|")) != 8:
            continue
        nom = ligne.split("|")[1].strip()
        if "non separable" in ligne:
            fautives.append(nom)
        elif "bornes exactes" not in ligne:
            fautives.append(nom + " (verdict sans regle nommee)")
    return fautives


def test_la_parade_du_rapport_MORD_sur_la_ligne_EXACTE_que_le_tour_2_publiait():
    """Une parade qu'on n'a jamais vue tomber ne garde rien.

    Le support est la ligne telle qu'elle etait dans `mesure/resultats/phase3.md` avant cette
    correction, recopiee au caractere pres -- pas une imitation.
    """
    du_tour_2 = (
        "| `B4-contre-nature` | 35.87 % (1368/3814) | 0.00 % (0/1967) | +35.87 pt | - | "
        "non separable a ce budget |"
    )
    assert _zeros_sans_verdict_calcule(du_tour_2) == ["`B4-contre-nature`"]

    corrigee = (
        "| `B4-contre-nature` | 35.87 % (1368/3814) | 0.00 % (0/1967) | +35.87 pt | - | "
        "**separable** -- par bornes exactes : le zero de la ligne de base a pour borne haute "
        "a 99 % **0.2338 %**, et l'agent est au-dela |"
    )
    assert _zeros_sans_verdict_calcule(corrigee) == []

    # Et le tableau du paragraphe 6, qui ne conclut rien : la parade ne doit pas l'accuser.
    du_paragraphe_6 = (
        "| `B4-contre-nature` | 35.87 % (1368/3814) | 0.00 % (0/1967) | "
        "desaccord avec l'evaluation myope |"
    )
    assert _zeros_sans_verdict_calcule(du_paragraphe_6) == []


def test_le_RAPPORT_PUBLIE_ne_declare_aucune_ligne_a_zero_NON_SEPARABLE():
    """**La parade du defaut A, du cote du document.** Le tableau et le texte doivent dire la
    meme chose.

    Le tour 2 publiait `B4-contre-nature` et `B4-meurtre-couteux` « non separable a ce
    budget », avec un tiret a la place du detectable, dans un rapport dont le paragraphe 6
    argumentait une demi-page sur ce que le meme ecart etablit. Ce cas relit le fichier livre
    -- pas la fonction qui le produit -- et exige que toute ligne portant un zero absolu y
    porte un verdict **calcule**.
    """
    rapport = Path("mesure/resultats/phase3.md")
    if not rapport.exists():  # pragma: no cover - le rapport est dans le depot
        pytest.skip("le rapport publie n'est pas la")
    fautives = _zeros_sans_verdict_calcule(rapport.read_text(encoding="utf-8"))
    assert not fautives, (
        f"le rapport publie conclut sur des lignes a zero absolu sans les avoir calculees : "
        f"{fautives}. « Non separable a ce budget » est une conclusion."
    )


def test_les_comptes_de_ce_fichier_sont_CEUX_DU_RAPPORT_PUBLIE():
    """La parade du defaut B : **les entrees du cas ci-dessus sont relues dans le rapport.**

    Un cas peut mentir sur son assertion -- la phase 2 l'a paye -- ou sur son **entree**, et le
    tour 2 l'a paye. Contre le second, une assertion soigneuse ne sert a rien : il faut aller
    rechercher les chiffres a leur source. Ce cas ouvre `mesure/resultats/phase3.md`, y lit les
    cinq lignes, et exige qu'elles soient celles que le cas precedent transcrit.

    Il tombe si quelqu'un retouche un compte pour faire passer un cas, dans un sens ou dans
    l'autre : la source ne se retouche pas depuis un fichier de tests.
    """
    rapport = Path("mesure/resultats/phase3.md")
    if not rapport.exists():  # pragma: no cover - le rapport est dans le depot
        pytest.skip("le rapport publie n'est pas la")
    texte = rapport.read_text(encoding="utf-8")
    attendus = {
        "B4-strict": ((391, 3814), (622, 1967)),
        "B4-departage": ((2055, 3814), (1345, 1967)),
        "B4-contre-nature": ((1368, 3814), (0, 1967)),
        "B4-meurtre-couteux": ((298, 8131), (0, 10382)),
        "B5-renfort": ((2270, 12454), (1746, 13159)),
    }
    for nom, ((sa, na), (sb, nb)) in attendus.items():
        motif = re.compile(
            r"\| `" + re.escape(nom) + r"` \| [\d.]+ % \((\d+)/(\d+)\) \| "
            r"[\d.]+ % \((\d+)/(\d+)\) \|"
        )
        trouve = motif.search(texte)
        assert trouve is not None, f"{nom} : introuvable dans le rapport publie"
        lus = tuple(int(g) for g in trouve.groups())
        assert lus == (sa, na, sb, nb), (
            f"{nom} : le rapport publie {lus}, le cas de ce fichier transcrit "
            f"{(sa, na, sb, nb)}. **Corrige le cas, pas le rapport.**"
        )


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
    meme critere qui divergeraient rendraient le tableau incoherent avec lui-meme.

    **Le cas compte ses deux branches et exige qu'elles soient toutes deux visitees.** Sans ce
    decompte, un balayage qui ne produirait que des lignes separables -- ou que des `continue`
    -- passerait au vert sans avoir eprouve l'equivalence. C'est la faiblesse que l'audit du
    tour 2 a trouvee ailleurs dans ce fichier, sous une forme plus grave : un cas dont les
    donnees decident du contenu, et qui ne verifie pas ce qu'elles ont decide.
    """
    separables, non_separables = 0, 0
    # **Le balayage du tour 2 allait de 2900 a 3100 par pas de 20, et il ne visitait QUE la
    # branche non separable** : le detectable a 6 000 contre 6 000 vaut environ 3 points, et
    # aucun ecart de ce balayage ne l'atteignait. Le cas etait vert sans avoir jamais compare
    # les deux ecritures du critere sur une ligne separable. Trouve en ajoutant le decompte
    # ci-dessous, qui est tombe du premier coup.
    for succes_base in range(2700, 3301, 50):
        resultat = phase3_mesure.comparer(
            {"X": compte("X", 3000, 6000)},
            {"X": compte("X", succes_base, 6000)},
            6000, 6000, budget=6000,
        )[0]
        if resultat.ecart == 0 or resultat.exclu is not None:
            continue
        assert resultat.regle == phase3_mesure.REGLE_DETECTABLE, resultat.regle
        if resultat.separable:
            separables += 1
            assert resultat.parties_requises is None
        else:
            non_separables += 1
            assert resultat.parties_requises is not None
            assert resultat.parties_requises > 6000, (succes_base, resultat.parties_requises)
    assert separables > 0 and non_separables > 0, (
        f"le balayage n'a visite qu'une des deux branches -- {separables} separables, "
        f"{non_separables} non separables : il ne compare plus les deux ecritures du critere"
    )


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

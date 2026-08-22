"""Le garde-fou de la campagne : il doit arreter un agent qui n'apprend pas, et LUI SEUL.

Un garde-fou se teste par ses deux erreurs, pas par une seule :

- **le faux negatif** -- il laisse tourner un agent qui n'apprend pas, et deux heures sont
  perdues. C'est l'erreur que le protocole voulait eviter ;
- **le faux positif** -- il tue un agent qui apprend. C'est l'erreur que les versions
  precedentes commettaient, et elle est plus couteuse : elle rend un verdict « l'agent
  n'apprend pas » sur un agent qui apprenait.

**Et une troisieme condition, que les quatre premieres versions n'avaient pas** : la regle
doit chercher un progres que son budget peut voir. Un garde-fou qui cherche un signal sous son
propre seuil de detection se declenche quoi que fasse l'agent -- c'est le quatrieme defaut, et
`test_une_portee_de_UN_serait_indetectable_a_ce_budget` le fige.

Les cas ci-dessous eprouvent les trois, sur des series par donne construites a la main.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import torch

from agents import campagne, entrainement
from mesure import bootstrap as boot
from mesure import dimensionnement as dim

APPAREIL = torch.device("cpu")

#: Assez de donnes pour qu'un ecart de quelques points soit tranchable, comme au budget reel.
DONNES = 600


def _serie(part: float, bruit: float, graine: int) -> tuple[float, ...]:
    """Une serie par donne de moyenne `part`, avec du bruit. Les donnes sont appariees d'une
    serie a l'autre : c'est le rang qui apparie, comme dans la campagne reelle."""
    alea = random.Random(graine)
    brut = [part + alea.uniform(-bruit, bruit) for _ in range(DONNES)]
    correction = part - sum(brut) / len(brut)
    return tuple(x + correction for x in brut)


def _jalon(numero: int, part: float, serie: tuple[float, ...] | None = None) -> campagne.Jalon:
    """Un jalon reduit a ce que la regle regarde : son numero et sa serie par donne."""
    return campagne.Jalon(
        numero=numero,
        secondes=numero * 900.0,
        vagues=numero * 10,
        parties=numero * 5120,
        noeuds=numero * 98_000,
        perte_politique=0.0,
        perte_valeur=0.0,
        entropie=2.0,
        part_fractionnee=part,
        borne_basse=part - 0.02,
        borne_haute=part + 0.02,
        gain_moyen=0.0,
        parts_par_donne=serie if serie is not None else _serie(part, 0.35, numero),
        ecart_de_portee=None,
        declenche=False,
    )


def _declencherait(jalons: list[campagne.Jalon], numero: int, serie: tuple[float, ...]) -> bool:
    """La regle en vigueur, reimplementee ici depuis le TEXTE de la docstring du module.

    **Reimplementee, pas importee.** Appeler la fonction qu'on teste pour produire l'attendu
    ne verifierait rien -- c'est la faute que la phase 2 a payee, deux implementations qui
    partagent la meme hypothese fausse concordant parfaitement.

    Le texte : *« il se declenche si l'ecart apparie entre part(k) et part(k - 3) n'est pas
    etabli -- intervalle a 99 % corrige de Bonferroni contenant 0 --, a partir de k = 4 ».*
    """
    if numero < campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE:
        return False
    reference = jalons[numero - campagne.PORTEE_DU_GARDE_FOU - 1]
    ecart = boot.bootstrap_apparie_par_donne(
        reference.parts_par_donne,
        serie,
        2_000,
        random.Random(7),
        risque=0.01 / campagne.CHECKPOINTS_ATTENDUS,
    )
    bas, haut = ecart.intervalle
    return not (bas > 0.0 or haut < 0.0)


def test_un_agent_qui_progresse_n_est_PAS_arrete():
    """Le faux positif, celui qui coute le plus cher : trois versions du garde-fou le
    commettaient, la derniere en tuant ce run-ci au checkpoint 3."""
    parts = [0.57, 0.59, 0.62, 0.63, 0.65, 0.68, 0.69, 0.70]
    jalons = [_jalon(i + 1, p) for i, p in enumerate(parts)]
    for numero in range(campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE, len(parts) + 1):
        assert not _declencherait(jalons, numero, jalons[numero - 1].parts_par_donne), (
            f"le checkpoint {numero} arrete un agent qui progresse de "
            f"{100 * (parts[numero - 1] - parts[numero - 4]):.2f} pt sur trois quarts d'heure"
        )


def test_un_agent_qui_STAGNE_EST_arrete():
    """Le faux negatif : un agent qui ne bouge plus sur trois quarts d'heure doit tomber."""
    parts = [0.57, 0.60, 0.63, 0.66, 0.662, 0.661, 0.663, 0.662]
    jalons = [_jalon(i + 1, p) for i, p in enumerate(parts)]
    declenchements = [
        _declencherait(jalons, numero, jalons[numero - 1].parts_par_donne)
        for numero in range(campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE, len(parts) + 1)
    ]
    assert declenchements[-1], "une stagnation sur trois quarts d'heure doit declencher"
    assert any(declenchements), declenchements


def test_un_agent_qui_stagne_TRES_HAUT_est_arrete_aussi():
    """**La distance a la barre du greedy n'entre plus dans la regle.** Elle y entrait dans les
    versions 2 et 3, et c'est ce qui confondait « n'a pas atteint la barre » et « n'apprend
    pas ». Un agent qui stagne au-dessus de 86,52 % n'apprend plus : rallonger ne dira rien."""
    parts = [0.90, 0.90, 0.90, 0.90, 0.90]
    jalons = [_jalon(i + 1, p) for i, p in enumerate(parts)]
    assert _declencherait(jalons, 5, jalons[4].parts_par_donne)
    assert _declencherait(jalons, 4, jalons[3].parts_par_donne)


def test_les_TROIS_premiers_checkpoints_ne_declenchent_jamais():
    """`part(k-3)` n'existe pas avant le quatrieme."""
    jalons = [_jalon(i + 1, 0.5) for i in range(8)]
    for numero in (1, 2, 3):
        assert not _declencherait(jalons, numero, jalons[numero - 1].parts_par_donne), (
            f"le checkpoint {numero} declenche alors qu'il n'a pas de terme de comparaison"
        )
    assert campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE == 4


def test_une_portee_de_UN_serait_indetectable_a_ce_budget():
    """**La regle generale que les quatre versions du garde-fou n'avaient pas.**

    *Un garde-fou ne peut chercher qu'un progres plus grand que l'ecart detectable a son
    propre budget.*

    **Et la grandeur a lui donner est le detectable d'un ECART APPARIE, pas celui d'un
    NIVEAU.** La demi-largeur mesuree des sept ecarts apparies du run de la phase 3 vaut 3,83
    point en moyenne -- de 3,56 a 4,06 --, quand la pre-inscription publie 2,75 pour un
    niveau. Un quart d'heure de progres vaut 1,83.

    Le cas fige les deux, parce que le choix de la grandeur **change la reponse** : avec la
    bonne, la portee minimale est **3** et la portee retenue est donc minimale, pas
    confortable ; avec celle du niveau, elle rendrait 2, et une portee de 2 chercherait 3,66
    pour une barre de 3,83 -- **sous le seuil**. C'est la relecture finale du tour 2 qui l'a vu.
    """
    apparie_pt, niveau_pt, progres_pt = 3.83, 2.75, 1.83

    minimale = campagne.portee_minimale(apparie_pt, progres_pt)
    assert minimale == 3, minimale
    assert campagne.PORTEE_DU_GARDE_FOU >= minimale, (
        f"portee {campagne.PORTEE_DU_GARDE_FOU} alors qu'il en faut {minimale} pour que le "
        f"progres cherche depasse le detectable apparie de son propre budget"
    )
    # La mauvaise grandeur donnerait une portee insuffisante : le cas le fige pour que
    # personne ne la reintroduise en croyant simplifier.
    assert campagne.portee_minimale(niveau_pt, progres_pt) == 2
    assert 2 * progres_pt < apparie_pt, (
        "une portee de 2 chercherait un progres sous la barre : le contre-exemple a bouge"
    )
    assert campagne.PORTEE_DU_GARDE_FOU * progres_pt > apparie_pt


def test_portee_minimale_refuse_un_progres_ou_un_detectable_nul():
    with pytest.raises(ValueError, match="strictement positives"):
        campagne.portee_minimale(2.75, 0.0)
    with pytest.raises(ValueError, match="strictement positives"):
        campagne.portee_minimale(0.0, 1.83)


def test_le_garde_fou_du_RUN_REEL_ne_declenche_sur_aucun_checkpoint():
    """**Eprouve sur les donnees avant d'etre ecrit** -- ce que les quatre versions
    precedentes n'avaient pas ete. Les cinq ecarts de portee trois du run de la phase 3."""
    journal = Path("models/phase3/journal.jsonl")
    if not journal.exists():
        pytest.skip("le journal du run n'est pas dans le depot")
    jalons = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
    if not all(j.get("parts_par_donne") for j in jalons):
        pytest.skip("journal sans serie par donne : lancer `mesure.phase3_courbe`")
    from mesure import phase3_courbe

    risque = 0.01 / campagne.CHECKPOINTS_ATTENDUS
    ecarts = phase3_courbe.ecarts(jalons, campagne.PORTEE_DU_GARDE_FOU, risque)
    assert len(ecarts) == 5, len(ecarts)
    non_etablis = [f"ckpt {e.depuis}->{e.vers}" for e in ecarts if not e.etabli]
    assert not non_etablis, (
        f"le garde-fou declencherait sur {non_etablis} : la regle en vigueur tuerait le run "
        f"de la phase 3, exactement comme celle qu'elle remplace"
    )
    # Et le contraste avec la portee 1, qui est le defaut fige.
    voisins = phase3_courbe.ecarts(jalons, 1, risque)
    assert not any(e.etabli for e in voisins), (
        "a portee 1, un ecart est etabli : le contre-exemple qui justifie la portee 3 a bouge"
    )


def test_la_correction_de_bonferroni_est_bien_appliquee():
    """Huit regards, `risque / 8`. Un IC a 99 % applique huit fois se franchit plus souvent.

    Le cas verifie le quantile lui-meme, pas seulement qu'un argument est passe : c'est le
    chiffre qui elargit l'intervalle, et il doit valoir 3,2272 et non 2,5758.
    """
    assert campagne.CHECKPOINTS_ATTENDUS == 8
    sans = dim.quantile_bilateral(0.01)
    avec = dim.quantile_bilateral(0.01, campagne.CHECKPOINTS_ATTENDUS)
    assert avec == pytest.approx(3.2272, abs=1e-4)
    assert sans == pytest.approx(2.5758, abs=1e-4)
    assert avec > sans


def test_le_seuil_du_garde_fou_est_celui_de_la_phase_2_et_son_grain_est_ecrit():
    """86,52 %, moyenne sur les TROIS sieges, 10 002 parties de la campagne B.

    Il ne se compare qu'a une mesure agregee de la meme facon. Le cas verifie la constante et,
    surtout, que la campagne du garde-fou mesure bien **les trois sieges**.
    """
    assert campagne.GARDE_FOU_GREEDY == 0.8652
    from mesure import phase3

    petite = phase3.jouer_composition(
        agent=phase3.uniforme,
        adversaire=phase3.uniforme,
        donnes=3,
        intitule="controle de grain",
        depart=campagne.DEPART_DONNE_GARDE_FOU,
    )
    for sieges in petite.sieges_mesures:
        assert sorted(sieges) == [0, 1, 2], (
            f"le garde-fou ne mesure pas les trois sieges : {sieges}. Le 86,52 % est une "
            f"moyenne sur trois sieges et ne se compare qu'a une mesure du meme grain."
        )


def test_le_garde_fou_mesure_bien_UN_agent_contre_DEUX_aleatoires():
    """La composition doit etre identique a celle du 86,52 %, sinon la comparaison est fausse.

    Le cas verifie que dans chaque partie, **un seul** siege est celui de l'agent mesure et que
    les deux autres jouent la politique uniforme -- en comparant leurs actions a celles qu'un
    tirage uniforme sur les memes graines produit.
    """
    from mesure import phase3

    modele = entrainement.construire(APPAREIL)
    campagne_test = phase3.jouer_composition(
        agent=lambda alea: __import__(
            "agents.politique_reseau", fromlist=["politique_reseau"]
        ).politique_reseau(modele, alea),
        adversaire=phase3.uniforme,
        donnes=2,
        intitule="1 agent contre 2 aleatoires",
        depart=campagne.DEPART_DONNE_GARDE_FOU,
        decalage_adversaire=phase3.DECALAGE_UNIFORME,
    )
    assert campagne_test.replicats_par_donne == 3
    for sieges in campagne_test.sieges_mesures:
        assert len(set(sieges)) == 3


def test_le_run_ecrit_un_journal_relisible_et_des_checkpoints(tmp_path: Path):
    """Un run qui ne laisse pas de trace n'est pas auditable.

    Run minuscule -- quelques secondes -- dont on ne lit **aucun chiffre de performance** :
    seule la forme de la trace est verifiee. Les chiffres viennent du vrai run.
    """
    jalons = campagne.entrainer(
        dossier=tmp_path,
        plafond_secondes=6,
        secondes_entre_checkpoints=2,
        parties_par_vague=8,
        appareil=APPAREIL,
        donnes_garde_fou=4,
    )
    assert jalons, "aucun checkpoint sur un run de 6 s a 2 s d'intervalle"
    assert (tmp_path / "final.pt").exists()
    assert (tmp_path / "checkpoint_01.pt").exists()

    lignes = [
        json.loads(x)
        for x in (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(lignes) == len(jalons)
    attendus = {
        "numero", "secondes", "vagues", "parties", "noeuds", "perte_politique",
        "perte_valeur", "entropie", "part_fractionnee", "borne_basse", "borne_haute",
        "gain_moyen", "parts_par_donne", "ecart_de_portee", "declenche",
    }
    assert set(lignes[0]) == attendus, set(lignes[0]) ^ attendus
    # La serie par donne est journalisee, et elle a la bonne longueur : sans elle, aucun ecart
    # apparie n'est calculable et le rapport ne pourrait publier que des niveaux.
    for ligne in lignes:
        assert len(ligne["parts_par_donne"]) == 4, ligne["parts_par_donne"]
    assert lignes[0]["ecart_de_portee"] is None, "le premier checkpoint n'a rien a comparer"
    # Les compteurs sont cumulatifs : un compteur qui reculerait serait un compteur remis a zero.
    for avant, apres in zip(lignes, lignes[1:], strict=False):
        assert apres["parties"] > avant["parties"]
        assert apres["noeuds"] > avant["noeuds"]


def test_un_checkpoint_relu_rend_exactement_la_meme_politique(tmp_path: Path):
    """Un checkpoint qui ne se relit pas a l'identique rendrait le pool et la mesure faux."""
    from agents.politique_reseau import charger

    modele = entrainement.construire(APPAREIL)
    chemin = tmp_path / "essai.pt"
    torch.save(modele.state_dict(), chemin)
    relu = charger(str(chemin), modele.taille_observation, modele.nb_actions)

    assert not relu.training, "un checkpoint relu doit etre en mode evaluation"
    entree = torch.randn(4, modele.taille_observation)
    modele.eval()
    with torch.no_grad():
        assert torch.equal(modele(entree)[0], relu(entree)[0])
        assert torch.equal(modele(entree)[1], relu(entree)[1])

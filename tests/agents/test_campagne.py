"""Le garde-fou de la campagne : il doit arreter un agent qui n'apprend pas, et LUI SEUL.

Un garde-fou se teste par ses deux erreurs, pas par une seule :

- **le faux negatif** -- il laisse tourner un agent qui n'apprend pas, et deux heures sont
  perdues. C'est l'erreur que le protocole voulait eviter ;
- **le faux positif** -- il tue un agent qui apprend mais n'a pas encore atteint la barre.
  C'est l'erreur que la premiere version de ce module commettait, et elle est plus couteuse :
  elle rend un verdict « l'agent n'apprend pas » sur un agent qui apprenait.

Les cas ci-dessous eprouvent les deux, sur des suites de jalons construites a la main.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch

from agents import campagne, entrainement
from mesure import dimensionnement as dim

APPAREIL = torch.device("cpu")


def _jalon(numero: int, part: float, haute: float | None = None) -> campagne.Jalon:
    """Un jalon reduit a ce que la regle regarde : son numero, sa part, sa borne haute."""
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
        borne_haute=part + 0.02 if haute is None else haute,
        gain_moyen=0.0,
    declenche=False,
    )


def _declencherait(jalons: list[campagne.Jalon], numero: int, part: float, haute: float) -> bool:
    """La regle en vigueur, reimplementee ici depuis le TEXTE de la docstring du module.

    **Reimplementee, pas importee.** Appeler la fonction qu'on teste pour produire l'attendu
    ne verifierait rien -- c'est la faute que la phase 2 a payee, deux implementations qui
    partagent la meme hypothese fausse concordant parfaitement.
    """
    if numero < campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE:
        return False
    precedent = jalons[numero - campagne.PREMIER_CHECKPOINT_QUI_DECLENCHE]
    stagne = part <= precedent.part_fractionnee
    loin = haute < campagne.GARDE_FOU_GREEDY
    return stagne and loin


def test_un_agent_qui_progresse_loin_de_la_barre_n_est_PAS_arrete():
    """Le faux positif que la premiere version commettait, fige ici.

    Part fractionnee 38 % -> 42 % -> 46 % -> 50 % : tres loin des 86,52 %, et en progres
    constant. La premiere version arretait au 3e checkpoint parce que la borne haute restait
    sous la barre. **MESURE sur un run d'essai** : l'entropie tombait de 2,089 a 1,646 pendant
    ce temps -- l'agent apprenait.
    """
    jalons: list[campagne.Jalon] = []
    for numero, part in enumerate([0.38, 0.42, 0.46, 0.50], start=1):
        assert not _declencherait(jalons, numero, part, part + 0.02), (
            f"checkpoint {numero} : un agent qui progresse a {part:.0%} est arrete"
        )
        jalons.append(_jalon(numero, part))


def test_un_agent_qui_STAGNE_loin_de_la_barre_EST_arrete():
    """Le vrai positif : aucun progres sur une demi-heure, et tres loin de la barre."""
    jalons: list[campagne.Jalon] = []
    parts = [0.35, 0.34, 0.35, 0.34]
    declenchements = []
    for numero, part in enumerate(parts, start=1):
        declenchements.append(_declencherait(jalons, numero, part, part + 0.02))
        jalons.append(_jalon(numero, part))
    assert declenchements == [False, False, True, True], declenchements


def test_un_agent_qui_stagne_AU_DESSUS_de_la_barre_n_est_pas_arrete():
    """Stagner n'est un symptome que **loin** de la barre. Au-dessus, c'est une reussite.

    Un agent a 90 % qui n'avance plus a atteint le niveau du greedy contre deux aleatoires :
    l'arreter dirait « il n'apprend pas » d'un agent qui a franchi le critere terminal.
    """
    jalons: list[campagne.Jalon] = []
    for numero, part in enumerate([0.90, 0.89, 0.90, 0.89], start=1):
        assert not _declencherait(jalons, numero, part, part + 0.02)
        jalons.append(_jalon(numero, part))


def test_les_deux_premiers_checkpoints_ne_declenchent_jamais():
    """`part(k-2)` n'existe pas avant le troisieme, et un reseau quasi uniforme n'a rien a dire."""
    jalons: list[campagne.Jalon] = []
    for numero, part in enumerate([0.05, 0.02], start=1):
        assert not _declencherait(jalons, numero, part, part + 0.001), (
            f"le checkpoint {numero} declenche alors qu'il n'a pas de terme de comparaison"
        )
        jalons.append(_jalon(numero, part))


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
        "gain_moyen", "declenche",
    }
    assert set(lignes[0]) == attendus, set(lignes[0]) ^ attendus
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

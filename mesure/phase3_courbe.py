"""La courbe d'apprentissage, et l'INTERVALLE DE SES ECARTS.

Ce module existe parce que le premier tour de la phase 3 a publie **huit intervalles sur huit
niveaux et aucun sur les sept ecarts**, puis a conclu « croissance monotone sans exception, et
il progressait encore au dernier ». L'audit a montre que la phrase ne tenait sur aucun ecart :
les sept pas valent +2,19 a +0,86 point pour un detectable que la pre-inscription fixe
elle-meme a **2,75**, et une remesure sur les MEMES donnes avec un autre aleatoire de tirage
porte deux inversions et un dernier pas **negatif**.

**La monotonie n'etait pas une propriete de l'agent, c'etait une propriete de son tirage.**

La regle qui en sort est desormais au paragraphe 0.2 du protocole : *une courbe d'apprentissage
se publie avec l'intervalle de ses ECARTS, pas seulement de ses niveaux.* C'est un ecart qui
decide -- « il progresse encore » --, jamais un niveau.

Un ecart apparie ne coute pas une partie de plus
--------------------------------------------------
Les donnes du garde-fou sont **les memes a chaque checkpoint** -- `DEPART_DONNE_GARDE_FOU`,
`DONNES_GARDE_FOU` --, ce que la pre-inscription avait prevu explicitement « pour que deux
checkpoints se comparent sur les memes donnes ». La matiere de l'ecart apparie etait donc deja
jouee : il ne manquait que de la garder.

Ce que ce module ne fait PAS : rejouer une campagne
-----------------------------------------------------
Le run de la phase 3 a ete journalise avant que `Jalon.parts_par_donne` n'existe. `completer`
**rejoue** l'evaluation du garde-fou de chaque checkpoint pour retrouver la serie par donne --
et **exige que les quatre nombres deja journalises soient reproduits a l'identique**, sinon
elle leve. Ce n'est donc pas une nouvelle mesure : c'est la meme, dont on garde davantage. Si
un seul bit avait bouge, aucun ecart ne serait publie.

Les runs suivants n'en ont pas besoin : `agents.campagne` journalise la serie directement.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mesure import bootstrap as boot
from mesure import phase3

#: Les champs deja journalises que le rejeu doit reproduire **exactement**. Reproduire trois
#: nombres sur quatre laisserait passer le cas ou la serie par donne appartient a un autre run.
CHAMPS_A_REPRODUIRE: tuple[str, ...] = (
    "part_fractionnee",
    "borne_basse",
    "borne_haute",
    "gain_moyen",
)


@dataclass(frozen=True)
class Ecart:
    """L'ecart apparie entre deux checkpoints, avec ce qui permet de le lire.

    Attributes:
        depuis, vers: les numeros des deux checkpoints, `vers > depuis`.
        portee: `vers - depuis`, en checkpoints.
        moyenne: l'ecart moyen apparie, en part fractionnee.
        intervalle: son intervalle de percentiles, bootstrap **par donne**.
        etabli: l'intervalle exclut-il 0 ? **C'est la seule lecture licite** d'un ecart.
        progres_etabli: l'intervalle est-il **entierement au-dessus de 0** ? Recopie de
            `bootstrap.EcartApparie`, ou le predicat est defini une seule fois. Ce n'est pas
            `etabli` : un effondrement etabli est etabli et n'est pas un progres, et c'est la
            distinction dont le garde-fou depend.
    """

    depuis: int
    vers: int
    portee: int
    moyenne: float
    intervalle: tuple[float, float]
    etabli: bool
    progres_etabli: bool


@dataclass(frozen=True)
class RejeuDeCheckpoint:
    """Tout ce que le rejeu d'un checkpoint rend, **chaque champ sous son nom**.

    Ce type existe parce que la fonction ci-dessous rendait un `tuple[float, ...]` de cinq
    elements dont le cinquieme etait une **suite** de flottants, pas un flottant. L'annotation
    etait donc fausse, et le nom de la fonction ne promettait qu'un des cinq. Un appelant qui
    lisait la signature ne pouvait pas deviner l'ordre des quatre premiers -- et c'est
    exactement l'ordre dont depend la garde de reproduction bit a bit.

    Attributes:
        part_fractionnee: la part fractionnee du checkpoint.
        borne_basse: la borne basse de son intervalle.
        borne_haute: la borne haute de son intervalle.
        gain_moyen: le gain moyen.
        serie: la part fractionnee **donne par donne** -- la matiere de l'ecart apparie.
    """

    part_fractionnee: float
    borne_basse: float
    borne_haute: float
    gain_moyen: float
    serie: tuple[float, ...]


def serie_par_donne(chemin_checkpoint: Path, donnes: int) -> RejeuDeCheckpoint:
    """Rejoue l'evaluation du garde-fou d'un checkpoint et rend **tout** ce qu'elle produit.

    Passe par `agents.campagne.evaluer_le_garde_fou` plutot que de refaire la campagne ici :
    deux definitions de la meme composition finiraient par ne plus etre d'accord, et c'est la
    mesure qui aurait tort sans que rien ne le signale (paragraphe 2 des conventions).

    Le nom est garde parce qu'il dit ce qu'on vient chercher ; le type de retour dit ce qu'on
    obtient, et les deux ne se contredisent plus depuis que ce n'est plus un tuple anonyme.
    """
    from agents.campagne import evaluer_le_garde_fou
    from agents.politique_reseau import charger
    from courtisans.engine import Engine
    from courtisans.infoset import tenseur

    etat_zero = Engine(phase3.CONFIG).reset(0)
    modele = charger(
        str(chemin_checkpoint),
        taille_observation=len(tenseur(etat_zero, 0)),
        nb_actions=6 * 2 * (phase3.CONFIG.joueurs - 1),
    )
    part, (basse, haute), gain, serie = evaluer_le_garde_fou(modele, donnes)
    return RejeuDeCheckpoint(
        part_fractionnee=part,
        borne_basse=basse,
        borne_haute=haute,
        gain_moyen=gain,
        serie=tuple(serie),
    )


def completer(dossier: Path, donnes: int) -> list[dict]:
    """Relit le journal et y ajoute `parts_par_donne` la ou il manque. **Idempotente.**

    Raises:
        FileNotFoundError: si le journal ou l'un des checkpoints manque.
        ValueError: si le rejeu d'un checkpoint ne **reproduit pas exactement** les nombres
            deja journalises. C'est la garde qui distingue « garder davantage de la meme
            mesure » de « refaire une mesure » : sans elle, ce module pourrait publier des
            ecarts calcules sur des parties qui ne sont pas celles du run.
    """
    journal = dossier / "journal.jsonl"
    if not journal.exists():
        raise FileNotFoundError(f"{journal} : pas de journal, pas de courbe")
    jalons = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines() if x]
    if all("parts_par_donne" in jalon for jalon in jalons):
        return jalons

    for jalon in jalons:
        if "parts_par_donne" in jalon:
            continue
        chemin = dossier / f"checkpoint_{jalon['numero']:02d}.pt"
        if not chemin.exists():
            raise FileNotFoundError(
                f"{chemin} : la serie par donne du checkpoint {jalon['numero']} ne peut pas "
                f"etre rejouee sans lui, et elle ne s'invente pas"
            )
        rejeu = serie_par_donne(chemin, donnes)
        rejoue = {
            "part_fractionnee": rejeu.part_fractionnee,
            "borne_basse": rejeu.borne_basse,
            "borne_haute": rejeu.borne_haute,
            "gain_moyen": rejeu.gain_moyen,
        }
        ecarts = [
            f"{champ} : journalise {jalon[champ]!r}, rejoue {rejoue[champ]!r}"
            for champ in CHAMPS_A_REPRODUIRE
            if jalon[champ] != rejoue[champ]
        ]
        if ecarts:
            raise ValueError(
                f"le rejeu du checkpoint {jalon['numero']} ne reproduit pas le journal : "
                + " ; ".join(ecarts)
                + ". Ce n'est donc pas la meme mesure, et aucun ecart n'en sera publie."
            )
        jalon["parts_par_donne"] = list(rejeu.serie)

    journal.write_text(
        "".join(json.dumps(jalon, ensure_ascii=False) + "\n" for jalon in jalons),
        encoding="utf-8",
    )
    return jalons


def ecarts(jalons: Sequence[dict], portee: int, risque: float) -> list[Ecart]:
    """Les ecarts apparies de portee donnee, du premier possible au dernier.

    Args:
        portee: le nombre de checkpoints enjambes. `1` compare des voisins, `3` est la portee
            du garde-fou.
        risque: le risque de l'intervalle. Corrige de Bonferroni par l'appelant s'il y a lieu.

    Raises:
        ValueError: si un jalon n'a pas de serie par donne -- l'ecart n'est alors pas
            calculable, et le publier a partir des seuls niveaux serait la lecture fautive que
            ce module existe pour interdire. Egalement si `portee < 1`.
    """
    if portee < 1:
        raise ValueError(f"une portee vaut au moins 1 checkpoint, {portee} demandee")
    manquants = [j["numero"] for j in jalons if not j.get("parts_par_donne")]
    if manquants:
        raise ValueError(
            f"checkpoint(s) {manquants} sans serie par donne : un ecart apparie ne se "
            f"reconstruit pas a partir de deux niveaux. Appeler `completer` d'abord."
        )
    resultats: list[Ecart] = []
    for indice in range(portee, len(jalons)):
        avant, apres = jalons[indice - portee], jalons[indice]
        apparie = boot.bootstrap_apparie_par_donne(
            avant["parts_par_donne"],
            apres["parts_par_donne"],
            phase3.RECHANTILLONS,
            random.Random(phase3.graine_du_garde_fou(apres["numero"])),
            risque=risque,
        )
        resultats.append(
            Ecart(
                depuis=avant["numero"],
                vers=apres["numero"],
                portee=portee,
                moyenne=apparie.moyenne,
                intervalle=apparie.intervalle,
                etabli=apparie.etabli,
                progres_etabli=apparie.progres_etabli,
            )
        )
    return resultats


def ecart_des_extremes(jalons: Sequence[dict], risque: float) -> Ecart:
    """L'ecart apparie du premier au dernier checkpoint. **C'est lui qui etablit « il apprend ».**"""
    return ecarts(jalons, len(jalons) - 1, risque)[0]


__all__ = [
    "Ecart",
    "RejeuDeCheckpoint",
    "completer",
    "ecart_des_extremes",
    "ecarts",
    "serie_par_donne",
]

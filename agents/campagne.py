"""La campagne d'entrainement de la phase 3 : entrainer, jalonner, garder le garde-fou.

Ce module **orchestre**, il ne decide rien. Ce qu'il applique est pre-inscrit dans
`mesure/phase3_hypothese_et_instrument.md`, commite avant tout entrainement, et chaque
constante ci-dessous renvoie au paragraphe qui la fixe.

Le garde-fou, et pourquoi il est ici plutot que dans la boucle
---------------------------------------------------------------
Le protocole disait : « si apres 2 h d'entrainement l'agent n'a pas depasse 86,52 % ». **Ce
garde-fou ne pouvait rien arreter** : le plafond d'execution de la phase est lui aussi de 2 h,
donc il se declenchait quand le run etait deja fini. Corrige au protocole le 20/08/2026, et
repris ici sous sa forme en vigueur -- evaluation **a chaque checkpoint de 15 minutes**, contre
deux aleatoires, **agregee sur les trois sieges** comme le 86,52 % l'est.

Huit regards, et ce qu'on en fait
-----------------------------------
Deux heures a un checkpoint tous les quarts d'heure font **huit** evaluations. Huit regards
multiplient les occasions de faux arret, et l'IC est donc corrige de **Bonferroni** :
`risque / 8`, soit `z = 3,2272` au lieu de 2,5758.

**Un seuil terminal ne s'applique pas a un instant intermediaire, et c'est le defaut que ce
module a porte avant d'entrainer quoi que ce soit.**

Le 86,52 % du protocole est le critere de **fin de budget** : « si **apres 2 h** d'entrainement
l'agent n'a pas depasse... ». Une premiere version de ce module l'appliquait tel quel des le 3e
checkpoint -- 45 minutes -- en arretant des que la borne haute restait sous 86,52 %. Ca
confond deux choses tres differentes : **« l'agent n'a pas encore atteint la barre »** et
**« l'agent n'apprend pas »**.

MESURE sur un run d'essai de 2 minutes, 25 088 parties, trois checkpoints : l'entropie de la
politique tombe de **2,089 a 1,646** -- l'agent apprend, visiblement -- et la regle l'arretait
quand meme, parce que 86,52 % est le niveau du greedy et qu'il est loin. **Une regle qui tue un
apprenant sain n'est pas un garde-fou, c'est une panne.**

La regle en vigueur separe donc les deux criteres :

  - **arret anticipe**, possible des le 3e checkpoint, et il demande **deux conditions a la
    fois** : que la part fractionnee **stagne** -- `part(k) <= part(k-2)`, donc aucun progres
    sur une demi-heure -- **et** que l'agent soit **loin**, borne haute encore sous 86,52 %.
    Stagner loin de la barre est le symptome d'un agent qui n'apprend pas ; etre loin en
    progressant ne l'est pas ;
  - **critere terminal**, inchange et celui du protocole : a la fin des 2 h, la part
    fractionnee a-t-elle depasse **86,52 %** ? C'est ce qui se rapporte, quel que soit le
    chemin ;
  - les deux premiers checkpoints sont **rapportes mais ne declenchent jamais** : un reseau
    quasi uniforme n'a encore rien a dire, et `part(k-2)` n'existe pas avant le 3e.

Ce que le garde-fou n'est PAS
------------------------------
Ce n'est **pas un juge**. Depasser 86,52 % contre deux aleatoires ne dit **rien** sur le fait de
battre le greedy : le greedy y est deja. C'est un detecteur d'agent qui n'apprend pas, et rien
d'autre.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from torch import optim

from agents import entrainement
from agents.politique_reseau import politique_reseau
from agents.reseau import ReseauPolitiqueValeur
from mesure import bootstrap as boot
from mesure import dimensionnement as dim
from mesure import phase3

#: Paragraphe 8 : la part de victoire fractionnee du greedy contre deux aleatoires, **moyenne
#: sur les trois sieges**, agregee sur les 10 002 parties de la campagne B de la phase 2. Elle
#: ne se compare qu'a une mesure agregee de la meme facon.
GARDE_FOU_GREEDY = 0.8652

#: Paragraphe 8.1 : 600 donnes x 3 sieges = 1 800 parties par checkpoint, ecart detectable
#: 2,75 pt en iid. Seeds `40000+`, **les memes a chaque checkpoint**, pour que deux checkpoints
#: se comparent sur les memes donnes.
DONNES_GARDE_FOU = 600
DEPART_DONNE_GARDE_FOU = 40_000

#: Huit regards en 2 h. Bonferroni : `risque / 8`.
CHECKPOINTS_ATTENDUS = 8

#: Le premier checkpoint qui peut declencher l'arret, et il vaut **3** pour deux raisons qui
#: coincident. La condition de stagnation compare `part(k)` a `part(k-2)`, qui n'existe pas
#: avant le troisieme. Et un reseau encore quasi uniforme n'a rien a dire : un ecart de deux
#: intervalles, soit une demi-heure, est ce qui separe du bruit d'une absence reelle de progres.
PREMIER_CHECKPOINT_QUI_DECLENCHE = 3

#: Paragraphe 3 de la phase 3 du protocole : plafond de 2 h, checkpoint tous les quarts d'heure.
SECONDES_ENTRE_CHECKPOINTS = 15 * 60
PLAFOND_SECONDES = 2 * 60 * 60

#: Vagues de 512 parties. **MESURE** : 229 parties/s sur le CPU de la machine contre 204 sur le
#: GPU -- le reseau est trop petit pour que le GPU paie son transfert. Trois passes, etendue
#: 2,04-2,39 s par iteration sur CPU.
PARTIES_PAR_VAGUE = 512


@dataclass(frozen=True)
class Jalon:
    """Ce qu'un checkpoint a produit. **Tout y porte son echantillon.**

    Attributes:
        numero: le rang du checkpoint, a partir de 1.
        secondes: temps mural depuis le debut du run.
        vagues: nombre de vagues jouees.
        parties: nombre de parties d'entrainement jouees.
        noeuds: nombre de nœuds collectes.
        perte_politique, perte_valeur, entropie: moyennes de la derniere mise a jour.
        part_fractionnee: part de victoire fractionnee contre deux aleatoires, **agregee sur
            les trois sieges**.
        borne_basse, borne_haute: IC de cette part, **corrige de Bonferroni pour 8 regards**.
        gain_moyen: gain moyen dans la meme composition, rapporte a cote.
        declenche: vrai si le garde-fou impose l'arret a ce checkpoint.
    """

    numero: int
    secondes: float
    vagues: int
    parties: int
    noeuds: int
    perte_politique: float
    perte_valeur: float
    entropie: float
    part_fractionnee: float
    borne_basse: float
    borne_haute: float
    gain_moyen: float
    declenche: bool


def evaluer_le_garde_fou(
    modele: ReseauPolitiqueValeur, donnes: int = DONNES_GARDE_FOU
) -> tuple[float, tuple[float, float], float]:
    """L'agent contre **deux aleatoires**, sieges permutes, agrege sur les trois.

    Rend `(part fractionnee, IC corrige de Bonferroni, gain moyen)`.

    **La composition est identique a celle du 86,52 %** -- un agent contre deux aleatoires --
    et seul l'agent au siege mesure change. C'est ce qui rend la comparaison licite, et c'est
    la seule raison pour laquelle elle l'est.

    L'IC est calcule au risque `0,01 / 8` : huit checkpoints sont huit regards, et un IC a 99 %
    applique huit fois se franchit a tort bien plus d'une fois sur cent.
    """
    campagne = phase3.jouer_composition(
        agent=lambda alea: politique_reseau(modele, alea),
        adversaire=phase3.uniforme,
        donnes=donnes,
        intitule="1 agent entraine contre 2 aleatoires (garde-fou)",
        depart=DEPART_DONNE_GARDE_FOU,
        decalage_adversaire=phase3.DECALAGE_UNIFORME,
    )
    risque_corrige = 0.01 / CHECKPOINTS_ATTENDUS
    part = boot.bootstrap_par_donne(
        campagne.parts_fractionnees_par_donne(),
        phase3.RECHANTILLONS,
        random.Random(phase3.GRAINE_BOOTSTRAP + 2),
        risque=risque_corrige,
    )
    gain = boot.bootstrap_par_donne(
        campagne.gains_par_donne(),
        phase3.RECHANTILLONS,
        random.Random(phase3.GRAINE_BOOTSTRAP + 3),
        risque=risque_corrige,
    )
    return part.moyenne, part.intervalle, gain.moyenne


def _sauver(modele: ReseauPolitiqueValeur, chemin: Path) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    torch.save(modele.state_dict(), chemin)


def entrainer(
    dossier: Path,
    plafond_secondes: float = PLAFOND_SECONDES,
    secondes_entre_checkpoints: float = SECONDES_ENTRE_CHECKPOINTS,
    parties_par_vague: int = PARTIES_PAR_VAGUE,
    appareil: torch.device | None = None,
    donnes_garde_fou: int = DONNES_GARDE_FOU,
) -> list[Jalon]:
    """Le run complet. Rend la suite des jalons, et ecrit tout dans `dossier`.

    **Le CPU est le defaut**, et c'est une mesure et non un gout : 229 parties/s sur CPU contre
    204 sur GPU, sur trois passes. Le reseau est trop petit pour que le transfert vers le GPU
    soit rentable ; le moteur stdlib pese 57 a 69 % du temps d'une vague, ce qui etait un
    SUPPOSE et qui est desormais MESURE.
    """
    appareil = appareil or torch.device("cpu")
    modele = entrainement.construire(appareil)
    optimiseur = optim.Adam(modele.parameters(), lr=entrainement.TAUX_APPRENTISSAGE)
    pool: list[ReseauPolitiqueValeur] = []

    dossier.mkdir(parents=True, exist_ok=True)
    journal = dossier / "journal.jsonl"
    journal.write_text("", encoding="utf-8")

    jalons: list[Jalon] = []
    debut = time.perf_counter()
    prochain = secondes_entre_checkpoints
    donne = entrainement.DEPART_DONNE_ENTRAINEMENT
    vagues = parties = noeuds = 0
    pertes = {"politique": 0.0, "valeur": 0.0, "entropie": 0.0}

    while True:
        ecoule = time.perf_counter() - debut
        if ecoule >= plafond_secondes:
            break

        trajectoires, jouees = entrainement.jouer_une_vague(
            modele, pool, parties_par_vague, donne, appareil
        )
        donne += jouees
        vagues += 1
        parties += jouees
        noeuds += len(trajectoires)
        pertes = entrainement.mettre_a_jour(
            modele, optimiseur, trajectoires, appareil, random.Random(vagues)
        )

        ecoule = time.perf_counter() - debut
        if ecoule < prochain and ecoule < plafond_secondes:
            continue

        # --- Checkpoint ---
        numero = len(jalons) + 1
        chemin = dossier / f"checkpoint_{numero:02d}.pt"
        _sauver(modele, chemin)

        fige = entrainement.construire(appareil)
        fige.load_state_dict(modele.state_dict())
        fige.eval()
        pool.append(fige)
        if len(pool) > entrainement.POOL_MAXIMUM:
            # Le plafond garde les **plus recents** : un pool rempli de versions tres faibles
            # dilue le signal sans rien retenir de l'effondrement de convention.
            del pool[0]

        part, (basse, haute), gain = evaluer_le_garde_fou(modele, donnes_garde_fou)
        # Deux conditions, et il faut les deux : STAGNER et etre LOIN. Voir la docstring du
        # module -- appliquer le seul « loin » tuerait un apprenant sain, et c'est mesure.
        stagne = (
            numero >= PREMIER_CHECKPOINT_QUI_DECLENCHE
            and part <= jalons[numero - PREMIER_CHECKPOINT_QUI_DECLENCHE].part_fractionnee
        )
        loin = haute < GARDE_FOU_GREEDY
        declenche = stagne and loin
        jalon = Jalon(
            numero=numero,
            secondes=ecoule,
            vagues=vagues,
            parties=parties,
            noeuds=noeuds,
            perte_politique=pertes["politique"],
            perte_valeur=pertes["valeur"],
            entropie=pertes["entropie"],
            part_fractionnee=part,
            borne_basse=basse,
            borne_haute=haute,
            gain_moyen=gain,
            declenche=declenche,
        )
        jalons.append(jalon)
        with journal.open("a", encoding="utf-8") as fichier:
            fichier.write(json.dumps(asdict(jalon), ensure_ascii=False) + "\n")
        print(
            f"[{numero:02d}] {ecoule:7.1f} s  {parties:8d} parties  "
            f"part {part:.4%} IC [{basse:.4%} ; {haute:.4%}]  gain {gain:+.4f}  "
            f"H {pertes['entropie']:.4f}"
            + ("  -- GARDE-FOU DECLENCHE" if declenche else ""),
            flush=True,
        )
        if declenche:
            break
        prochain += secondes_entre_checkpoints

    _sauver(modele, dossier / "final.pt")
    return jalons


def main(argv: list[str] | None = None) -> int:
    """Point d'entree de la campagne.

    Reproduire :

        UV_LINK_MODE=copy uv run python -m agents.campagne --dossier models/phase3
    """
    import argparse
    import sys

    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--dossier", type=Path, default=Path("models/phase3"))
    analyseur.add_argument("--minutes", type=float, default=PLAFOND_SECONDES / 60)
    analyseur.add_argument(
        "--minutes-entre-checkpoints", type=float, default=SECONDES_ENTRE_CHECKPOINTS / 60
    )
    analyseur.add_argument("--parties-par-vague", type=int, default=PARTIES_PAR_VAGUE)
    analyseur.add_argument("--donnes-garde-fou", type=int, default=DONNES_GARDE_FOU)
    analyseur.add_argument("--appareil", default="cpu")
    arguments = analyseur.parse_args(argv)

    reconfigurer = getattr(sys.stdout, "reconfigure", None)
    if reconfigurer is not None:
        reconfigurer(encoding="utf-8")

    quantile = dim.quantile_bilateral(0.01, CHECKPOINTS_ATTENDUS)
    print(
        f"# Campagne phase 3 -- plafond {arguments.minutes:.0f} min, checkpoint tous les "
        f"{arguments.minutes_entre_checkpoints:.0f} min",
        flush=True,
    )
    print(
        f"# Garde-fou : part fractionnee contre 2 aleatoires, 3 sieges agreges, seuil "
        f"{GARDE_FOU_GREEDY:.4%} ; IC corrige Bonferroni pour {CHECKPOINTS_ATTENDUS} "
        f"regards (z = {quantile:.4f})",
        flush=True,
    )
    jalons = entrainer(
        dossier=arguments.dossier,
        plafond_secondes=arguments.minutes * 60,
        secondes_entre_checkpoints=arguments.minutes_entre_checkpoints * 60,
        parties_par_vague=arguments.parties_par_vague,
        appareil=torch.device(arguments.appareil),
        donnes_garde_fou=arguments.donnes_garde_fou,
    )
    if not jalons:
        print("# aucun checkpoint : le plafond est trop court pour un seul intervalle")
        return 1
    dernier = jalons[-1]
    print(
        f"# Fin. {len(jalons)} checkpoints, {dernier.parties} parties d'entrainement. "
        f"Garde-fou au dernier checkpoint : part {dernier.part_fractionnee:.4%} contre "
        f"{GARDE_FOU_GREEDY:.4%}"
        + (" -- DECLENCHE" if dernier.declenche else " -- non declenche")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CHECKPOINTS_ATTENDUS",
    "DONNES_GARDE_FOU",
    "GARDE_FOU_GREEDY",
    "Jalon",
    "entrainer",
    "evaluer_le_garde_fou",
    "main",
]

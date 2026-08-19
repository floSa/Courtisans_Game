"""Combien de fois le greedy decide un ciblage sans ses Assassins en attente.

**Defaut majeur releve par l'audit croise de la phase 2.** La pose du greedy est evaluee avec ses
Assassins resolus **conjointement** -- l'arbitrage G-combine du paragraphe 5.3 du document
d'instrument. Ses ciblages, eux, se decident **un nœud a la fois** : `Perception` porte
l'Assassin en cours et pas les suivants, donc la politique **ne peut pas** regarder plus loin.

L'incoherence est **structurelle et non un accident de code** : l'action de pose de l'adaptateur
est atomique -- un identifiant encode le bloc de trois cartes entier --, donc le bloc est choisi
d'un coup sous une evaluation conjointe pendant que le ciblage se decide apres, sans memoire de ce
que le bloc contenait.

Ce module **mesure** cet ecart. Il ne le corrige pas : corriger le code referait un autre agent et
invaliderait M3 et M4 entiers. La correction est dans la **description** de l'agent -- voir la
section correspondante en tete de `agents/greedy.py`.

Deux lectures, deux denominateurs, et c'est le meme piege que celui du paragraphe 6
------------------------------------------------------------------------------------
« X % des nœuds ou un Assassin reste en attente avec un argmax myope different » admet **deux**
lectures :

  - la part parmi les nœuds **a Assassin en attente** -- `incoherence/argmax-differents` ;
  - la part parmi **tous** les nœuds de ciblage -- `incoherence/argmax-differents-tous-noeuds`.

Les deux sont publiees, chacune avec son grain, et elles ne se soustraient pas l'une de l'autre.
Un chiffre dont on ne sait pas de quoi il est la part n'est pas auditable : c'est exactement la
faute que la parade de `comportements.ecart_de_taux` rend desormais impossible.

Deux numerateurs, et ils ne disent pas la meme chose
----------------------------------------------------
  - **argmax differents** : les deux ensembles d'argmax ne sont pas egaux. C'est la lecture
    litterale, et c'est celle que l'audit a chiffree.
  - **myope non optimal** : l'argmax myope contient une action que l'argmax coherent **rejette**.
    C'est la lecture qui **coute** : sur ces nœuds-la, le departage uniforme du greedy peut tirer
    une action coherentement dominee. Le premier majore le second par construction.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from agents.greedy import evaluer_ciblages_coherents
from courtisans.config import GameConfig
from courtisans.engine import Phase
from mesure.binomiale import intervalle_clopper_pearson
from mesure.comportements import VUE_DECIDEUR, Compte, cumuler
from mesure.instance import ENTRAINEMENT_3J
from mesure.trace import TracePartie

GRAIN_ATTENTE = "nœuds de ciblage a >= 1 Assassin en attente"
GRAIN_TOUS = "nœuds de ciblage, tous"


@dataclass(frozen=True)
class Intervalle:
    """Un taux et son intervalle exact. `None` partout si le denominateur est vide."""

    taux: float | None
    bas: float | None
    haut: float | None

    def __str__(self) -> str:
        if self.taux is None:
            return "sans objet"
        return f"{100 * self.taux:.2f} % [{100 * self.bas:.2f} ; {100 * self.haut:.2f}]"


def intervalle_exact(compte: Compte, risque: float = 0.01) -> Intervalle:
    """L'intervalle de Clopper-Pearson du taux de `compte`, **exact et non normal**.

    Obligatoire sur ce diagnostic : a quelques centaines de nœuds l'intervalle est large, et sans
    lui un lecteur qui verrait deux estimations differentes lirait une contradiction la ou il n'y
    a que du bruit d'echantillonnage. Deux mesures independantes ne se comparent que par leurs
    intervalles.
    """
    if compte.total == 0:
        return Intervalle(None, None, None)
    bas, haut = intervalle_clopper_pearson(compte.succes, compte.total, risque)
    return Intervalle(compte.succes / compte.total, bas, haut)


def _argmax(valeurs: dict[int, int]) -> set[int]:
    """Les actions qui atteignent le maximum. Un ensemble : une egalite en est un."""
    meilleur = max(valeurs.values())
    return {action for action, valeur in valeurs.items() if valeur == meilleur}


def mesurer_incoherence(
    traces: Sequence[TracePartie], config: GameConfig, sieges: Sequence[int] | None = None
) -> dict[str, Compte]:
    """Les trois compteurs de l'incoherence, sur les sieges mesures.

    L'evaluation myope est **relue de la trace** (`Decision.valeurs`, produite par
    `greedy.evaluer_actions`), jamais recalculee : la recalculer ici la ferait deriver de celle de
    l'agent mesure, ce qui est exactement l'erreur que l'etalon commun evite.

    L'evaluation coherente est calculee par `greedy.evaluer_ciblages_coherents` sur les Assassins
    en attente **releves du moteur** et enregistres dans la trace.
    """
    retenus = tuple(range(config.joueurs)) if sieges is None else tuple(sieges)
    tous = 0
    avec_attente = 0
    differents = 0
    non_optimal = 0
    for trace in traces:
        for decision in trace.decisions:
            if decision.phase is not Phase.CIBLAGE or decision.joueur not in retenus:
                continue
            tous += 1
            if not decision.assassins_en_attente:
                # Sans Assassin en attente les deux evaluations coincident par construction --
                # c'est teste --, donc ce nœud ne peut pas porter d'ecart. Il compte au
                # denominateur « tous », pas a celui de l'occasion.
                continue
            avec_attente += 1
            myope = _argmax(decision.valeurs)
            coherente = _argmax(
                evaluer_ciblages_coherents(
                    connues=decision.connues,
                    cibles=decision.cibles,
                    actions_legales=tuple(decision.valeurs),
                    en_attente=decision.assassins_en_attente,
                    moi=decision.joueur,
                    config=config,
                )
            )
            if myope != coherente:
                differents += 1
            if not myope <= coherente:
                non_optimal += 1
    return {
        "incoherence/argmax-differents": Compte(
            "incoherence/argmax-differents", differents, avec_attente, GRAIN_ATTENTE, VUE_DECIDEUR
        ),
        "incoherence/myope-non-optimal": Compte(
            "incoherence/myope-non-optimal", non_optimal, avec_attente, GRAIN_ATTENTE, VUE_DECIDEUR
        ),
        "incoherence/argmax-differents-tous-noeuds": Compte(
            "incoherence/argmax-differents-tous-noeuds", differents, tous, GRAIN_TOUS, VUE_DECIDEUR
        ),
    }


def sous_echantillon_de_la_campagne_b(donnes: int) -> list[tuple[TracePartie, int]]:
    """Les `donnes` **premieres donnes de la campagne B**, avec le siege mesure de chacune.

    **Ce n'est pas une population neuve, et c'est deliberé.** Le chiffre de l'incoherence decrit
    le comportement du greedy **dans les campagnes publiees** : le mesurer sur d'autres graines
    aurait fabrique une troisieme population a auditer pour rien. `phase2.campagne_b` est appelee
    avec ses decalages de graine d'origine, donc ces parties **sont** les premieres de la
    campagne B, a l'identique.

    Rend `(trace, siege du greedy)`, les sieges tournant comme partout ailleurs.
    """
    from mesure.phase2 import campagne_b

    apparies: list[tuple[TracePartie, int]] = []
    for groupe in campagne_b(donnes):
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
            (siege,) = sieges
            apparies.append((trace, siege))
    return apparies


def main(argv: Sequence[str] | None = None) -> int:
    """Chiffre l'incoherence et l'imprime avec ses intervalles exacts."""
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--donnes", type=int, default=200)
    arguments = analyseur.parse_args(argv)

    apparies = sous_echantillon_de_la_campagne_b(arguments.donnes)
    # Chaque trace n'est mesuree que sur le siege du greedy : agreger par siege mesure, comme
    # `mesurer_comportements`. `cumuler` leve si deux grains diffèrent.
    cumul: dict[str, Compte] = {}
    for trace, siege in apparies:
        partiel = mesurer_incoherence([trace], ENTRAINEMENT_3J, sieges=[siege])
        for nom, compte in partiel.items():
            cumul[nom] = cumuler(cumul[nom], compte) if nom in cumul else compte

    print(
        f"echantillon : donnes 0 a {arguments.donnes - 1} de la **campagne B**, "
        f"{len(apparies)} parties (3 sieges par donne), siege du greedy seul"
    )
    print("graines : celles de `phase2.campagne_b`, inchangees")
    print()
    largeur = max(len(nom) for nom in cumul)
    for nom, compte in cumul.items():
        borne = intervalle_exact(compte)
        print(f"{nom:{largeur}s} {compte.succes:>5d}/{compte.total:<6d} {borne}  [{compte.grain}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

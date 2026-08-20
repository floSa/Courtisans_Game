"""Quelles lignes de M4 la phase 3 peut separer -- **a SON budget, pas a celui du protocole**.

Pourquoi ce module existe
--------------------------
Le rapport de la phase 2 marque **19 lignes sur 34 « hors budget »** et **2 « aveugles par le
bas »**. Ces deux marqueurs sont **calcules sur les 1 000 parties** que le protocole donnait
alors a la phase 3 : le rapport l'ecrit noir sur blanc, « Marqueur `(hors budget)` calcule sur
les 1000 parties de la phase 3 ».

**La phase 3 s'est dimensionnee elle-meme et se donne 6 000 parties** (voir
`mesure/phase3_hypothese_et_instrument.md`, paragraphe 2.2). Recopier 19 et 2 dans son rapport
serait exactement la faute que ce projet paie depuis trois phases : un chiffre exact sur une
population -- ici un **budget** -- que la phrase ne nomme pas.

Ce que ce module fait, et ce qu'il ne fait pas
------------------------------------------------
Il **relit le rapport livre** de la phase 2, reconstruit les 34 `Compte`, et repasse chacun par
`phase2.budget_d_un_compteur` -- **la fonction unique** que l'audit du tour 2 a imposee la ou
trois sites deduisaient chacun leur denominateur, dont l'un avec un facteur trois indu.

Il ne rejoue **aucune partie** et ne remesure **aucun taux** : les taux de la phase 2 sont
acquis et audites. Seuls les deux marqueurs, qui dependent du budget, sont recalcules.

Le controle qui rend le recalcul credible
-------------------------------------------
**A 1 000 parties, la reconstruction doit retrouver exactement 19 et 2.** Si elle ne les
retrouve pas, c'est la reconstruction qui est fausse, et aucun de ses chiffres a 6 000 parties
ne vaut. Ce controle est dans le code -- `verifier_contre_la_phase_2` **leve** -- et non dans un
commentaire : l'unite se reconstruit avant la valeur, et separement.

Reproduire :

    UV_LINK_MODE=copy uv run python -m mesure.phase3_budget_des_comportements
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

from mesure import comportements as comp
from mesure import phase2

#: Le rapport livre de la phase 2. Sa table de la section 5 est la source des 34 comptes.
RAPPORT = pathlib.Path("mesure/resultats/phase2.md")

#: Le nombre de parties de la campagne B, sur laquelle la colonne greedy est mesuree. Il entre
#: dans `observations_par_partie`, donc dans le denominateur par partie de chaque compteur.
NB_PARTIES_CAMPAGNE_B = 10_002

#: Les deux marqueurs **publies** par la phase 2, a son budget de 1 000 parties. Ils servent de
#: controle, pas de resultat.
HORS_BUDGET_PUBLIE = 19
AVEUGLES_PUBLIES = 2

#: Une ligne de la table de la section 5 : `| \`nom\` | taux % (a/b) | ... | grain | vue |`.
_LIGNE = re.compile(r"^\| `(B[1-7][^`]*)` \|")
_TAUX = re.compile(r"\*?\*?([\d.]+) ?%\*?\*? \((\d+)/(\d+)\)")


@dataclass(frozen=True)
class LigneDeBudget:
    """Un compteur, et ce qu'il peut separer a deux budgets differents.

    Attributes:
        nom: le nom du compteur, tel qu'il est publie.
        taux: son taux chez le greedy, ou `None` si le denominateur est nul.
        detectable_1000: l'ecart detectable au budget de 1 000 parties.
        detectable_6000: le meme, au budget de la phase 3.
        parties_requises: parties pour etablir l'ecart greedy-hasard observe, ou `None`.
        hors_budget_1000: le marqueur publie par la phase 2.
        hors_budget_6000: le marqueur **au budget de la phase 3**.
        aveugle_1000: l'ecart detectable depasse le taux, au budget de 1 000.
        aveugle_6000: idem, au budget de la phase 3.
    """

    nom: str
    taux: float | None
    detectable_1000: float | None
    detectable_6000: float | None
    parties_requises: int | None
    hors_budget_1000: bool
    hors_budget_6000: bool
    aveugle_1000: bool
    aveugle_6000: bool


def _comptes_du_rapport() -> list[tuple[comp.Compte, float | None]]:
    """Reconstruit les 34 comptes depuis la table de la section 5 du rapport livre.

    Rend `(compte greedy, ecart greedy - hasard)`. L'ecart est `None` quand la colonne hasard
    n'est pas lisible -- il ne sert qu'a `parties_requises`, jamais aux ecarts detectables.

    Le rapport publie certaines lignes deux fois, dans deux tables : **la premiere occurrence
    seule est retenue**, et le doublon est ignore par son nom. Compter deux fois une ligne
    gonflerait le total sans que rien ne le signale.
    """
    texte = RAPPORT.read_text(encoding="utf-8")
    comptes: list[tuple[comp.Compte, float | None]] = []
    vus: set[str] = set()
    for ligne in texte.splitlines():
        entete = _LIGNE.match(ligne)
        if entete is None:
            continue
        nom = entete.group(1)
        if nom in vus:
            continue
        cellules = [c.strip() for c in ligne.strip("|").split("|")]
        if len(cellules) < 5:
            continue
        greedy = _TAUX.match(cellules[1])
        if greedy is None:
            continue
        vus.add(nom)
        _, succes, total = greedy.groups()
        compte = comp.Compte(
            nom=nom,
            succes=int(succes),
            total=int(total),
            grain=cellules[3],
            vue=cellules[4],
        )
        hasard = _TAUX.match(cellules[2])
        ecart = None
        if hasard is not None and compte.taux() is not None:
            ecart = compte.taux() - int(hasard.group(2)) / int(hasard.group(3))
        comptes.append((compte, ecart))
    return comptes


def lignes_de_budget(budget: int = 6_000) -> list[LigneDeBudget]:
    """Les 34 compteurs, avec leurs marqueurs aux deux budgets."""
    resultat = []
    for compte, ecart in _comptes_du_rapport():
        mille = phase2.budget_d_un_compteur(
            compte, NB_PARTIES_CAMPAGNE_B, ecart, budget=phase2.BUDGET_PHASE_3
        )
        mien = phase2.budget_d_un_compteur(
            compte, NB_PARTIES_CAMPAGNE_B, ecart, budget=budget
        )
        resultat.append(
            LigneDeBudget(
                nom=compte.nom,
                taux=compte.taux(),
                detectable_1000=mille.detectable,
                detectable_6000=mien.detectable,
                parties_requises=mille.parties,
                hors_budget_1000=mille.hors_budget,
                hors_budget_6000=mien.hors_budget,
                aveugle_1000=mille.aveugle_par_le_bas,
                aveugle_6000=mien.aveugle_par_le_bas,
            )
        )
    return resultat


def verifier_contre_la_phase_2(lignes: list[LigneDeBudget]) -> None:
    """Leve si la reconstruction ne retrouve pas les chiffres publies par la phase 2.

    **C'est le controle qui rend tout le reste lisible.** Sans lui, un recalcul a 6 000 parties
    serait un nombre produit par du code que personne n'a confronte a une valeur connue.

    Raises:
        ValueError: si le compte de lignes, le compte de hors-budget ou le compte d'aveugles
            differe de ce que le rapport publie.
    """
    if len(lignes) != 34:
        raise ValueError(
            f"{len(lignes)} compteurs reconstruits depuis le rapport, la phase 2 en publie 34. "
            f"La table a change de forme : la reconstruction est fausse, pas le rapport."
        )
    hors = sum(1 for ligne in lignes if ligne.hors_budget_1000)
    aveugles = sum(1 for ligne in lignes if ligne.aveugle_1000)
    if hors != HORS_BUDGET_PUBLIE or aveugles != AVEUGLES_PUBLIES:
        raise ValueError(
            f"la reconstruction rend {hors} hors budget et {aveugles} aveugles au budget de "
            f"{phase2.BUDGET_PHASE_3} parties, la phase 2 publie {HORS_BUDGET_PUBLIE} et "
            f"{AVEUGLES_PUBLIES}. Aucun chiffre a un autre budget ne vaut tant que celui-ci "
            f"ne tombe pas juste."
        )


def main(argv: list[str] | None = None) -> int:
    """Ecrit les deux colonnes, et les NOMS des lignes qui changent de camp."""
    import argparse
    import sys

    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--budget", type=int, default=6_000)
    arguments = analyseur.parse_args(argv)

    reconfigurer = getattr(sys.stdout, "reconfigure", None)
    if reconfigurer is not None:
        reconfigurer(encoding="utf-8")

    lignes = lignes_de_budget(arguments.budget)
    verifier_contre_la_phase_2(lignes)

    hors_1000 = [x.nom for x in lignes if x.hors_budget_1000]
    hors_mien = [x.nom for x in lignes if x.hors_budget_6000]
    aveugles_1000 = [x.nom for x in lignes if x.aveugle_1000]
    aveugles_mien = [x.nom for x in lignes if x.aveugle_6000]

    print(f"# {len(lignes)} compteurs, deux budgets")
    print(f"  controle contre la phase 2 a {phase2.BUDGET_PHASE_3} parties : OK")
    print()
    print(f"{'':24s} {phase2.BUDGET_PHASE_3:>8d} {arguments.budget:>8d}")
    print(f"{'hors budget':24s} {len(hors_1000):>8d} {len(hors_mien):>8d}")
    print(f"{'aveugles par le bas':24s} {len(aveugles_1000):>8d} {len(aveugles_mien):>8d}")
    print()
    entrent = [x for x in lignes if x.hors_budget_1000 and not x.hors_budget_6000]
    print(f"# {len(entrent)} lignes ENTRENT dans le budget -- leurs noms, pas leur compte")
    for ligne in entrent:
        print(f"  {ligne.nom:36s} demande {ligne.parties_requises} parties")
    print()
    voient = [x for x in lignes if x.aveugle_1000 and not x.aveugle_6000]
    print(f"# {len(voient)} lignes CESSENT d'etre aveugles par le bas")
    for ligne in voient:
        print(
            f"  {ligne.nom:36s} taux {ligne.taux:.4%}  "
            f"detectable {ligne.detectable_1000:.4%} -> {ligne.detectable_6000:.4%}"
        )
    print()
    print(f"# Les {len(hors_mien)} lignes qui restent hors budget, et ne seront PAS comparees")
    for nom in hors_mien:
        print(f"  {nom}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AVEUGLES_PUBLIES",
    "HORS_BUDGET_PUBLIE",
    "LigneDeBudget",
    "NB_PARTIES_CAMPAGNE_B",
    "RAPPORT",
    "lignes_de_budget",
    "main",
    "verifier_contre_la_phase_2",
]

"""Etape 4 de l'audit : reintroduire dans SON code la faute exacte que je soupconne.

Une correction que rien ne tient rouge se defait au commit suivant. Chaque mutation
ci-dessous est une faute plausible -- pas un caractere au hasard : c'est la lecture que le
constructeur aurait pu faire, ou celle que la phase 1 a effectivement faite. Pour chacune,
la question est : **quel test tombe, et est-ce le bon ?**

Une mutation qui ne fait tomber aucun test designe une affirmation du compte rendu que rien
ne protege. Une mutation qui fait tomber cinquante tests dont aucun ne nomme le sujet est
presque aussi mauvaise : le defaut serait signale, mais pas identifie.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Mutation:
    """Une faute a reintroduire, et les tests censes la voir.

    Attributes:
        nom: ce que la faute represente, en mots.
        fichier: chemin relatif depuis la racine du depot.
        avant: le texte exact a remplacer. Doit apparaitre **une seule fois**.
        apres: le texte fautif.
        cibles: les chemins pytest a executer. Vide = toute la suite.
    """

    nom: str
    fichier: str
    avant: str
    apres: str
    cibles: tuple[str, ...] = field(default=())


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        nom="la perception laisse filtrer l'identite d'un dos adverse",
        fichier="agents/perception.py",
        avant="carte=cible.carte if connue else None,",
        apres="carte=cible.carte,",
        cibles=("tests/agents/", "tests/audit_phase2/"),
    ),
    Mutation(
        nom="le predicat de redaction du moteur est inverse",
        fichier="courtisans/infoset.py",
        avant="if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:",
        apres="if posee.carte.role in ROLES_CACHES and posee.poseur == joueur:",
        cibles=("tests/infoset/", "tests/agents/", "tests/audit_phase2/"),
    ),
    Mutation(
        nom="un taux sur un denominateur vide vaut 0 au lieu de ne pas exister",
        fichier="mesure/comportements.py",
        avant="return None if self.total == 0 else self.succes / self.total",
        apres="return 0.0 if self.total == 0 else self.succes / self.total",
        cibles=("tests/mesure/", "tests/audit_phase2/"),
    ),
    Mutation(
        nom="B1 exige l'Obscurite la ou le paragraphe 2.2 tranche l'Indifference",
        fichier="mesure/comportements.py",
        avant=(
            "if _paye(trace, famille, adversaire, exige_obscurite=False):\n"
            '                    trouve["B1-motif"] = True'
        ),
        apres=(
            "if _paye(trace, famille, adversaire, exige_obscurite=True):\n"
            '                    trouve["B1-motif"] = True'
        ),
        cibles=("tests/mesure/test_comportements.py", "tests/audit_phase2/"),
    ),
    Mutation(
        nom="B1 oublie que nourrir doit PRECEDER basculer",
        fichier="mesure/comportements.py",
        avant="if not [n for n in baisser.get(famille, []) if n > min(donnes)]:",
        apres="if not baisser.get(famille, []):",
        cibles=("tests/mesure/test_comportements.py", "tests/audit_phase2/"),
    ),
    Mutation(
        nom="B4 compte les noeuds sans cible, ou le refus est force",
        fichier="mesure/comportements.py",
        avant="if decision.joueur not in retenus or not decision.cibles:",
        apres="if decision.joueur not in retenus:",
        cibles=("tests/mesure/", "tests/audit_phase2/"),
    ),
)


@dataclass
class Resultat:
    """Ce qu'une mutation a produit."""

    mutation: Mutation
    applicable: bool
    code_retour: int | None
    resume: str


def _pytest(cibles: tuple[str, ...]) -> tuple[int, str]:
    """Lance pytest sur `cibles` et rend `(code, derniere ligne utile)`."""
    commande = [sys.executable, "-m", "pytest", "-x", "-q", *(cibles or ("tests",))]
    fin = subprocess.run(
        commande, cwd=RACINE, capture_output=True, text=True, errors="replace"
    )
    lignes = [ligne for ligne in fin.stdout.splitlines() if ligne.strip()]
    interessantes = [ligne for ligne in lignes if "passed" in ligne or "failed" in ligne]
    return fin.returncode, (interessantes[-1] if interessantes else (lignes[-1] if lignes else ""))


def _noms_des_echecs(cibles: tuple[str, ...]) -> list[str]:
    """Les tests qui tombent, nommes. Sans `-x`, pour les voir tous."""
    commande = [sys.executable, "-m", "pytest", "-q", "--no-header", *(cibles or ("tests",))]
    fin = subprocess.run(
        commande, cwd=RACINE, capture_output=True, text=True, errors="replace"
    )
    return [
        ligne.split(" ")[1]
        for ligne in fin.stdout.splitlines()
        if ligne.startswith("FAILED ")
    ]


def jouer(mutation: Mutation, nommer: bool = False) -> Resultat:
    """Applique la mutation, lance les tests, **restaure toujours** le fichier."""
    chemin = RACINE / mutation.fichier
    original = chemin.read_text(encoding="utf-8")
    if original.count(mutation.avant) != 1:
        return Resultat(
            mutation,
            applicable=False,
            code_retour=None,
            resume=(
                f"motif absent ou ambigu : {original.count(mutation.avant)} occurrence(s) "
                f"de {mutation.avant!r}"
            ),
        )
    try:
        chemin.write_text(
            original.replace(mutation.avant, mutation.apres), encoding="utf-8"
        )
        code, resume = _pytest(mutation.cibles)
        if nommer and code != 0:
            echecs = _noms_des_echecs(mutation.cibles)
            resume = f"{resume} | {len(echecs)} echec(s) : " + ", ".join(echecs[:6])
        return Resultat(mutation, applicable=True, code_retour=code, resume=resume)
    finally:
        chemin.write_text(original, encoding="utf-8")


def main() -> int:
    """Joue toutes les mutations et rend 1 si l'une d'elles survit."""
    nommer = "--nommer" in sys.argv
    survivantes = 0
    for mutation in MUTATIONS:
        resultat = jouer(mutation, nommer=nommer)
        if not resultat.applicable:
            etat = "NON APPLICABLE"
        elif resultat.code_retour == 0:
            etat = "SURVIT -- aucun test ne la voit"
            survivantes += 1
        else:
            etat = "TUEE"
        print(f"[{etat}] {mutation.nom}")
        print(f"    {mutation.fichier} : {resultat.resume}")
    print(f"\n{len(MUTATIONS) - survivantes} / {len(MUTATIONS)} mutations tuees")
    return 1 if survivantes else 0


if __name__ == "__main__":
    raise SystemExit(main())

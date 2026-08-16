"""Test de mutation : verifier que la suite sait echouer.

**Pourquoi cet outil existe.** A l'etape 6, la suite affichait 395 verts sur 395. En
supprimant deux blocs de l'encodage -- la phase et la zone de l'Assassin en cours -- puis
en faisant compter les cartes mortes dans le residu, elle affichait encore 395 sur 395.
Deux des trois pieges du paragraphe 4.2, classes bloquant et critique, n'etaient enforces
par aucun test alors que tout passait.

La cause est generale : **un test qui verifie la coherence entre deux sorties du meme
calcul ne teste rien.** C16 et I8 comparaient la chaine et le tenseur, tous deux rendus
depuis la meme observation ; retirer un champ des deux les laissait coherents.

Une suite qui passe sans qu'on ait verifie qu'elle sait echouer n'est pas une suite de
tests. Cet outil applique une mutation connue au coeur, rejoue la suite, et rapporte
combien de tests tombent. Une mutation qui ne fait rien tomber designe un trou.

Usage :

    uv run python outillage/mutation.py                  # toutes les mutations
    uv run python outillage/mutation.py --cible tests/infoset
    uv run python outillage/mutation.py --nom residu-compte-les-morts

L'outil refuse de tourner si le depot a des modifications non commitees : il restaure les
fichiers avec `git checkout`, ce qui detruirait un travail en cours.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Mutation:
    """Une faute plausible, injectee volontairement dans le coeur.

    Attributes:
        nom: identifiant court, utilisable avec `--nom`.
        fichier: chemin relatif du fichier a muter.
        avant: le texte a remplacer. Doit apparaitre exactement une fois.
        apres: le texte de remplacement.
        vise: ce que la mutation casse, en une ligne.
    """

    nom: str
    fichier: str
    avant: str
    apres: str
    vise: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation(
        nom="espions-adverses-visibles",
        fichier="courtisans/infoset.py",
        avant=(
            "        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:\n"
            "            dos.append(posee)\n"
            "        else:\n"
            "            connues.append(posee)"
        ),
        apres=(
            "        connues.append(posee)\n"
            "        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:\n"
            "            dos.append(posee)"
        ),
        vise="l'identite des Espions adverses fuite dans l'encodage (invariant I7)",
    ),
    Mutation(
        nom="phase-et-assassin-absents",
        fichier="courtisans/infoset.py",
        avant=(
            '        Bloc("phase", _phase_one_hot(etat)),\n'
            '        Bloc("assassin", _assassin_one_hot(assassin, joueur, config)),\n'
        ),
        apres="",
        vise="deux poses differentes donnent le meme tenseur avec des cibles differentes",
    ),
    Mutation(
        nom="residu-compte-les-morts",
        fichier="courtisans/infoset.py",
        avant=(
            "                - compte_main[(famille, role)]\n"
            "                - compte_morts[(famille, role)]\n"
            "            )"
        ),
        apres="                - compte_main[(famille, role)]\n            )",
        vise="le residu surestime ce qui circule encore (regle 2 du paragraphe 4.2)",
    ),
    Mutation(
        nom="meurtre-obligatoire",
        fichier="courtisans/engine.py",
        avant="        return list(range(len(self.cibles_courantes()) + 1))",
        apres=(
            "        cibles = self.cibles_courantes()\n"
            "        return list(range(len(cibles) + 1)) if not cibles else list(\n"
            "            range(len(cibles))\n"
            "        )"
        ),
        vise="le refus de tuer disparait quand une cible existe (regle R2, test C5)",
    ),
    Mutation(
        nom="fin-joueur-par-joueur",
        fichier="courtisans/engine.py",
        avant=(
            "        self._joueur = (self._joueur + 1) % self.config.joueurs\n"
            "        if self._joueur == 0:\n"
            "            self._tours_joues += 1\n"
            "            if not rules.peut_entamer_un_tour_de_table(\n"
            "                len(self._pioche), self.config.joueurs\n"
            "            ):"
        ),
        apres=(
            "        self._joueur = (self._joueur + 1) % self.config.joueurs\n"
            "        if True:\n"
            "            self._tours_joues += 1 if self._joueur == 0 else 0\n"
            "            if len(self._pioche) < 3:"
        ),
        vise="la fin de partie est testee joueur par joueur, donc les tours sont inegaux",
    ),
    Mutation(
        nom="noble-vaut-un",
        fichier="courtisans/cards.py",
        avant="        Role.NOBLE: 2,",
        apres="        Role.NOBLE: 1,",
        vise="l'influence se compte en cartes et non en valeur (arbitrage Q1)",
    ),
    Mutation(
        nom="points-au-poseur",
        fichier="courtisans/rules.py",
        avant="        totaux[posee.zone.proprietaire] += int(statut) * posee.carte.valeur",
        apres="        totaux[posee.poseur] += int(statut) * posee.carte.valeur",
        vise="les points vont au poseur et non au proprietaire du domaine (test C11)",
    ),
    Mutation(
        nom="morts-comptes-au-decompte",
        fichier="courtisans/engine.py",
        avant="        statuts = rules.statuts(self._posees, self.config.familles)",
        apres=(
            "        statuts = rules.statuts(\n"
            "            self._posees + self._defausse, self.config.familles\n"
            "        )"
        ),
        vise="une carte tuee compte encore dans l'influence (test C9, invariant I6)",
    ),
    Mutation(
        nom="main-non-triee",
        fichier="courtisans/rules.py",
        avant="    return tuple(sorted(cartes))",
        apres="    return tuple(cartes)",
        vise="l'ordre canonique de la main disparait, une action ne designe plus la meme carte",
    ),
    Mutation(
        nom="doublons-non-masques",
        fichier="courtisans/rules.py",
        avant="        representantes.setdefault(contenu, action)",
        apres="        representantes[(contenu, action)] = action",
        vise="deux actions legales posent les memes cartes aux memes endroits (test C14)",
    ),
)


def _depot_propre() -> bool:
    sortie = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=True,
    )
    return sortie.stdout.strip() == ""


def _restaurer(fichier: str) -> None:
    subprocess.run(["git", "checkout", "--", fichier], cwd=RACINE, check=True)


def _appliquer(mutation: Mutation) -> None:
    chemin = RACINE / mutation.fichier
    source = chemin.read_text(encoding="utf-8")
    occurrences = source.count(mutation.avant)
    if occurrences != 1:
        raise SystemExit(
            f"mutation {mutation.nom} : le motif apparait {occurrences} fois dans "
            f"{mutation.fichier}, il en faut exactement une. Le code a change : mets la "
            f"mutation a jour plutot que de la contourner."
        )
    chemin.write_text(source.replace(mutation.avant, mutation.apres), encoding="utf-8")


def _jouer(cible: str) -> tuple[int, int]:
    """Rejoue la suite et rend (verts, rouges)."""
    sortie = subprocess.run(
        [sys.executable, "-m", "pytest", cible, "-q", "--tb=no", "-p", "no:cacheprovider"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=False,
    )
    derniere = [ligne for ligne in sortie.stdout.splitlines() if ligne.strip()][-1]
    verts = rouges = 0
    for morceau in derniere.replace(",", " ").split():
        if morceau.isdigit():
            valeur = int(morceau)
        elif morceau.startswith("passed"):
            verts = valeur
        elif morceau.startswith("failed"):
            rouges = valeur
    return verts, rouges


def principal() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--cible", default="tests", help="selection pytest a rejouer")
    analyseur.add_argument("--nom", default=None, help="ne jouer qu'une mutation")
    arguments = analyseur.parse_args()

    if not _depot_propre():
        raise SystemExit(
            "le depot a des modifications non commitees : l'outil restaure les fichiers "
            "avec git checkout et les detruirait. Commite d'abord."
        )

    mutations = [m for m in MUTATIONS if arguments.nom in (None, m.nom)]
    if not mutations:
        raise SystemExit(f"aucune mutation nommee {arguments.nom!r}")

    print(f"{'mutation':32s} {'verts':>6s} {'rouges':>7s}  verdict")
    print("-" * 78)
    survivantes = []
    for mutation in mutations:
        _appliquer(mutation)
        try:
            verts, rouges = _jouer(arguments.cible)
        finally:
            _restaurer(mutation.fichier)
        verdict = "detectee" if rouges else "SURVIT -- trou de test"
        if not rouges:
            survivantes.append(mutation)
        print(f"{mutation.nom:32s} {verts:6d} {rouges:7d}  {verdict}")

    print("-" * 78)
    if survivantes:
        print(f"{len(survivantes)} mutation(s) non detectee(s) :")
        for mutation in survivantes:
            print(f"  - {mutation.nom} : {mutation.vise}")
        return 1
    print(f"{len(mutations)} mutation(s), toutes detectees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())

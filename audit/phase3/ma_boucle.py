"""La boucle de l'auditeur : ma construction de partie, mon tour de sieges, mon alea,
mon bootstrap. Aucune fonction de `mesure/phase3*.py` n'est importee ici -- c'est la
condition pour que la concordance dise quelque chose.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Callable

from agents.politique import politique_greedy
from agents.politique_reseau import charger, politique_reseau, politique_reseau_deterministe
from courtisans.engine import Engine, Phase, State
from mesure.instance import ENTRAINEMENT_3J

Politique = Callable[[State], int]


def jouer(seed: int, politiques: list[Politique]) -> tuple[list[float], list[int]]:
    """Une partie sur la donne `seed`. Rend (gains, scores). Ma propre boucle."""
    etat = Engine(ENTRAINEMENT_3J).reset(seed)
    garde = 0
    while etat.phase() is not Phase.TERMINAL:
        garde += 1
        if garde > 10000:
            raise RuntimeError("partie qui ne finit pas")
        if etat.phase() is Phase.CHANCE:
            etat.apply(etat.legal_actions()[0])
            continue
        joueur = etat.current_player()
        etat.apply(politiques[joueur](etat))
    scores = etat.scores()
    return etat.returns(), [scores[j] for j in range(ENTRAINEMENT_3J.joueurs)]


def part_fractionnee(scores: list[int], siege: int) -> float:
    """Ma definition, ecrite sans lire la sienne : 1/k si je suis au maximum partage
    par k joueurs, 0 sinon. Moyenne = 1/3 exactement sous echange des sieges."""
    maxi = max(scores)
    if scores[siege] != maxi:
        return 0.0
    return 1.0 / sum(1 for s in scores if s == maxi)


def campagne(
    fabrique_mesure: Callable[[random.Random], Politique],
    fabrique_adverse: Callable[[random.Random], Politique],
    donnes: range,
) -> dict:
    """Chaque donne jouee 3 fois : l'agent mesure au siege 0, puis 1, puis 2.

    L'alea de chaque politique est seme par (donne, siege occupe, role) -- distinct de la
    donne, comme la phase 1 l'a impose.
    """
    par_donne: list[list[float]] = []
    parts: list[float] = []
    gains: list[float] = []
    for d in donnes:
        trio: list[float] = []
        for siege in range(ENTRAINEMENT_3J.joueurs):
            politiques: list[Politique] = []
            for s in range(ENTRAINEMENT_3J.joueurs):
                alea = random.Random((d * 97 + siege * 13 + s) * 7919 + 5)
                politiques.append(
                    fabrique_mesure(alea) if s == siege else fabrique_adverse(alea)
                )
            gain, scores = jouer(d, politiques)
            trio.append(gain[siege])
            parts.append(part_fractionnee(scores, siege))
            gains.append(gain[siege])
        par_donne.append(trio)
    return {"par_donne": par_donne, "gains": gains, "parts": parts}


def bootstrap_par_donne(par_donne: list[list[float]], tirages: int, graine: int, niveau: float):
    """Mon bootstrap : je reechantillonne des DONNES, chacune apportant ses 3 parties."""
    alea = random.Random(graine)
    n = len(par_donne)
    plat = [statistics.fmean(t) for t in par_donne]
    moyennes = []
    for _ in range(tirages):
        moyennes.append(statistics.fmean(plat[alea.randrange(n)] for _ in range(n)))
    moyennes.sort()
    q = (1.0 - niveau) / 2.0
    bas = moyennes[max(0, int(math.floor(q * tirages)) - 1)]
    haut = moyennes[min(tirages - 1, int(math.ceil((1 - q) * tirages)) - 1)]
    return bas, haut


def rho_intra_donne(par_donne: list[list[float]]) -> float:
    """Correlation intraclasse par decomposition de variance, m = 3."""
    m = len(par_donne[0])
    n = len(par_donne)
    tous = [x for t in par_donne for x in t]
    grande = statistics.fmean(tous)
    inter = sum(m * (statistics.fmean(t) - grande) ** 2 for t in par_donne) / (n - 1)
    intra = sum((x - statistics.fmean(t)) ** 2 for t in par_donne for x in t) / (n * (m - 1))
    return (inter - intra) / (inter + (m - 1) * intra)


def greedy(alea: random.Random) -> Politique:
    return politique_greedy(alea)


def aleatoire(alea: random.Random) -> Politique:
    def politique(etat: State) -> int:
        return alea.choice(etat.legal_actions())

    return politique


def reseau(chemin: str = "models/phase3/final.pt", deterministe: bool = False):
    modele = charger(chemin, 205, 24)

    def fabrique(alea: random.Random) -> Politique:
        if deterministe:
            return politique_reseau_deterministe(modele)
        return politique_reseau(modele, alea)

    return fabrique

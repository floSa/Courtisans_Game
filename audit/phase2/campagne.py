"""Les quatre mesures de la phase 2, rejouees par l'auditeur.

Chaque mesure publie **plusieurs lectures nommees** plutot qu'un chiffre unique. Ce n'est
pas de l'indecision : c'est la seule facon de rendre auditable un enonce du protocole qui
ne definit pas son unite. « Si un siege gagne plus de 38 % des parties » ne dit pas ce
qu'est gagner quand les egalites sont conservees (paragraphe 5.1), et les trois lectures
possibles n'ont pas la meme valeur nulle -- deux d'entre elles n'ont meme pas 33,3 %.

L'appariement, et ce qu'il vaut entre politiques identiques
------------------------------------------------------------
Apparier, c'est rejouer la **meme donne** avec les agents permutes, pour retirer la
variance de distribution (paragraphe 1 du protocole). Entre trois agents **identiques**,
la permutation ne change aucune loi : les six permutations d'une donne sont six tirages
de la meme experience, correles par la donne partagee. L'appariement ne retire donc rien
et ne coute rien -- mais il divise le nombre de donnes distinctes par six a effectif
egal, et la correlation qui en resulte doit etre mesuree, pas supposee nulle.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import permutations
from statistics import mean, pvariance

from audit.phase2.greedy import Aleatoire, Greedy
from audit.phase2.trace import Trace, jouer
from courtisans.engine import Engine

#: Le decalage de seed des politiques aleatoires. Nomme, jamais en dur dans un appel :
#: l'audit de la phase 1 a paye deux fois une valeur en dur invisible dans les chiffres
#: qu'elle produisait.
DECALAGE_POLITIQUE = 1_000_000


def aleatoires(seed: int, joueurs: int) -> list[Aleatoire]:
    """Trois politiques uniformes, une graine par siege, reproductibles."""
    return [
        Aleatoire(random.Random(DECALAGE_POLITIQUE + seed * joueurs + siege))
        for siege in range(joueurs)
    ]


@dataclass
class Issue:
    """Ce qu'une partie rend, du point de vue d'une mesure de siege."""

    seed: int
    scores: tuple[int, ...]
    gains: tuple[float, ...]
    vainqueurs: tuple[int, ...]

    @classmethod
    def depuis(cls, trace: Trace) -> Issue:
        """Extrait l'issue d'une trace."""
        return cls(
            seed=trace.seed,
            scores=tuple(trace.scores_finaux),
            gains=tuple(trace.gains_finaux),
            vainqueurs=trace.vainqueurs,
        )


# ---------------------------------------------------------------------------------
# M1 -- l'avantage de siege
# ---------------------------------------------------------------------------------


@dataclass
class ResultatM1:
    """Les trois lectures de « gagner », plus le gain du paragraphe 5.2.

    Attributes:
        parties: nombre de parties jouees.
        donnes: nombre de **donnes distinctes** qui les portent. Deux parties issues de la
            meme donne ne sont pas deux observations independantes.
        strictes: par siege, parties ou il est **seul** au score maximum.
        partagees: par siege, parties ou il est au score maximum, ex aequo compris.
        gains: par siege, somme des gains du paragraphe 5.2.
        parties_avec_egalite: parties ou au moins deux joueurs finissent au maximum.
    """

    parties: int
    donnes: int
    strictes: list[int] = field(default_factory=list)
    partagees: list[int] = field(default_factory=list)
    gains: list[float] = field(default_factory=list)
    parties_avec_egalite: int = 0

    @property
    def nulle_stricte(self) -> float:
        """La valeur attendue d'un taux de victoire **stricte** sans avantage de siege.

        Ce n'est pas 1/3 : les parties a egalite n'ont pas de vainqueur unique, donc les
        trois taux stricts somment a `1 - P(egalite)`, pas a 1. Comparer un taux strict au
        seuil de 38 % contre une nulle de 33,3 % compare deux choses differentes.
        """
        return (self.parties - self.parties_avec_egalite) / (3 * self.parties)


def mesurer_m1(engine: Engine, seeds: Sequence[int], apparier: bool) -> ResultatM1:
    """L'avantage de siege sous jeu uniformement aleatoire.

    Args:
        seeds: les donnes. Une par partie si `apparier` est faux.
        apparier: si vrai, chaque donne est rejouee avec les `3! = 6` permutations des
            trois politiques, et le siege credite est celui qu'occupe la politique.
    """
    joueurs = engine.config.joueurs
    resultat = ResultatM1(parties=0, donnes=len(seeds))
    resultat.strictes = [0] * joueurs
    resultat.partagees = [0] * joueurs
    resultat.gains = [0.0] * joueurs
    for seed in seeds:
        ordres = list(permutations(range(joueurs))) if apparier else [tuple(range(joueurs))]
        for numero, ordre in enumerate(ordres):
            base = aleatoires(seed * len(ordres) + numero, joueurs)
            table = [base[ordre[siege]] for siege in range(joueurs)]
            issue = Issue.depuis(jouer(engine, seed, table))
            resultat.parties += 1
            if len(issue.vainqueurs) > 1:
                resultat.parties_avec_egalite += 1
            for siege in range(joueurs):
                if issue.vainqueurs == (siege,):
                    resultat.strictes[siege] += 1
                if siege in issue.vainqueurs:
                    resultat.partagees[siege] += 1
                resultat.gains[siege] += issue.gains[siege]
    return resultat


# ---------------------------------------------------------------------------------
# M2 -- la variance
# ---------------------------------------------------------------------------------


@dataclass
class ResultatM2:
    """Les variances, chacune nommee par ce dont elle est la variance.

    « La variance du score final entre parties » ne designe pas un nombre : le score d'un
    siege, les scores des trois sieges confondus, l'ecart au meilleur adversaire et le
    gain du paragraphe 5.2 ont quatre variances differentes. Seule la derniere dimensionne
    le nombre de parties necessaires pour conclure, puisque c'est le gain qui est compare.
    """

    parties: int
    variance_par_siege: list[float]
    variance_toutes_places: float
    variance_ecart: float
    variance_gain: float
    moyenne_par_siege: list[float]
    etendue_scores: tuple[int, int]
    scores_distincts: int


def mesurer_m2(issues: Sequence[Issue], joueurs: int) -> ResultatM2:
    """Les variances d'une campagne deja jouee."""
    if not issues:
        raise ValueError("aucune partie : il n'y a pas de variance a mesurer")
    par_siege = [[issue.scores[s] for issue in issues] for s in range(joueurs)]
    tous = [s for issue in issues for s in issue.scores]
    ecarts = [
        issue.scores[s] - max(v for j, v in enumerate(issue.scores) if j != s)
        for issue in issues
        for s in range(joueurs)
    ]
    gains = [issue.gains[s] for issue in issues for s in range(joueurs)]
    return ResultatM2(
        parties=len(issues),
        variance_par_siege=[pvariance(colonne) for colonne in par_siege],
        variance_toutes_places=pvariance(tous),
        variance_ecart=pvariance(ecarts),
        variance_gain=pvariance(gains),
        moyenne_par_siege=[mean(colonne) for colonne in par_siege],
        etendue_scores=(min(tous), max(tous)),
        scores_distincts=len(set(tous)),
    )


# ---------------------------------------------------------------------------------
# M3 -- le greedy contre l'aleatoire
# ---------------------------------------------------------------------------------


@dataclass
class ResultatM3:
    """Le greedy face a deux aleatoires, chaque donne jouee aux trois sieges.

    Attributes:
        rotations: parties jouees = `donnes x joueurs`, le greedy occupant chaque siege.
        victoires_strictes: parties ou le greedy est seul au maximum.
        victoires_partagees: parties ou il est au maximum, ex aequo compris.
        gain_total: somme de ses gains du paragraphe 5.2.
        par_siege: les memes trois comptes, siege par siege, pour verifier que la rotation
            a bien neutralise l'avantage de position au lieu de le moyenner en aveugle.
    """

    donnes: int
    rotations: int
    victoires_strictes: int
    victoires_partagees: int
    gain_total: float
    par_siege: list[tuple[int, int, float]]


def mesurer_m3(
    engine: Engine, seeds: Sequence[int], greedy: Greedy
) -> tuple[ResultatM3, list[Trace]]:
    """Le winrate du greedy contre deux politiques uniformes.

    Chaque donne est jouee `joueurs` fois, le greedy changeant de siege. C'est
    l'appariement du protocole applique a une comparaison qui, elle, oppose bien deux
    politiques differentes -- contrairement a M1.
    """
    joueurs = engine.config.joueurs
    resultat = ResultatM3(
        donnes=len(seeds),
        rotations=0,
        victoires_strictes=0,
        victoires_partagees=0,
        gain_total=0.0,
        par_siege=[(0, 0, 0.0) for _ in range(joueurs)],
    )
    traces: list[Trace] = []
    for seed in seeds:
        for siege in range(joueurs):
            base = aleatoires(seed * joueurs + siege, joueurs)
            table: list[object] = list(base)
            table[siege] = greedy
            trace = jouer(engine, seed, table)  # type: ignore[arg-type]
            traces.append(trace)
            issue = Issue.depuis(trace)
            resultat.rotations += 1
            strict = int(issue.vainqueurs == (siege,))
            partage = int(siege in issue.vainqueurs)
            resultat.victoires_strictes += strict
            resultat.victoires_partagees += partage
            resultat.gain_total += issue.gains[siege]
            a, b, c = resultat.par_siege[siege]
            resultat.par_siege[siege] = (a + strict, b + partage, c + issue.gains[siege])
    return resultat, traces

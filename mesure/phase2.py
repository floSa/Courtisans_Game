"""Les quatre mesures de la phase 2 : avantage de siege, variance, winrate du greedy, B1-B7.

Usage :

    uv run python -m mesure.phase2                        # le plan complet
    uv run python -m mesure.phase2 --donnes-a 50 --donnes-b 50   # repetition rapide

Ce module **n'interprete rien** : il compte, et affiche la decomposition de chaque chiffre.
Les seuils qu'il rappelle sont ceux de `phase2_hypothese_et_instrument.md`, ecrits et commites
avant la mesure.

Deux campagnes, et les memes parties servent plusieurs mesures
-------------------------------------------------------------
| Campagne | Composition | Plan | Sert |
|---|---|---|---|
| **A** | trois aleatoires | 1 667 x 6 = 10 002 | M1, M2, ligne de base **hasard** |
| **B** | 1 greedy, 2 aleatoires | 3 334 x 3 = 10 002 | M3, ligne de base **greedy** |

Mesurer la variance sur d'autres parties que l'avantage de siege n'apporterait rien et
interdirait de croiser les deux.

Les deux niveaux neutres, qui ne sont pas les memes
--------------------------------------------------
**`0,00` pour le gain moyen `returns()`** -- exact, par la somme nulle du paragraphe 5.2 des
regles, tenue par l'invariant I5. **`33,33 %` pour la part de victoire fractionnee** -- exact
aussi : les parts `1/k` somment a 1 sur les sieges a chaque partie. La part de victoire
**stricte** vaut `(1 - P(ex aequo)) / 3`, inconnue d'avance, et **ne peut donc pas servir de
seuil**. Un agent a `+0,05` de gain moyen n'est pas mediocre ; un agent a `0,05` de part de
victoire le serait.
"""

from __future__ import annotations

import argparse
import random
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean, pstdev
from time import perf_counter

from agents.politique import politique_greedy, politique_greedy_deterministe
from courtisans.engine import Engine
from mesure import comportements as comp
from mesure import dimensionnement as dim
from mesure.bootstrap import EffetDePlan, bootstrap_par_donne, correlation_intra_donne
from mesure.instance import ENTRAINEMENT_3J
from mesure.partie import politique_uniforme
from mesure.trace import TracePartie, tracer

CONFIG = ENTRAINEMENT_3J

#: Les seeds, ecrits une fois. Paragraphe 9 de la pre-inscription.
DEPART_A = 0
DEPART_A_CONTROLE = 10_000
DEPART_B = 0
DECALAGE_POLITIQUE_A = 2_000_000
DECALAGE_BOOTSTRAP = 2_500_000
DECALAGE_POLITIQUE_B = 3_000_000
DECALAGE_DEPARTAGE_B = 3_500_000
DECALAGE_POLITIQUE_2_GREEDYS = 5_000_000

#: Rechantillons du bootstrap par donne.
REPETITIONS_BOOTSTRAP = 10_000


# ---------------------------------------------------------------------------------
# Les campagnes
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Groupe:
    """Les parties d'une meme donne. L'unite du bootstrap.

    Attributes:
        seed: la donne.
        traces: ses parties, une par replicat ou par assignation de siege.
        sieges_mesures: pour chaque trace, le siege dont on mesure le comportement. Pour la
            campagne A c'est **tous** les sieges ; pour la campagne B, celui du greedy.
    """

    seed: int
    traces: tuple[TracePartie, ...]
    sieges_mesures: tuple[tuple[int, ...], ...]


def campagne_a(donnes: int, depart: int = DEPART_A, replicats: int = 6) -> list[Groupe]:
    """Trois aleatoires, `replicats` replicats de politique par donne.

    **L'appariement du protocole est vide ici** : permuter trois copies de la politique
    uniforme ne produit pas trois parties de lois differentes. Les replicats sont donc des
    tirages de politique independants sur la meme pioche -- ce qui EST le plan a 6 permutations
    quand les agents sont interchangeables, et ce qui donne un compte divisible par 6.
    """
    groupes: list[Groupe] = []
    tous = tuple(range(CONFIG.joueurs))
    for donne in range(depart, depart + donnes):
        traces = []
        for replicat in range(replicats):
            alea = random.Random(DECALAGE_POLITIQUE_A + replicats * donne + replicat)
            politiques = [politique_uniforme(alea) for _ in range(CONFIG.joueurs)]
            traces.append(
                tracer(
                    Engine(CONFIG).reset(donne), politiques, seed=donne, replicat=replicat
                )
            )
        groupes.append(
            Groupe(donne, tuple(traces), tuple(tous for _ in range(replicats)))
        )
    return groupes


def campagne_b(
    donnes: int,
    depart: int = DEPART_B,
    nb_greedys: int = 1,
    departage_deterministe: bool = False,
) -> list[Groupe]:
    """Un greedy contre deux aleatoires -- ou l'inverse --, les 3 assignations de siege.

    **L'appariement est reel ici**, et c'est la qu'il sert : rejouer chaque donne avec le
    greedy en siege 0, 1 puis 2 neutralise l'avantage de siege **par construction**, quel que
    soit cet avantage. C'est le plan applique inconditionnellement dans toutes les phases
    suivantes.

    Args:
        nb_greedys: 1 pour la composition de reference, 2 pour celle rapportee a cote. A 2, la
            variable permutee est le siege de l'**aleatoire**.
        departage_deterministe: la variante de robustesse du departage, biaisee, rapportee sur
            M3 seulement.

    Raises:
        ValueError: si `nb_greedys` n'est ni 1 ni 2. A 0 il n'y a pas de greedy a mesurer, a 3
            il n'y a plus d'aleatoire et la mesure n'a plus d'objet.
    """
    if nb_greedys not in (1, 2):
        raise ValueError(
            f"la composition mesuree oppose 1 ou 2 greedys a des aleatoires, "
            f"{nb_greedys} demande(s)"
        )
    decalage = DECALAGE_POLITIQUE_B if nb_greedys == 1 else DECALAGE_POLITIQUE_2_GREEDYS
    groupes: list[Groupe] = []
    for donne in range(depart, depart + donnes):
        traces = []
        mesures = []
        for variable in range(CONFIG.joueurs):
            alea = random.Random(decalage + CONFIG.joueurs * donne + variable)
            depart_alea = random.Random(
                DECALAGE_DEPARTAGE_B + CONFIG.joueurs * donne + variable
            )
            greedy = (
                politique_greedy_deterministe()
                if departage_deterministe
                else politique_greedy(depart_alea)
            )
            hasard = politique_uniforme(alea)
            if nb_greedys == 1:
                politiques = [hasard] * CONFIG.joueurs
                politiques[variable] = greedy
                sieges = (variable,)
            else:
                politiques = [greedy] * CONFIG.joueurs
                politiques[variable] = hasard
                sieges = tuple(s for s in range(CONFIG.joueurs) if s != variable)
            traces.append(
                tracer(
                    Engine(CONFIG).reset(donne), politiques, seed=donne, replicat=variable
                )
            )
            mesures.append(sieges)
        groupes.append(Groupe(donne, tuple(traces), tuple(mesures)))
    return groupes


# ---------------------------------------------------------------------------------
# Les deux statistiques de siege, et leurs niveaux neutres
# ---------------------------------------------------------------------------------


def part_de_victoire_fractionnee(scores: Sequence[int]) -> list[float]:
    """`1/k` pour chacun des `k` vainqueurs ex aequo, `0` sinon.

    **Somme a 1 exactement, a chaque partie** : c'est ce qui rend son niveau neutre exact et
    non estime. La part **stricte** ne somme pas a 1 -- elle vaut 0 partout sur une partie a
    ex aequo -- donc son attendu par siege est `(1 - P(ex aequo)) / 3`, inconnu avant mesure,
    et elle ne peut pas servir de seuil. Le seuil du protocole etant ecrit en parts de victoire,
    on y repond avec celle qui a un niveau neutre exact.
    """
    meilleur = max(scores)
    vainqueurs = sum(1 for score in scores if score == meilleur)
    return [1 / vainqueurs if score == meilleur else 0.0 for score in scores]


def part_de_victoire_stricte(scores: Sequence[int]) -> list[float]:
    """`1` pour un vainqueur unique, `0` sinon. Rapportee, jamais comparee a `1/3`."""
    meilleur = max(scores)
    unique = sum(1 for score in scores if score == meilleur) == 1
    return [1.0 if unique and score == meilleur else 0.0 for score in scores]


def _par_donne(groupes: Sequence[Groupe], valeur) -> list[list[float]]:
    """Les valeurs d'une statistique, regroupees par donne -- l'unite du bootstrap."""
    return [[valeur(trace) for trace in groupe.traces] for groupe in groupes]


# ---------------------------------------------------------------------------------
# M1 -- avantage de siege
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultatSiege:
    """Ce qu'un siege a obtenu, sur les deux statistiques et leurs deux niveaux neutres."""

    siege: int
    gain: EffetDePlan
    part_fractionnee: EffetDePlan
    part_stricte: float


def mesurer_m1(groupes: Sequence[Groupe], alea: random.Random) -> list[ResultatSiege]:
    """Le gain moyen et la part de victoire de chaque siege, avec bootstrap par donne."""
    resultats = []
    for siege in range(CONFIG.joueurs):
        gains = _par_donne(groupes, lambda t, s=siege: t.gains[s])
        parts = _par_donne(
            groupes, lambda t, s=siege: part_de_victoire_fractionnee(t.scores)[s]
        )
        strictes = [
            part_de_victoire_stricte(trace.scores)[siege]
            for groupe in groupes
            for trace in groupe.traces
        ]
        resultats.append(
            ResultatSiege(
                siege=siege,
                gain=bootstrap_par_donne(
                gains, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
            ),
                part_fractionnee=bootstrap_par_donne(
                    parts, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
                ),
                part_stricte=fmean(strictes),
            )
        )
    return resultats


# ---------------------------------------------------------------------------------
# M2 -- variance du score final
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultatVariance:
    """La dispersion du score et du gain, et la correlation intra-donne qui dimensionne."""

    ecarts_types_score: tuple[float, ...]
    ecart_type_score_global: float
    ecart_type_gain: float
    correlation_score: tuple[float | None, ...]
    correlation_gain: tuple[float | None, ...]
    valeurs_distinctes: tuple[int, ...]
    part_modale: tuple[float, ...]
    trois_ex_aequo: float
    nb_parties: int


def mesurer_m2(groupes: Sequence[Groupe]) -> ResultatVariance:
    """La variance, la correlation intra-donne, et les criteres de la phase 1 pour comparaison."""
    traces = [trace for groupe in groupes for trace in groupe.traces]
    scores_par_siege = [[trace.scores[s] for trace in traces] for s in range(CONFIG.joueurs)]
    tous_scores = [score for colonne in scores_par_siege for score in colonne]
    tous_gains = [gain for trace in traces for gain in trace.gains]
    trois = sum(1 for trace in traces if len(set(trace.scores)) == 1) / len(traces)
    modales = []
    for colonne in scores_par_siege:
        comptes = {valeur: colonne.count(valeur) for valeur in set(colonne)}
        modales.append(max(comptes.values()) / len(colonne))
    return ResultatVariance(
        ecarts_types_score=tuple(pstdev(colonne) for colonne in scores_par_siege),
        ecart_type_score_global=pstdev(tous_scores),
        ecart_type_gain=pstdev(tous_gains),
        correlation_score=tuple(
            correlation_intra_donne(_par_donne(groupes, lambda t, s=siege: float(t.scores[s])))
            for siege in range(CONFIG.joueurs)
        ),
        correlation_gain=tuple(
            correlation_intra_donne(_par_donne(groupes, lambda t, s=siege: t.gains[s]))
            for siege in range(CONFIG.joueurs)
        ),
        valeurs_distinctes=tuple(len(set(colonne)) for colonne in scores_par_siege),
        part_modale=tuple(modales),
        trois_ex_aequo=trois,
        nb_parties=len(traces),
    )


def tableau_de_dimensionnement(
    ecart_type_gain: float, correlation: float, ecarts: Sequence[float]
) -> list[tuple[float, int, int]]:
    """Pour chaque ecart de gain moyen, les parties necessaires, apparie et non apparie.

    Rend `(ecart, sans appariement, avec appariement)`. Le produit livre de M2 : c'est ce
    tableau que les phases suivantes consommeront, pas l'ecart-type lui-meme.
    """
    lignes = []
    borne = max(0.0, min(correlation, 0.999))
    for ecart in ecarts:
        sans = dim.parties_pour_contraste_apparie(
            ecart, ecart_type_gain, 0.0, dim.RISQUE, dim.PUISSANCE
        )
        avec = dim.parties_pour_contraste_apparie(
            ecart, ecart_type_gain, borne, dim.RISQUE, dim.PUISSANCE
        )
        lignes.append((ecart, sans, avec))
    return lignes


def ecart_detectable(ecart_type_gain: float, correlation: float, nb_parties: int) -> float:
    """L'ecart de gain moyen detectable a `nb_parties` parties appariees, 99 % et 80 %.

    Sert a repondre a une question du protocole : son seuil de phase 3 -- « > 55 % contre le
    greedy sur 1 000 parties appariees » -- est-il atteignable a ce budget ?
    """
    borne = max(0.0, min(correlation, 0.999))
    z = dim.quantile_bilateral(dim.RISQUE) + dim.quantile_de_puissance(dim.PUISSANCE)
    return z * ecart_type_gain * (2 * (1 - borne)) ** 0.5 / nb_parties**0.5


# ---------------------------------------------------------------------------------
# M3 -- winrate du greedy
# ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultatGreedy:
    """Ce que le greedy obtient, sur les deux statistiques et leurs deux niveaux neutres."""

    intitule: str
    gain: EffetDePlan
    part_fractionnee: EffetDePlan
    part_stricte: float
    par_siege: tuple[float, ...]
    par_siege_bootstrap: tuple[EffetDePlan, ...]
    contraste_extremes: EffetDePlan | None
    nb_parties: int


def mesurer_m3(
    groupes: Sequence[Groupe], intitule: str, alea: random.Random
) -> ResultatGreedy:
    """Le gain moyen et la part de victoire des sieges mesures, apparies par donne."""

    def moyenne_mesuree(trace: TracePartie, sieges: Sequence[int], valeurs) -> float:
        return fmean([valeurs(trace)[siege] for siege in sieges])

    gains = [
        [
            moyenne_mesuree(trace, sieges, lambda t: t.gains)
            for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True)
        ]
        for groupe in groupes
    ]
    parts = [
        [
            moyenne_mesuree(
                trace, sieges, lambda t: part_de_victoire_fractionnee(t.scores)
            )
            for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True)
        ]
        for groupe in groupes
    ]
    strictes = [
        moyenne_mesuree(trace, sieges, lambda t: part_de_victoire_stricte(t.scores))
        for groupe in groupes
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True)
    ]
    # L'effet de siege du greedy, par siege occupe. **Ce n'est pas M1** : M1 mesure le siege
    # sous jeu uniformement aleatoire, celui-ci sous jeu greedy. Rien ne dit d'avance que les
    # deux se ressemblent, et c'est precisement ce que l'appariement du plan neutralise sans
    # qu'on ait besoin de le connaitre.
    par_donne_par_siege: list[list[list[float]]] = [[] for _ in range(CONFIG.joueurs)]
    for groupe in groupes:
        occupees: list[list[float]] = [[] for _ in range(CONFIG.joueurs)]
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
            for siege in sieges:
                occupees[siege].append(trace.gains[siege])
        for siege in range(CONFIG.joueurs):
            if occupees[siege]:
                par_donne_par_siege[siege].append(occupees[siege])

    par_siege = []
    par_siege_bootstrap = []
    for siege in range(CONFIG.joueurs):
        observations = par_donne_par_siege[siege]
        plates = [valeur for groupe in observations for valeur in groupe]
        par_siege.append(fmean(plates) if plates else float("nan"))
        par_siege_bootstrap.append(
            bootstrap_par_donne(
                observations, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
            )
        )

    # Le contraste entre les deux sieges extremes, **apparie par donne** : chaque donne fournit
    # les deux, donc la difference ne contient plus la variance de distribution. C'est le seul
    # chiffre qui dise si l'ecart entre sieges est etabli, plutot que de laisser comparer deux
    # intervalles a la main.
    contraste = None
    if all(par_donne_par_siege):
        rang = sorted(range(CONFIG.joueurs), key=lambda siege: par_siege[siege])
        faible, fort = rang[0], rang[-1]
        differences = []
        for groupe in groupes:
            valeurs: dict[int, list[float]] = {faible: [], fort: []}
            for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
                for siege in (faible, fort):
                    if siege in sieges:
                        valeurs[siege].append(trace.gains[siege])
            if valeurs[faible] and valeurs[fort]:
                differences.append([fmean(valeurs[fort]) - fmean(valeurs[faible])])
        if differences:
            contraste = bootstrap_par_donne(
                differences, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
            )

    return ResultatGreedy(
        intitule=intitule,
        gain=bootstrap_par_donne(
            gains, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
        ),
        part_fractionnee=bootstrap_par_donne(
            parts, REPETITIONS_BOOTSTRAP, random.Random(alea.randrange(2**31))
        ),
        part_stricte=fmean(strictes),
        par_siege=tuple(par_siege),
        par_siege_bootstrap=tuple(par_siege_bootstrap),
        contraste_extremes=contraste,
        nb_parties=len(strictes),
    )


# ---------------------------------------------------------------------------------
# M4 -- B1 a B7
# ---------------------------------------------------------------------------------


def mesurer_m4(groupes: Sequence[Groupe]) -> dict[str, comp.Compte]:
    """Les sept compteurs sur les sieges mesures de ces groupes.

    Les traces sont regroupees par ensemble de sieges mesures : les compteurs prennent une
    liste de sieges commune, donc melanger des traces ou le greedy est en siege 0 et d'autres
    ou il est en siege 2 exigerait de les compter separement. On les additionne ensuite,
    denominateur compris.
    """
    par_sieges: dict[tuple[int, ...], list[TracePartie]] = {}
    for groupe in groupes:
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
            par_sieges.setdefault(sieges, []).append(trace)

    cumul: dict[str, comp.Compte] = {}
    for sieges, traces in par_sieges.items():
        partiel = comp.tous_les_comportements(traces, CONFIG, sieges=list(sieges))
        for nom, compte in partiel.items():
            if nom in cumul:
                ancien = cumul[nom]
                cumul[nom] = comp.Compte(
                    nom,
                    ancien.succes + compte.succes,
                    ancien.total + compte.total,
                    compte.grain,
                    compte.vue,
                )
            else:
                cumul[nom] = compte
    comp.verifier_b4(cumul)
    return cumul


def mesurer_b6(groupes: Sequence[Groupe]) -> dict[str, float | None]:
    """La distance de variation totale entre le tour 1 et le dernier, par groupe de categories."""
    par_sieges: dict[tuple[int, ...], list[TracePartie]] = {}
    for groupe in groupes:
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
            par_sieges.setdefault(sieges, []).append(trace)
    distributions: dict[tuple[str, int], dict[str, comp.Compte]] = {}
    for sieges, traces in par_sieges.items():
        partiel = comp.distributions_b6(traces, CONFIG, sieges=list(sieges))
        for cle, classes in partiel.items():
            if cle not in distributions:
                distributions[cle] = classes
                continue
            distributions[cle] = {
                categorie: comp.Compte(
                    compte.nom,
                    distributions[cle][categorie].succes + compte.succes,
                    distributions[cle][categorie].total + compte.total,
                    compte.grain,
                    compte.vue,
                )
                for categorie, compte in classes.items()
            }
    return {
        groupe: comp.distance_de_variation_totale(distributions, groupe, 1, CONFIG.tours)
        for groupe in comp.GROUPES_B6
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Joue les campagnes et ecrit le rapport sur la sortie standard."""
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--donnes-a", type=int, default=dim.DONNES_CAMPAGNE_A)
    analyseur.add_argument("--donnes-b", type=int, default=dim.DONNES_CAMPAGNE_B)
    analyseur.add_argument("--sans-variantes", action="store_true")
    arguments = analyseur.parse_args(argv)

    from mesure.rapport_phase2 import rapport

    debut = perf_counter()
    print(
        rapport(
            donnes_a=arguments.donnes_a,
            donnes_b=arguments.donnes_b,
            avec_variantes=not arguments.sans_variantes,
        )
    )
    print(f"\n<!-- duree totale : {perf_counter() - debut:.1f} s -->")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONFIG",
    "Groupe",
    "ResultatGreedy",
    "ResultatSiege",
    "ResultatVariance",
    "campagne_a",
    "campagne_b",
    "ecart_detectable",
    "main",
    "mesurer_b6",
    "mesurer_m1",
    "mesurer_m2",
    "mesurer_m3",
    "mesurer_m4",
    "part_de_victoire_fractionnee",
    "part_de_victoire_stricte",
    "tableau_de_dimensionnement",
]

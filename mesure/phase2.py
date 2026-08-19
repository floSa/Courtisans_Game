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
from mesure.binomiale import intervalle_clopper_pearson
from mesure.bootstrap import (
    EffetDePlan,
    bootstrap_par_donne,
    correlation_intra_donne,
)
from mesure.coherence_greedy import mesurer_incoherence
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
#: La composition a **trois** greedys, ajoutee apres l'audit croise. Elle ne sert qu'a M4, et
#: seulement la ou la configuration a deux hasards rend la ligne de base inadaptee a ce que la
#: phase 3 comparera -- `B1-collectif` et les lignes `-par-partie`.
DECALAGE_POLITIQUE_3_GREEDYS = 6_000_000

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
        nb_greedys: 1 pour la composition de reference, 2 pour celle rapportee a cote, 3 pour la
            population de M4 ajoutee apres l'audit croise. A 2, la variable permutee est le siege
            de l'**aleatoire** ; a 3 il n'y a plus de siege a permuter, et les trois parties d'une
            donne ne diffèrent que par l'alea de **departage** du greedy -- trois replicats sur la
            meme pioche, exactement la structure de la campagne A.
        departage_deterministe: la variante de robustesse du departage, biaisee, rapportee sur
            M3 seulement.

    Raises:
        ValueError: si `nb_greedys` n'est pas dans `1..3`. A 0 il n'y a pas de greedy a mesurer,
            au-dela de 3 il n'y a pas assez de sieges.

    **Cette garde a ete scindee, et c'etait un defaut a part entiere.** Elle refusait aussi
    `nb_greedys=3` en disant « la mesure n'a plus d'objet » : vrai de **M3**, ou trois greedys
    identiques rendent un tiers de part de victoire **par symetrie**, faux de **M4**, ou les
    compteurs de comportement gardent tout leur sens. Elle **confondait une mesure avec une
    phase**. Elle ne juge donc plus que la composition, et `mesurer_m3` refuse ce qui n'a pas
    d'objet pour lui.
    """
    if nb_greedys not in (1, 2, 3):
        raise ValueError(
            f"la composition mesuree compte 1 a 3 greedys, {nb_greedys} demande(s) : "
            f"a 0 il n'y a pas de greedy a mesurer, au-dela de 3 pas assez de sieges"
        )
    decalage = {
        1: DECALAGE_POLITIQUE_B,
        2: DECALAGE_POLITIQUE_2_GREEDYS,
        3: DECALAGE_POLITIQUE_3_GREEDYS,
    }[nb_greedys]
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
            elif nb_greedys == 2:
                politiques = [greedy] * CONFIG.joueurs
                politiques[variable] = hasard
                sieges = tuple(s for s in range(CONFIG.joueurs) if s != variable)
            else:
                # Trois greedys : plus rien a permuter. `variable` ne sert plus qu'a donner trois
                # aleas de departage differents sur la meme pioche -- trois replicats, comme la
                # campagne A. Les trois sieges sont mesures.
                politiques = [greedy] * CONFIG.joueurs
                sieges = tuple(range(CONFIG.joueurs))
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
    groupes: Sequence[Groupe], intitule: str, alea: random.Random, nb_greedys: int
) -> ResultatGreedy:
    """Le gain moyen et la part de victoire des sieges mesures, apparies par donne.

    `nb_greedys` est **obligatoire et sans defaut** : c'est la seule chose que `groupes` ne dit
    pas, et l'oublier ferait calculer M3 sur une population ou il n'a pas d'objet sans que la
    garde s'en apercoive -- exactement le mode de defaut silencieux que ce projet cherche a
    fermer.

    Raises:
        ValueError: a `nb_greedys=3`. Trois politiques identiques rendent, **par symetrie**, un
            tiers de part de victoire et un gain moyen nul : le chiffre existerait, il ne
            mesurerait rien. C'est la moitie « M3 » de la garde qui etait melangee dans
            `campagne_b`.
    """
    if nb_greedys == 3:
        raise ValueError(
            "M3 n'a pas d'objet a trois greedys : trois politiques identiques rendent un tiers "
            "de part de victoire et un gain moyen nul **par symetrie**, donc le chiffre "
            "existerait sans rien mesurer. Cette population ne sert qu'a M4."
        )

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
# Le pouvoir discriminant d'un compteur -- la vraie livrable de M4 pour la phase 3
# ---------------------------------------------------------------------------------


def ecart_de_taux_detectable(
    taux: float,
    par_partie: float,
    nb_parties: int,
    risque: float = dim.RISQUE,
    puissance: float = dim.PUISSANCE,
) -> float | None:
    """L'ecart de taux detectable entre deux agents, chacun mesure sur `nb_parties` parties.

    Un compteur de comportement n'a de valeur pour la phase 3 que s'il peut **separer** deux
    agents au budget qu'elle se donne. Trois fois dans ce projet un critere a constate au lieu
    de tester : les quatre criteres de non-degenerescence de la phase 1, le seuil de 38 % de M1,
    et B7 ici. Ce chiffre est ce qui l'empeche une quatrieme fois.

    Args:
        taux: le taux de reference -- celui du greedy, la ligne de base a battre.
        par_partie: le denominateur **par partie** du compteur. `12` pour une pose au banquet
            tous sieges confondus, `4` pour le seul siege mesure, `0,0122` pour une occasion de
            B7... C'est lui qui fait qu'un compteur d'action discrimine et qu'un compteur
            d'occasion rare ne discrimine pas.
        nb_parties: le budget, en parties, de **chacun** des deux agents compares.

    Rend `None` dans deux cas, et les deux sont des resultats :

      - le denominateur attendu est inferieur a 1 : sur un compteur aussi rare, l'ecart
        detectable n'est pas un grand nombre, il **n'existe pas** ;
      - le taux vaut **exactement 0 ou 1**. La variance binomiale y est nulle, donc la formule
        normale rendrait un ecart detectable de zero -- « tout est detectable » -- ce qui est
        exactement faux. Un zero observe se traite par sa **borne exacte**, que rend
        `borne_exacte_d_un_taux_nul`.
    """
    effectif = nb_parties * par_partie
    if effectif < 1:
        return None
    if taux <= 0.0 or taux >= 1.0:
        return None
    erreur = (2 * taux * (1 - taux) / effectif) ** 0.5
    return (dim.quantile_bilateral(risque) + dim.quantile_de_puissance(puissance)) * erreur


def borne_exacte_d_un_taux_nul(
    par_partie: float, nb_parties: int, risque: float = dim.RISQUE
) -> float | None:
    """La borne haute exacte d'un taux observe **nul**, au budget donne.

    Un compteur a 0 sur `n` observations n'a pas d'ecart detectable au sens normal : sa variance
    estimee est nulle. Ce qu'on peut dire est **jusqu'ou** le vrai taux pourrait monter sans
    qu'on l'ait vu -- la borne haute de Clopper-Pearson pour `k = 0`, exacte et sans hypothese
    de normalite.

    Lecture pour la phase 3 : un agent dont ce compteur depasse cette borne est **separable** du
    greedy ; en dessous, il ne l'est pas. C'est la seule facon de donner un pouvoir discriminant
    a un zero, et le seul moyen d'empecher qu'on lise « le greedy ne le fait jamais » comme
    « aucun agent ne peut faire mieux ».

    Rend `None` si le budget ne produit aucune observation.
    """
    effectif = int(nb_parties * par_partie)
    if effectif < 1:
        return None
    return intervalle_clopper_pearson(0, effectif, risque)[1]


def parties_pour_separer_un_taux(
    taux: float,
    par_partie: float,
    ecart: float,
    risque: float = dim.RISQUE,
    puissance: float = dim.PUISSANCE,
) -> int | None:
    """Les parties necessaires pour separer un ecart de `ecart` sur un compteur de ce taux.

    L'inverse de `ecart_de_taux_detectable`. Rend `None` si `ecart` est nul ou si le compteur
    n'a aucun denominateur -- aucun nombre de parties n'etablit un ecart nul.
    """
    if ecart <= 0 or par_partie <= 0 or taux <= 0.0 or taux >= 1.0:
        # A taux nul ou unitaire la variance estimee est nulle : la formule rendrait « 0 partie
        # suffit », ce qui est le contraire de la verite. Voir `borne_exacte_d_un_taux_nul`.
        return None
    z = dim.quantile_bilateral(risque) + dim.quantile_de_puissance(puissance)
    effectif = (z / ecart) ** 2 * 2 * taux * (1 - taux)
    return int(-(-(effectif / par_partie) // 1))


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
            # `comp.cumuler` **leve** si deux compositions de sieges n'agregent pas le meme
            # nombre de sieges : additionner leurs numerateurs en ne gardant qu'un libelle
            # etait exactement la forme du defaut du paragraphe 6.
            cumul[nom] = comp.cumuler(cumul[nom], compte) if nom in cumul else compte
    comp.verifier_b4(cumul)
    return cumul


def distributions_b6(
    groupes: Sequence[Groupe],
) -> dict[tuple[str, int], dict[str, comp.Compte]]:
    """Les distributions de B6, par groupe et par tour, agregees sur toutes les campagnes.

    Extraite pour que les **deux** definitions de B6 -- celle retenue et sa concurrente -- se
    calculent sur la meme agregation. La recopier ferait deux endroits ou se tromper de siege
    mesure.
    """
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
    return distributions


def mesurer_incoherence_du_greedy(groupes: Sequence[Groupe]) -> dict[str, comp.Compte]:
    """L'incoherence du ciblage du greedy, agregee par composition de sieges mesures.

    **Defaut majeur de l'audit croise, mesure et non corrige.** Voir
    `mesure/coherence_greedy.py` pour ce qui est mesure et `agents/greedy.py` pour la
    description corrigee de l'agent.

    Calcule sur les traces **deja en memoire** : ce diagnostic ne rejoue aucune campagne.
    """
    cumul: dict[str, comp.Compte] = {}
    for groupe in groupes:
        for trace, sieges in zip(groupe.traces, groupe.sieges_mesures, strict=True):
            partiel = mesurer_incoherence([trace], CONFIG, sieges=list(sieges))
            for nom, compte in partiel.items():
                cumul[nom] = comp.cumuler(cumul[nom], compte) if nom in cumul else compte
    return cumul


def mesurer_b6(groupes: Sequence[Groupe]) -> dict[str, float | None]:
    """La distance de variation totale entre le tour 1 et le dernier, par groupe de categories."""
    distributions = distributions_b6(groupes)
    return {
        groupe: comp.distance_de_variation_totale(distributions, groupe, 1, CONFIG.tours)
        for groupe in comp.GROUPES_B6
    }


def mesurer_b6_concurrente(groupes: Sequence[Groupe]) -> dict[str, float | None]:
    """**B6-dernier-contre-reste** : le dernier tour contre tous les precedents agreges.

    La concurrente pre-inscrite au paragraphe 6.6. Son terme de comparaison porte trois fois
    plus de nœuds, donc elle est plus stable -- et elle melange trois etats de plateau, donc
    elle dilue l'ecart. Publiee a cote de la retenue, jamais a sa place.
    """
    distributions = distributions_b6(groupes)
    premiers = tuple(range(1, CONFIG.tours))
    return {
        groupe: comp.distance_dernier_contre_reste(
            distributions, groupe, CONFIG.tours, premiers
        )
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
    "borne_exacte_d_un_taux_nul",
    "campagne_a",
    "campagne_b",
    "ecart_de_taux_detectable",
    "parties_pour_separer_un_taux",
    "ecart_detectable",
    "main",
    "distributions_b6",
    "mesurer_b6",
    "mesurer_b6_concurrente",
    "mesurer_incoherence_du_greedy",
    "mesurer_m1",
    "mesurer_m2",
    "mesurer_m3",
    "mesurer_m4",
    "part_de_victoire_fractionnee",
    "part_de_victoire_stricte",
    "tableau_de_dimensionnement",
]

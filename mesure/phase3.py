"""L'instrument de la phase 3 : dimensionner AVANT d'entrainer, et sur SA composition.

Ce module ne mesure pas un agent. Il mesure le **terrain sur lequel un agent sera juge**,
pour repondre a l'etape 4 de la boucle du paragraphe 2 du protocole : *la mesure peut-elle
trancher dans le budget ?*

Pourquoi le depot ne contient pas deja ces chiffres
----------------------------------------------------
La phase 2 a publie `sigma(gain) = 0,6652` et `rho = +0,0066` -- **sous jeu uniformement
aleatoire**, campagne A, ou l'alea de la politique domine tout. Le protocole en tirait un
ecart de gain detectable de `+0,1013` a 1 000 parties appariees.

**Rien ne dit que ces valeurs tiennent sous « un agent contre deux greedys »**, et le depot
ne contient aucune mesure de `sigma` ni de `rho` sur une population de greedys -- verifie.
Les emprunter serait la faute que ce projet paie depuis trois phases : un chiffre exact sur
une population que la phrase ne nomme pas.

La composition mesuree, et pourquoi son niveau nul est EXACT
--------------------------------------------------------------
**Un agent contre deux greedys, sieges permutes systematiquement.** Chaque donne est jouee
`joueurs` fois : l'agent occupe le siege 0, puis 1, puis 2, sur la **meme pioche**. La donne
est l'unite du bootstrap.

Ce plan a une propriete que ni le protocole ni la phase 2 n'ecrivent, et qui est la raison
pour laquelle il faut le tenir : **sous l'hypothese nulle, l'ESPERANCE du gain mesure vaut
exactement 0,0000.**

La demonstration, et il faut la lire jusqu'au bout parce qu'une version plus courte en est
fausse. Notons `mu_s` l'esperance du gain du siege `s` dans cette composition. La somme nulle
du paragraphe 5.2, tenue par l'invariant I5, donne `mu_0 + mu_1 + mu_2 = 0` **exactement** --
c'est vrai partie par partie, donc en esperance. Sous l'hypothese nulle, l'agent est la meme
politique que ses deux adversaires : l'esperance de **son** gain quand il occupe le siege `s`
est donc `mu_s`, et pas autre chose. Le plan lui fait occuper chaque siege **exactement une
fois par donne**, donc l'esperance de la moyenne mesuree vaut `(mu_0 + mu_1 + mu_2) / 3 = 0`.

**Ce qui n'est PAS vrai, et qu'une premiere redaction de ce module affirmait.** La moyenne
*realisee* sur une donne ne vaut pas 0. Les trois traces d'une donne sont **trois parties
differentes** -- meme pioche, mais aleas de politique distincts --, et non une seule partie
lue trois fois : sommer le gain de l'agent sur ces trois traces n'est **pas** sommer les trois
sieges d'une partie. L'invariant I5 s'applique aux trois sieges d'**une** partie, pas aux
trois parties d'une donne. La confusion est exactement celle que ce projet a payee trois fois
-- un enonce exact sur une population que sa phrase ne nomme pas --, et elle a ete ecrite ici
avant d'etre relue.

**Ce que l'esperance exacte apporte quand meme, et c'est beaucoup.** Le niveau nul du seuil
n'est **pas estime** : il n'y a pas de population de reference a mesurer a cote, pas de second
echantillon, pas de soustraction entre deux grains -- la faute bloquante du tour 1 de la
phase 2 n'a pas de prise ici, par construction du plan. Et le **desequilibre** des sieges est
ce qui la detruirait : les gains par siege du greedy valent 0,697 / 0,812 / 0,886, donc un
plan qui ne donnerait pas chaque siege exactement une fois deplacerait le niveau nul de
l'ordre du dixieme de point de gain -- soit l'ordre de grandeur de l'effet cherche. **La
permutation n'est pas une precaution de forme : elle est ce qui fait exister le seuil.**

Ce que ce module mesure donc, et sur quoi
------------------------------------------
L'echantillon de dimensionnement est **le greedy mis a la place de l'agent** :
`trois greedys`, un seul siege compte, celui qui tourne. C'est la population de l'hypothese
nulle, et c'est celle qui dimensionne un test.

  - `sigma(gain)` du siege mesure, sur cette population ;
  - `rho`, correlation intra-donne entre les trois assignations de siege ;
  - l'effet de plan `1 + (m - 1) rho` avec `m = joueurs`, et le `n` effectif ;
  - l'ecart de gain detectable a un budget donne, et le budget pour un ecart donne ;
  - **la calibration** : l'IC 99 % de cette meme mesure doit contenir 0,0000. S'il ne le
    contient pas, c'est l'instrument qui est faux, pas l'agent -- et il faut s'arreter la.

Ce que `sigma` mesure ici est SUPPOSE valoir sous l'agent
-----------------------------------------------------------
`sigma` est mesure sous l'hypothese nulle. Un agent reellement meilleur a une distribution de
gain differente, donc un `sigma` different. C'est SUPPOSE, ce n'est pas mesure, et ca se
remesure sur la campagne finale -- `mesurer_composition` rend `sigma` a chaque fois, pour que
l'ecart entre le suppose et le mesure soit un chiffre et non un oubli.
"""

from __future__ import annotations

import random
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import fmean, pstdev

from agents.politique import Politique, politique_greedy
from courtisans.engine import Engine, State
from mesure import bootstrap as boot
from mesure import dimensionnement as dim
from mesure.instance import ENTRAINEMENT_3J
from mesure.partie import politique_uniforme
from mesure.phase2 import part_de_victoire_fractionnee, part_de_victoire_stricte
from mesure.trace import TracePartie, tracer

CONFIG = ENTRAINEMENT_3J

#: Une fabrique de politique : elle recoit son propre aleatoire et rend une `Politique`.
#: Le passer plutot qu'une `Politique` toute faite permet a chaque partie d'avoir son alea,
#: sans qu'aucun appelant ait a le savoir.
Fabrique = Callable[[random.Random], Politique]

# ---------------------------------------------------------------------------------
# Les decalages de graine. Disjoints de ceux de la phase 2 -- 2000000, 2500000, 3000000,
# 4000000, 5000000, 6000000 -- pour qu'aucune partie de la phase 3 ne soit une partie de
# la phase 2 rejouee sous un autre nom.
# ---------------------------------------------------------------------------------

#: Les donnes de la phase 3. Disjointes de celles de la phase 2 (0 a 3333 et 10000 a 11666)
#: pour que le dimensionnement ne se fasse pas sur les donnes qui ont produit la ligne de base.
DEPART_DONNE = 20_000

#: Alea de departage du greedy.
DECALAGE_DEPARTAGE = 7_000_000

#: Alea de la politique uniforme, pour la composition du garde-fou.
DECALAGE_UNIFORME = 7_500_000

#: Alea propre a l'agent mesure, s'il en a besoin.
DECALAGE_AGENT = 8_000_000

#: Bootstrap. Meme nombre de rechantillons qu'en phase 2, pour que les intervalles des deux
#: phases soient produits par le meme grain de calcul.
RECHANTILLONS = 10_000
GRAINE_BOOTSTRAP = 8_500_000


@dataclass(frozen=True)
class Campagne:
    """Les parties d'une composition, groupees par donne -- l'unite du bootstrap.

    Attributes:
        intitule: la composition, en toutes lettres. **Elle est portee par la donnee**, pas
            par le commentaire du site d'appel : un resultat qui ne nomme pas sa composition
            n'est pas auditable, et c'est la faute la plus frequente du projet.
        donnes: les seeds de donne, dans l'ordre.
        traces: pour chaque donne, une trace par assignation de siege.
        sieges_mesures: pour chaque donne, le siege occupe par l'agent dans chaque trace.
    """

    intitule: str
    donnes: tuple[int, ...]
    traces: tuple[tuple[TracePartie, ...], ...]
    sieges_mesures: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        if not (len(self.donnes) == len(self.traces) == len(self.sieges_mesures)):
            raise ValueError(
                f"campagne incoherente : {len(self.donnes)} donnes, "
                f"{len(self.traces)} groupes de traces, "
                f"{len(self.sieges_mesures)} groupes de sieges"
            )
        tailles = {len(groupe) for groupe in self.traces}
        if len(tailles) > 1:
            raise ValueError(
                f"les donnes n'ont pas toutes le meme nombre de parties : {sorted(tailles)}. "
                f"Le rapport intraclasse et le bootstrap par donne supposent un plan "
                f"equilibre ; sur un plan desequilibre ils rendent un nombre sans le signaler."
            )

    @property
    def nb_parties(self) -> int:
        return sum(len(groupe) for groupe in self.traces)

    @property
    def replicats_par_donne(self) -> int:
        """`m`, le nombre de parties par donne. C'est le `m` de l'effet de plan."""
        return len(self.traces[0]) if self.traces else 0

    def gains_par_donne(self) -> list[list[float]]:
        """Le gain de l'agent, groupe par donne. L'entree du bootstrap et de `rho`."""
        return [
            [trace.gains[siege] for trace, siege in zip(groupe, sieges, strict=True)]
            for groupe, sieges in zip(self.traces, self.sieges_mesures, strict=True)
        ]

    def parts_fractionnees_par_donne(self) -> list[list[float]]:
        """La part de victoire fractionnee de l'agent, groupee par donne."""
        return [
            [
                part_de_victoire_fractionnee(trace.scores)[siege]
                for trace, siege in zip(groupe, sieges, strict=True)
            ]
            for groupe, sieges in zip(self.traces, self.sieges_mesures, strict=True)
        ]

    def parts_strictes_par_donne(self) -> list[list[float]]:
        """La part de victoire **stricte**. Rapportee, jamais un seuil : son niveau nul vaut
        `(1 - P(trois ex aequo)) / 3` et depend de la frequence des ex aequo."""
        return [
            [
                part_de_victoire_stricte(trace.scores)[siege]
                for trace, siege in zip(groupe, sieges, strict=True)
            ]
            for groupe, sieges in zip(self.traces, self.sieges_mesures, strict=True)
        ]

    def gains_par_siege(self) -> dict[int, list[float]]:
        """Le gain de l'agent, ventile par siege occupe.

        **A publier a cote de la moyenne, jamais a sa place.** L'avantage de siege est massif
        sous jeu greedy -- 0,697 / 0,812 / 0,886 en phase 2 --, donc un chiffre par siege ne se
        compare jamais a un chiffre agrege sur trois.
        """
        par_siege: dict[int, list[float]] = {s: [] for s in range(CONFIG.joueurs)}
        for groupe, sieges in zip(self.traces, self.sieges_mesures, strict=True):
            for trace, siege in zip(groupe, sieges, strict=True):
                par_siege[siege].append(trace.gains[siege])
        return par_siege


def jouer_composition(
    agent: Fabrique,
    adversaire: Fabrique,
    donnes: int,
    intitule: str,
    depart: int = DEPART_DONNE,
    decalage_agent: int = DECALAGE_AGENT,
    decalage_adversaire: int = DECALAGE_DEPARTAGE,
) -> Campagne:
    """Un agent contre deux copies de `adversaire`, les `joueurs` assignations de siege.

    **La permutation est inconditionnelle**, et pas parce qu'un seuil la declenche : elle est
    ce qui rend le niveau nul exact sous l'hypothese nulle, et ce qui empeche un chiffre d'un
    seul siege d'etre confronte a un chiffre agrege sur trois.

    Chaque trace d'une donne rejoue **la meme pioche** : `Engine(CONFIG).reset(donne)`. Seuls
    le siege de l'agent et les aleas de politique changent.

    Args:
        agent: la fabrique de la politique mesuree.
        adversaire: la fabrique des deux adversaires. Les deux recoivent des aleas
            **distincts** : deux copies d'une politique aleatoire partageant un generateur
            joueraient de facon correlee, ce qui n'est pas la composition annoncee.
        intitule: la composition en toutes lettres, recopiee dans le resultat.
    """
    if donnes < 1:
        raise ValueError(f"il faut au moins une donne, {donnes} demandee(s)")

    moteur = Engine(CONFIG)
    tous_donnes: list[int] = []
    toutes_traces: list[tuple[TracePartie, ...]] = []
    tous_sieges: list[tuple[int, ...]] = []

    for donne in range(depart, depart + donnes):
        traces: list[TracePartie] = []
        sieges: list[int] = []
        for siege in range(CONFIG.joueurs):
            politiques: list[Politique] = []
            for place in range(CONFIG.joueurs):
                if place == siege:
                    graine = decalage_agent + CONFIG.joueurs * donne + siege
                    politiques.append(agent(random.Random(graine)))
                else:
                    # Un alea par (donne, siege de l'agent, place) : deux adversaires ne
                    # partagent jamais de generateur.
                    graine = (
                        decalage_adversaire
                        + CONFIG.joueurs * CONFIG.joueurs * donne
                        + CONFIG.joueurs * siege
                        + place
                    )
                    politiques.append(adversaire(random.Random(graine)))
            traces.append(
                tracer(moteur.reset(donne), politiques, seed=donne, replicat=siege)
            )
            sieges.append(siege)
        tous_donnes.append(donne)
        toutes_traces.append(tuple(traces))
        tous_sieges.append(tuple(sieges))

    return Campagne(
        intitule=intitule,
        donnes=tuple(tous_donnes),
        traces=tuple(toutes_traces),
        sieges_mesures=tuple(tous_sieges),
    )


@dataclass(frozen=True)
class Dimensionnement:
    """Ce qu'une composition dit du budget necessaire pour y trancher.

    Attributes:
        intitule: la composition mesuree, en toutes lettres.
        nb_donnes: le nombre de donnes.
        nb_parties: le nombre de parties -- `nb_donnes x replicats`.
        replicats: `m`, parties par donne.
        sigma_gain: l'ecart-type du gain **par partie**, sur le siege mesure.
        rho: la correlation intra-donne du gain, ou `None` si elle n'est pas definie.
        effet_de_plan: `1 + (m - 1) rho`, le facteur qui multiplie la variance de la moyenne.
        gain: le bootstrap par donne du gain moyen.
    """

    intitule: str
    nb_donnes: int
    nb_parties: int
    replicats: int
    sigma_gain: float
    rho: float | None
    effet_de_plan: float | None
    gain: boot.EffetDePlan

    def ecart_detectable(self, nb_parties: int, puissance: float = 0.80) -> float:
        """L'ecart de gain moyen detectable a `nb_parties`, a 99 % bilateral.

        `(z_{1-a/2} + z_{puissance}) * sigma / sqrt(n_effectif)`, avec
        `n_effectif = nb_parties / effet_de_plan`. **L'effet de plan est applique**, la ou une
        formule iid le tairait -- c'est tout le contenu de la mesure de `rho`.
        """
        if nb_parties < 1:
            raise ValueError(f"il faut au moins une partie, {nb_parties} demandee(s)")
        effet = self.effet_de_plan if self.effet_de_plan is not None else 1.0
        n_effectif = nb_parties / effet
        quantile = dim.quantile_bilateral(0.01) + dim.quantile_de_puissance(puissance)
        return quantile * self.sigma_gain / (n_effectif**0.5)

    def parties_pour_ecart(self, ecart: float, puissance: float = 0.80) -> int:
        """Le nombre de parties pour etablir `ecart`, a 99 % bilateral et `puissance`.

        Rendu en **parties**, pas en donnes : c'est l'unite du protocole. Le nombre de donnes
        s'en deduit en divisant par `replicats`, et le module l'ecrit a cote plutot que de
        laisser le lecteur choisir son unite.
        """
        if ecart <= 0:
            raise ValueError(
                f"un ecart a etablir est strictement positif, {ecart} recu : un ecart nul "
                f"ou negatif demanderait une infinite de parties"
            )
        effet = self.effet_de_plan if self.effet_de_plan is not None else 1.0
        quantile = dim.quantile_bilateral(0.01) + dim.quantile_de_puissance(puissance)
        n_effectif = (quantile * self.sigma_gain / ecart) ** 2
        return max(1, int(-(-n_effectif * effet // 1)))

    def donnes_pour_ecart(self, ecart: float, puissance: float = 0.80) -> int:
        """Le meme budget, en **donnes** : `parties_pour_ecart` arrondi au plan complet.

        Un plan a `m` parties par donne ne se coupe pas au milieu d'une donne : le bootstrap
        par donne et le rapport intraclasse supposent tous deux un plan equilibre, et la garde
        de `Campagne` leve si ce n'est pas le cas.
        """
        parties = self.parties_pour_ecart(ecart, puissance)
        return max(1, -(-parties // self.replicats))


def dimensionner(campagne: Campagne) -> Dimensionnement:
    """Mesure `sigma`, `rho`, l'effet de plan et l'IC du gain sur une composition."""
    gains = campagne.gains_par_donne()
    plates = [valeur for groupe in gains for valeur in groupe]
    rho = boot.correlation_intra_donne(gains)
    replicats = campagne.replicats_par_donne
    effet = None if rho is None else 1.0 + (replicats - 1) * rho
    return Dimensionnement(
        intitule=campagne.intitule,
        nb_donnes=len(campagne.donnes),
        nb_parties=campagne.nb_parties,
        replicats=replicats,
        # `pstdev` et non `stdev` : c'est l'ecart-type de la population des parties jouees,
        # la meme convention que `sigma(gain) = 0,6652` de la phase 2.
        sigma_gain=pstdev(plates),
        rho=rho,
        effet_de_plan=effet,
        gain=boot.bootstrap_par_donne(
            gains, RECHANTILLONS, random.Random(GRAINE_BOOTSTRAP)
        ),
    )


@dataclass(frozen=True)
class Verdict:
    """Le juge de la phase 3, sur une composition nommee.

    Attributes:
        intitule: la composition, en toutes lettres.
        gain: le bootstrap par donne du gain moyen. Niveau nul **exact** : 0,0000.
        part_fractionnee: le bootstrap de la part de victoire fractionnee. Niveau nul
            **exact** : `1 / joueurs`.
        part_stricte: la part de victoire stricte, **rapportee et jamais un seuil**.
        gains_par_siege: le gain moyen sur chaque siege occupe. A cote, jamais a la place.
    """

    intitule: str
    gain: boot.EffetDePlan
    part_fractionnee: boot.EffetDePlan
    part_stricte: float
    gains_par_siege: dict[int, float]

    @property
    def bat_le_greedy(self) -> bool:
        """Le seuil du protocole : borne basse de l'IC 99 % **strictement** positive."""
        return self.gain.intervalle[0] > 0.0

    @property
    def part_neutre(self) -> float:
        """`1 / joueurs` -- 33,3333 % a trois joueurs, jamais 50 %."""
        return 1.0 / CONFIG.joueurs


def juger(campagne: Campagne) -> Verdict:
    """Applique le juge du paragraphe 3 du protocole a une campagne."""
    alea = random.Random(GRAINE_BOOTSTRAP)
    gains = campagne.gains_par_donne()
    fractionnees = campagne.parts_fractionnees_par_donne()
    strictes = campagne.parts_strictes_par_donne()
    return Verdict(
        intitule=campagne.intitule,
        gain=boot.bootstrap_par_donne(gains, RECHANTILLONS, alea),
        part_fractionnee=boot.bootstrap_par_donne(
            fractionnees, RECHANTILLONS, random.Random(GRAINE_BOOTSTRAP + 1)
        ),
        part_stricte=fmean(v for groupe in strictes for v in groupe),
        gains_par_siege={
            siege: fmean(valeurs) if valeurs else 0.0
            for siege, valeurs in campagne.gains_par_siege().items()
        },
    )


# ---------------------------------------------------------------------------------
# Les deux fabriques de reference
# ---------------------------------------------------------------------------------


def greedy_de_reference(alea: random.Random) -> Politique:
    """Le greedy de `agents/greedy.py`, **inchange**. La ligne de base de toutes les phases."""
    return politique_greedy(alea)


def uniforme(alea: random.Random) -> Politique:
    """La politique uniformement aleatoire. Elle sert au garde-fou, et **n'entraine rien**."""
    return politique_uniforme(alea)


def collision_de_tenseurs(campagne: Campagne) -> tuple[int, int, int]:
    """Deux nœuds de meme tenseur ont-ils la meme chaine ? Rend (nœuds, tenseurs, collisions).

    **Le controle que le reseau partage exige, et que le depot n'a pas.** L'observation est
    relative a l'observateur -- `infoset._relatif`, « 0 c'est moi, 1 le suivant » --, donc un
    reseau unique partage par les trois sieges est la symetrie correcte du probleme. Mais si
    deux nœuds a des positions differentes dans l'ordre du tour partageaient un tenseur, ce
    reseau serait **plafonne par construction** et rien ne le dirait.

    La preuve exhaustive d'injectivite existe pour l'ancienne instance combo, **pas** pour
    `entrainement-3j` : ceci est un ECHANTILLON, et il se rapporte comme tel.

    `chaine` est la serialisation **sans perte** des memes blocs que `tenseur` : deux nœuds de
    meme tenseur et de chaines differentes sont une collision reelle de l'encodage numerique.
    """
    from courtisans.infoset import chaine as chaine_de
    from courtisans.infoset import tenseur as tenseur_de

    vus: dict[tuple[float, ...], str] = {}
    noeuds = 0
    collisions = 0
    moteur = Engine(CONFIG)
    # **Toutes** les parties, pas une par donne : l'agent occupe un siege different dans
    # chacune, et c'est precisement entre sieges que la collision serait dangereuse.
    for groupe in campagne.traces:
        for trace in groupe:
            # La trace porte les actions, pas les etats : on rejoue la partie pour retrouver
            # chaque nœud. `trace.seed` plutot qu'un indice recalcule -- un `index()` sur une
            # liste de donnes rendrait la premiere occurrence, et se tromperait en silence si
            # une donne etait jouee deux fois.
            assert trace.seed is not None, "une partie mesuree porte toujours son seed"
            etat: State = moteur.reset(trace.seed)
            for decision in trace.decisions:
                joueur = etat.current_player()
                cle = tuple(tenseur_de(etat, joueur))
                texte = chaine_de(etat, joueur)
                noeuds += 1
                if cle in vus and vus[cle] != texte:
                    collisions += 1
                vus[cle] = texte
                etat.apply(decision.action)
    return noeuds, len(vus), collisions


# ---------------------------------------------------------------------------------
# Le point d'entree de la pre-inscription
# ---------------------------------------------------------------------------------


def _ligne(cle: str, valeur: str) -> str:
    return f"{cle:52s} {valeur}"


def main(argv: Sequence[str] | None = None) -> int:
    """Mesure `sigma`, `rho` et le budget sur la composition de la phase 3.

    **Aucun agent n'est mesure ici.** L'echantillon est le greedy mis a la place de l'agent :
    c'est la population de l'hypothese nulle, et c'est elle qui dimensionne un test.

    Reproduire :

        UV_LINK_MODE=copy uv run python -m mesure.phase3 --donnes 2000
    """
    import argparse

    analyseur = argparse.ArgumentParser(description="Dimensionnement de la phase 3")
    analyseur.add_argument("--donnes", type=int, default=2000)
    analyseur.add_argument("--budgets", type=int, nargs="+", default=[500, 1000, 3000, 6000])
    analyseur.add_argument("--ecarts", type=float, nargs="+", default=[0.02, 0.05, 0.10, 0.20])
    arguments = analyseur.parse_args(argv)

    sortie = getattr(sys.stdout, "reconfigure", None)
    if sortie is not None:
        sortie(encoding="utf-8")

    campagne = jouer_composition(
        agent=greedy_de_reference,
        adversaire=greedy_de_reference,
        donnes=arguments.donnes,
        intitule="1 greedy contre 2 greedys, sieges permutes (hypothese nulle)",
    )
    mesure = dimensionner(campagne)
    verdict = juger(campagne)

    print(f"# Composition : {campagne.intitule}")
    print(_ligne("donnes", f"{mesure.nb_donnes}"))
    print(_ligne("parties", f"{mesure.nb_parties}"))
    print(_ligne("parties par donne (m)", f"{mesure.replicats}"))
    print(_ligne("seeds de donne", f"{campagne.donnes[0]} a {campagne.donnes[-1]}"))
    print()
    print(_ligne("sigma(gain), siege mesure", f"{mesure.sigma_gain:.4f}"))
    rho_txt = f"{mesure.rho:+.4f}" if mesure.rho is not None else "non defini"
    print(_ligne("rho intra-donne (gain)", rho_txt))
    effet_txt = f"{mesure.effet_de_plan:.4f}" if mesure.effet_de_plan else "-"
    print(_ligne("effet de plan 1 + (m-1) rho", effet_txt))
    print(_ligne("effet de plan mesure par bootstrap", f"{mesure.gain.effet:.4f}"))
    print(_ligne("n effectif (bootstrap)", f"{mesure.gain.n_effectif:.0f}"))
    print()
    print("# Calibration -- l'IC 99 % doit contenir 0,0000, sinon l'instrument est faux")
    basse, haute = verdict.gain.intervalle
    print(_ligne("gain moyen", f"{verdict.gain.moyenne:+.4f}"))
    print(_ligne("IC 99 % bootstrap par donne", f"[{basse:+.4f} ; {haute:+.4f}]"))
    print(_ligne("contient 0,0000 ?", "OUI" if basse <= 0.0 <= haute else "NON -- ARRET"))
    part_txt = (
        f"{verdict.part_fractionnee.moyenne:.4%} "
        f"(neutre {verdict.part_neutre:.4%})"
    )
    print(_ligne("part de victoire fractionnee", part_txt))
    print(_ligne("part de victoire stricte", f"{verdict.part_stricte:.4%}"))
    for siege, gain in sorted(verdict.gains_par_siege.items()):
        print(_ligne(f"  gain moyen au siege {siege}", f"{gain:+.4f}"))
    print()
    print("# Budget -- ecart de gain detectable, 99 % bilateral, 80 % de puissance")
    for budget in arguments.budgets:
        print(_ligne(f"  a {budget} parties", f"{mesure.ecart_detectable(budget):+.4f}"))
    print()
    print("# Budget -- parties pour etablir un ecart donne")
    for ecart in arguments.ecarts:
        parties = mesure.parties_pour_ecart(ecart)
        donnes = mesure.donnes_pour_ecart(ecart)
        budget_txt = f"{parties} parties = {donnes} donnes x {mesure.replicats}"
        print(_ligne(f"  ecart {ecart:+.2f}", budget_txt))
    print()
    print("# Collision de tenseurs -- le controle qu'exige le reseau partage")
    noeuds, tenseurs, collisions = collision_de_tenseurs(campagne)
    print(_ligne("nœuds observes", f"{noeuds}"))
    print(_ligne("tenseurs distincts", f"{tenseurs}"))
    print(_ligne("collisions tenseur -> chaine", f"{collisions}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONFIG",
    "Campagne",
    "Dimensionnement",
    "Fabrique",
    "Verdict",
    "collision_de_tenseurs",
    "dimensionner",
    "greedy_de_reference",
    "jouer_composition",
    "juger",
    "main",
    "uniforme",
]

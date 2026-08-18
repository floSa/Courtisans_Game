"""La campagne de mesure de l'auditeur : N parties aleatoires, et tous les denominateurs.

Ce module ne reutilise pas une ligne de `mesure/`. Il produit les quatre statistiques
demandees par le paragraphe 3 de `05_protocole_experimental.md`, phase 1 -- duree,
distribution des scores finaux, frequence des retournements, frequence des situations ou
refuser de tuer est possible -- **et le denominateur de chacune**, parce qu'un taux sans
son denominateur ne peut pas etre audite.
"""

from __future__ import annotations

import statistics
import time
from collections import Counter
from dataclasses import dataclass, field

from audit.intervalle import par_quantile_beta
from audit.retournement import (
    ANNULATION,
    INVERSION,
    Partie,
    est_retournement,
    politique_aleatoire,
    rejoue,
)
from courtisans.cards import Role
from courtisans.config import GameConfig
from courtisans.engine import Engine

#: L'instance de la phase 1 : 4 familles, les 5 roles, 2 exemplaires, 3 joueurs.
#: L'alternative a 1 exemplaire (20 cartes) donne `20 // 9 = 2` tours et est **refusee a la
#: construction** par le plancher du paragraphe 8 -- ce n'est donc pas un arbitrage laisse
#: au constructeur, c'est la configuration qui le tranche. Verifie par un controle hostile.
INSTANCE_PHASE_1 = GameConfig(
    familles=4,
    roles=(Role.ASSASSIN, Role.GARDE, Role.NOBLE, Role.ESPION, Role.NEUTRE),
    exemplaires=2,
    joueurs=3,
)


@dataclass
class Campagne:
    """Le releve brut d'un bloc de parties. Aucun taux n'est stocke : ils se recalculent."""

    config: GameConfig
    seeds: range | list[int]
    parties: list[Partie] = field(default_factory=list)
    secondes: float = 0.0

    # -- Duree ---------------------------------------------------------------------

    @property
    def n(self) -> int:
        return len(self.parties)

    def tours_par_joueur(self) -> Counter:
        """Multi-ensemble des vecteurs de poses par joueur. Doit valoir un seul vecteur."""
        return Counter(tuple(p.poses_par_joueur) for p in self.parties)

    def decisions(self) -> list[int]:
        return [p.decisions for p in self.parties]

    # -- Scores --------------------------------------------------------------------

    def scores_a_plat(self) -> list[int]:
        return [s for p in self.parties for s in p.scores]

    def valeurs_de_score_distinctes(self) -> list[int]:
        return sorted(set(self.scores_a_plat()))

    def amplitude(self) -> int:
        scores = self.scores_a_plat()
        return max(scores) - min(scores)

    def parties_ex_aequo(self) -> int:
        return sum(1 for p in self.parties if len(set(p.scores)) < len(p.scores))

    def victoires_par_siege(self) -> list[int]:
        compte = [0] * self.config.joueurs
        for p in self.parties:
            meilleur = max(p.scores)
            for siege, score in enumerate(p.scores):
                if score == meilleur:
                    compte[siege] += 1
        return compte

    # -- Retournements -------------------------------------------------------------

    def parties_avec_retournement(self, grain: int | None = None) -> int:
        return sum(1 for p in self.parties if p.retournements(grain))

    def retournements_totaux(self, grain: int | None = None) -> int:
        return sum(len(p.retournements(grain)) for p in self.parties)

    def par_classe(self, grain: int | None = None) -> Counter:
        return Counter(t.classe for p in self.parties for t in p.retournements(grain))

    def etablissements(self, grain: int | None = None) -> int:
        return sum(
            1
            for p in self.parties
            for t in p.transitions
            if t.grain == grain and not est_retournement(t.classe)
        )

    def parties_avec_invisible(self) -> int:
        return sum(
            1 for p in self.parties if p.retournements_invisibles(self.config.joueurs)
        )

    def invisibles_totaux(self) -> int:
        return sum(
            len(p.retournements_invisibles(self.config.joueurs)) for p in self.parties
        )

    # -- Refus de tuer -------------------------------------------------------------

    def noeuds_de_ciblage(self) -> int:
        return sum(p.noeuds_de_ciblage for p in self.parties)

    def noeuds_avec_cible(self) -> int:
        return sum(p.noeuds_avec_cible for p in self.parties)

    def meurtres(self) -> int:
        return sum(p.meurtres for p in self.parties)

    def refus(self) -> int:
        return sum(p.refus for p in self.parties)

    def parties_avec_refus_possible(self) -> int:
        return sum(1 for p in self.parties if p.noeuds_avec_cible > 0)


def joue_campagne(config: GameConfig, seeds: range | list[int]) -> Campagne:
    """Joue un bloc de parties : la graine fixe la pioche **et** la politique.

    Meme graine, meme partie : c'est ce qui rend un bloc rejouable a l'identique. La
    politique tire sur un generateur derive (`graine + 10**9`) pour que l'ordre de pioche et
    les choix ne soient pas produits par le meme flux -- sinon deux parties de graines
    voisines partageraient une partie de leurs decisions.
    """
    engine = Engine(config)
    campagne = Campagne(config=config, seeds=seeds)
    depart = time.perf_counter()
    for seed in seeds:
        pioche = engine.pioche_depuis_seed(seed)
        campagne.parties.append(
            rejoue(engine, pioche, politique_aleatoire(seed + 10**9))
        )
    campagne.secondes = time.perf_counter() - depart
    return campagne


def rapport(campagne: Campagne, titre: str) -> str:
    """Le releve d'une campagne, chaque taux accompagne de son denominateur."""
    c, n = campagne, campagne.n
    lignes = [f"=== {titre} : {n} parties, instance {c.config.familles} familles / "
              f"{c.config.nb_roles} roles / {c.config.exemplaires} ex. / "
              f"{c.config.joueurs} joueurs ==="]

    lignes.append(f"  paquet {c.config.nb_cartes} cartes, tours/joueur {c.config.tours}, "
                  f"cartes jouees {c.config.cartes_jouees}, reste en pioche "
                  f"{c.config.reste_en_pioche}")
    lignes.append(f"  duree machine : {c.secondes:.2f} s pour {n} parties, soit "
                  f"{c.secondes / max(n, 1) * 1000:.3f} ms/partie")

    vecteurs = c.tours_par_joueur()
    lignes.append(f"  D1 tours egaux    : vecteurs de poses observes = {dict(vecteurs)}")
    decisions = c.decisions()
    lignes.append(f"     decisions/partie : min {min(decisions)} med "
                  f"{statistics.median(decisions):.1f} max {max(decisions)}")

    scores = c.scores_a_plat()
    distinctes = c.valeurs_de_score_distinctes()
    lignes.append(f"  D2 scores         : {len(scores)} scores ({n} x {c.config.joueurs}), "
                  f"{len(distinctes)} valeurs distinctes, "
                  f"min {min(scores)} max {max(scores)} amplitude {c.amplitude()}")
    lignes.append(f"     moyenne {statistics.mean(scores):+.4f} "
                  f"ecart-type {statistics.pstdev(scores):.4f} "
                  f"parties avec ex aequo {c.parties_ex_aequo()}/{n}")
    lignes.append(f"     valeurs : {distinctes}")
    lignes.append(f"     victoires (ex aequo comptes) par siege : {c.victoires_par_siege()}")

    verite = c.parties_avec_retournement(None)
    basse, haute = par_quantile_beta(verite, n)
    lignes.append(f"  D3 retournements  : {verite}/{n} parties avec >= 1 retournement en "
                  f"verite = {verite / n:.4f}  IC99 [{basse * 100:.2f} % ; "
                  f"{haute * 100:.2f} %]")
    lignes.append(f"     total {c.retournements_totaux(None)} retournements, dont "
                  f"annulations {c.par_classe(None)[ANNULATION]} / inversions "
                  f"{c.par_classe(None)[INVERSION]}")
    lignes.append(f"     non-vacuite : {c.etablissements(None)} etablissements en verite "
                  f"(exclus du compte, par definition)")
    for j in range(c.config.joueurs):
        vu = c.parties_avec_retournement(j)
        lignes.append(f"     vue J{j} : {vu}/{n} parties = {vu / n:.4f}, "
                      f"{c.retournements_totaux(j)} retournements")
    lignes.append(f"     invisibles des {c.config.joueurs} sieges : "
                  f"{c.invisibles_totaux()} evenements dans "
                  f"{c.parties_avec_invisible()}/{n} parties")

    noeuds, avec = c.noeuds_de_ciblage(), c.noeuds_avec_cible()
    lignes.append(f"  D4 refus de tuer  : {noeuds} noeuds de ciblage, {avec} avec >= 1 "
                  f"cible = {avec / max(noeuds, 1):.4f} des noeuds")
    lignes.append(f"     parties ou refuser est un choix reel : "
                  f"{c.parties_avec_refus_possible()}/{n} = "
                  f"{c.parties_avec_refus_possible() / n:.4f}")
    lignes.append(f"     politique aleatoire : {c.meurtres()} meurtres, {c.refus()} refus")
    return "\n".join(lignes)

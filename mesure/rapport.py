"""La mesure de la phase 1 : jouer N parties aleatoires et rendre les chiffres du go/no-go.

Usage :

    uv run python -m mesure.rapport                        # 1000 parties, seeds 0 a 999
    uv run python -m mesure.rapport --parties 100 --depart 0

Ce module **n'interprete rien** : il compte, et affiche la decomposition de chaque chiffre.
Les seuils qu'il rappelle sont ceux de `hypothese_et_instrument.md`, ecrits avant la mesure.

L'aleatoire de la donne et celui de la politique sont **deux generateurs distincts** :
`Engine.reset(seed)` pour la premiere, `Random(DECALAGE_POLITIQUE + seed)` pour la seconde.
Sans cette separation, on ne saurait pas laquelle des deux fait varier un chiffre.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, lgamma, log, log1p
from statistics import mean, median, pstdev
from time import perf_counter

from courtisans.cards import Role
from courtisans.config import GameConfig
from courtisans.engine import Engine
from mesure.partie import SUPPORTS, Grain, Partie, Vue, observer, politique_uniforme
from mesure.retournement import Retournements

#: L'instance mesuree : `entrainement-3j` du paragraphe 3 de la specification du moteur.
#: Elle n'est pas choisie ici, elle est fixee -- la variante a 20 cartes est refusee a la
#: construction par le plancher `tours >= 3` du paragraphe 8 des regles.
CONFIG = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)

#: Decalage entre le seed de la donne et celui de la politique, pour que les deux tirages
#: soient independants tout en restant reproductibles depuis le seul seed de partie.
DECALAGE_POLITIQUE = 1_000_000

#: Le seuil du go/no-go, paragraphe 3 de `05_protocole_experimental.md`.
SEUIL_RETOURNEMENT = 1 / 3

#: Les quatre seuils de « distribution non degeneree », proposes dans
#: `hypothese_et_instrument.md` avant la mesure.
SEUIL_ECART_TYPE = 1.0
SEUIL_VALEURS_DISTINCTES = 8
SEUIL_PART_MODALE = 0.50
SEUIL_PART_TRIPLE_EX_AEQUO = 0.50

DEFINITIONS = ("r0", "r1", "r2", "r3")


# ---------------------------------------------------------------------------------
# Intervalle de confiance exact -- Clopper-Pearson
# ---------------------------------------------------------------------------------


def _log_binomiale(n: int, k: int, p: float) -> float:
    """Log de `C(n, k) p^k (1-p)^(n-k)`, en passant par lgamma pour ne pas deborder."""
    return (
        lgamma(n + 1)
        - lgamma(k + 1)
        - lgamma(n - k + 1)
        + k * log(p)
        + (n - k) * log1p(-p)
    )


def _queue_superieure(k: int, n: int, p: float) -> float:
    """`P(X >= k)` pour `X ~ Binomiale(n, p)`."""
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0
    return sum(exp(_log_binomiale(n, i, p)) for i in range(k, n + 1))


def intervalle_clopper_pearson(k: int, n: int, alpha: float = 0.01) -> tuple[float, float]:
    """L'intervalle exact de Clopper-Pearson, a `1 - alpha`.

    Exact au sens ou il ne suppose pas la normalite : a 1 000 parties l'approximation
    normale serait suffisante, mais elle ne le serait plus sur les sous-populations.
    """
    if not 0 <= k <= n:
        raise ValueError(f"{k} succes sur {n} parties : impossible")
    # Borne basse : le `p` tel que `P(X >= k) = alpha/2`.
    # Borne haute : le `p` tel que `P(X <= k) = alpha/2`, ecrit `P(X >= k+1) = 1 - alpha/2`
    # pour que les deux fonctions soient croissantes en `p` et se cherchent pareil. Ecrire
    # la seconde sous la forme `1 - P(X >= k+1) - alpha/2` la rendrait decroissante, et la
    # bissection rendrait la mauvaise borne sans rien signaler.
    basse = 0.0 if k == 0 else _bissection(lambda p: _queue_superieure(k, n, p) - alpha / 2)
    haute = (
        1.0
        if k == n
        else _bissection(lambda p: _queue_superieure(k + 1, n, p) - (1.0 - alpha / 2))
    )
    return basse, haute


def _bissection(fonction, iterations: int = 200) -> float:
    """Le zero d'une fonction **croissante** sur [0, 1]."""
    basse, haute = 0.0, 1.0
    for _ in range(iterations):
        milieu = (basse + haute) / 2
        if fonction(milieu) < 0:
            basse = milieu
        else:
            haute = milieu
    return basse


# ---------------------------------------------------------------------------------
# La campagne
# ---------------------------------------------------------------------------------


def jouer_campagne(nb_parties: int, depart: int) -> list[Partie]:
    """Joue `nb_parties` parties aleatoires, seeds `depart` a `depart + nb_parties - 1`."""
    moteur = Engine(CONFIG)
    return [
        observer(
            moteur.reset(seed),
            politique_uniforme(random.Random(DECALAGE_POLITIQUE + seed)),
            seed=seed,
        )
        for seed in range(depart, depart + nb_parties)
    ]


@dataclass(frozen=True)
class Proportion:
    """Un compte, son effectif, et son intervalle exact."""

    succes: int
    total: int

    @property
    def valeur(self) -> float:
        return self.succes / self.total if self.total else 0.0

    @property
    def intervalle(self) -> tuple[float, float]:
        return intervalle_clopper_pearson(self.succes, self.total)

    def __str__(self) -> str:
        basse, haute = self.intervalle
        return (
            f"{self.valeur:7.2%}  ({self.succes} / {self.total}) "
            f"IC99 [{basse:.2%} ; {haute:.2%}]"
        )


def _titre(texte: str) -> str:
    return f"\n{texte}\n{'-' * len(texte)}"


def _decision(proportion: Proportion, seuil: float) -> str:
    """Ce que l'intervalle permet de conclure face a un seuil, sans le franchir de justesse."""
    basse, haute = proportion.intervalle
    if basse > seuil:
        return f"au-dessus du seuil de {seuil:.1%} (borne basse {basse:.2%})"
    if haute < seuil:
        return f"SOUS le seuil de {seuil:.1%} (borne haute {haute:.2%})"
    return f"INDECIS : l'intervalle [{basse:.2%} ; {haute:.2%}] contient le seuil {seuil:.1%}"


# ---------------------------------------------------------------------------------
# Les sections du rapport
# ---------------------------------------------------------------------------------


def section_instance(lignes: list[str]) -> None:
    lignes.append(_titre("1. L'INSTANCE MESUREE"))
    lignes.append(
        f"  familles={CONFIG.familles}  roles={CONFIG.nb_roles}  "
        f"exemplaires={CONFIG.exemplaires}  joueurs={CONFIG.joueurs}"
    )
    lignes.append(
        f"  paquet        : {CONFIG.familles} x {CONFIG.nb_roles} x {CONFIG.exemplaires} "
        f"= {CONFIG.nb_cartes} cartes"
    )
    lignes.append(
        f"  tours/joueur  : {CONFIG.nb_cartes} // (3 x {CONFIG.joueurs}) = {CONFIG.tours}"
    )
    lignes.append(
        f"  cartes jouees : 3 x {CONFIG.joueurs} x {CONFIG.tours} = {CONFIG.cartes_jouees}"
    )
    lignes.append(
        f"  non piochees  : {CONFIG.nb_cartes} - {CONFIG.cartes_jouees} "
        f"= {CONFIG.reste_en_pioche}"
    )
    lignes.append(f"  actions de pose : 6 x 2 x ({CONFIG.joueurs} - 1) = {CONFIG.actions_de_pose}")


def section_duree(lignes: list[str], parties: Sequence[Partie], duree_totale: float) -> None:
    lignes.append(_titre("2. DUREE ET LONGUEUR D'UNE PARTIE"))
    durees = [partie.duree_s for partie in parties]
    poses = [sum(partie.poses_par_joueur) for partie in parties]
    ciblages = [partie.noeuds_ciblage for partie in parties]
    lignes.append(f"  temps total du run          : {duree_totale:.2f} s")
    lignes.append(
        f"  temps par partie            : moyenne {mean(durees) * 1e3:.3f} ms, "
        f"mediane {median(durees) * 1e3:.3f} ms, max {max(durees) * 1e3:.3f} ms"
    )
    lignes.append(f"  parties par seconde         : {len(parties) / duree_totale:.0f}")
    lignes.append(
        f"  noeuds de pose par partie   : min {min(poses)}, max {max(poses)} "
        f"(attendu {CONFIG.cartes_jouees // 3} = {CONFIG.joueurs} joueurs x {CONFIG.tours} tours)"
    )
    lignes.append(
        f"  noeuds de ciblage par partie: moyenne {mean(ciblages):.2f}, "
        f"min {min(ciblages)}, max {max(ciblages)}"
    )
    decisions = [pose + ciblage for pose, ciblage in zip(poses, ciblages, strict=True)]
    lignes.append(f"  decisions par partie        : moyenne {mean(decisions):.2f}")


def section_tours(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("3. GO/NO-GO 1 -- LES TROIS JOUEURS JOUENT LE MEME NOMBRE DE TOURS"))
    egaux = sum(1 for partie in parties if len(set(partie.poses_par_joueur)) == 1)
    attendus = sum(
        1 for partie in parties if partie.poses_par_joueur == (CONFIG.tours,) * CONFIG.joueurs
    )
    reste = Counter(partie.cartes_non_piochees for partie in parties)
    lignes.append(f"  parties ou les 3 sieges jouent autant : {Proportion(egaux, len(parties))}")
    lignes.append(
        f"  parties ou chacun joue exactement {CONFIG.tours} tours : "
        f"{Proportion(attendus, len(parties))}"
    )
    lignes.append(f"  cartes restees en pioche             : {dict(reste)}")
    lignes.append(
        f"  distribution des tours par siege      : "
        f"{Counter(partie.poses_par_joueur for partie in parties)}"
    )


def section_scores(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("4. GO/NO-GO 2 -- LA DISTRIBUTION DES SCORES FINAUX"))
    total = len(parties)
    lignes.append("  Par siege :")
    lignes.append(
        "    siege   moyenne  ecart-type   min   max   valeurs   mode (part)     D1   D2   D3"
    )
    verdicts: list[bool] = []
    for siege in range(CONFIG.joueurs):
        scores = [partie.scores[siege] for partie in parties]
        comptes = Counter(scores)
        valeur_modale, effectif_modal = comptes.most_common(1)[0]
        ecart = pstdev(scores)
        distinctes = len(comptes)
        part_modale = effectif_modal / total
        d1, d2, d3 = (
            ecart >= SEUIL_ECART_TYPE,
            distinctes >= SEUIL_VALEURS_DISTINCTES,
            part_modale < SEUIL_PART_MODALE,
        )
        verdicts.extend([d1, d2, d3])
        lignes.append(
            f"    {siege:^5d} {mean(scores):8.3f} {ecart:11.3f} {min(scores):5d} "
            f"{max(scores):5d} {distinctes:9d}   {valeur_modale:3d} ({part_modale:5.1%})  "
            f"{'ok' if d1 else 'NON':>4} {'ok' if d2 else 'NON':>4} {'ok' if d3 else 'NON':>4}"
        )

    tous = [score for partie in parties for score in partie.scores]
    lignes.append(
        f"  Tous sieges confondus : {len(tous)} scores, moyenne {mean(tous):.3f}, "
        f"ecart-type {pstdev(tous):.3f}, etendue [{min(tous)}, {max(tous)}]"
    )
    lignes.append("  Histogramme des scores (tous sieges) :")
    comptes = Counter(tous)
    for valeur in sorted(comptes):
        part = comptes[valeur] / len(tous)
        barre = "#" * int(part * 200)
        lignes.append(f"    {valeur:4d} : {comptes[valeur]:5d}  {part:6.2%}  {barre}")

    vainqueurs = Counter(
        sum(1 for score in partie.scores if score == max(partie.scores)) for partie in parties
    )
    triple = Proportion(vainqueurs.get(CONFIG.joueurs, 0), total)
    lignes.append(
        f"  Vainqueur unique : {Proportion(vainqueurs.get(1, 0), total)}"
    )
    lignes.append(f"  Deux ex aequo    : {Proportion(vainqueurs.get(2, 0), total)}")
    lignes.append(f"  Trois ex aequo   : {triple}")
    d4 = triple.valeur < SEUIL_PART_TRIPLE_EX_AEQUO
    verdicts.append(d4)
    lignes.append(
        f"  D4 (trois ex aequo < {SEUIL_PART_TRIPLE_EX_AEQUO:.0%}) : {'ok' if d4 else 'NON'}"
    )
    lignes.append(
        f"  => distribution non degeneree : {'OUI' if all(verdicts) else 'NON'} "
        f"({sum(verdicts)}/{len(verdicts)} criteres satisfaits)"
    )

    somme_nulle = sum(1 for partie in parties if abs(sum(partie.gains)) < 1e-9)
    lignes.append(f"  Controle somme nulle des gains : {Proportion(somme_nulle, total)}")


def section_retournements(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("5. GO/NO-GO 3 -- LES RETOURNEMENTS"))
    total = len(parties)
    lignes.append("  Proportion de parties ou AU MOINS UNE famille satisfait la definition :")
    lignes.append("    support                R0        R1        R2        R3")
    for grain, vue in SUPPORTS:
        cellules = []
        for definition in DEFINITIONS:
            succes = sum(
                1
                for partie in parties
                if getattr(partie.retournements(grain, vue), definition)
            )
            cellules.append(f"{succes / total:8.2%}")
        lignes.append(f"    {grain.value:4s} / {vue.value:9s} {'  '.join(cellules)}")

    lignes.append("")
    lignes.append(
        f"  Le go/no-go porte sur R2, grain tour, vue vraie. Seuil {SEUIL_RETOURNEMENT:.1%}."
    )
    for grain in Grain:
        succes = sum(1 for partie in parties if partie.retournements(grain, Vue.VRAIE).r2)
        proportion = Proportion(succes, total)
        lignes.append(f"    R2 grain {grain.value:4s} vue vraie : {proportion}")
        lignes.append(f"      -> {_decision(proportion, SEUIL_RETOURNEMENT)}")

    lignes.append("")
    lignes.append("  Nombre de familles retournees par partie (R2, grain tour, vue vraie) :")
    comptes = Counter(
        sum(
            1
            for retournement in partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE)
            if retournement.r2
        )
        for partie in parties
    )
    for nb in sorted(comptes):
        lignes.append(f"    {nb} famille(s) : {comptes[nb]:5d}  {comptes[nb] / total:6.2%}")
    moyenne = sum(nb * effectif for nb, effectif in comptes.items()) / total
    lignes.append(f"    moyenne : {moyenne:.3f} famille(s) sur {CONFIG.familles}")

    lignes.append("")
    lignes.append("  Par famille, toutes parties confondues (les familles sont interchangeables,")
    lignes.append("  invariant I11 : ces quatre chiffres doivent etre proches) :")
    for famille in range(CONFIG.familles):
        succes = sum(
            1
            for partie in parties
            if partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE)[famille].r2
        )
        lignes.append(f"    famille {famille} : {Proportion(succes, total)}")


def section_espions(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("6. LA PART QUE PERSONNE NE VOIT -- CONTRIBUTION DES ESPIONS"))
    total = len(parties)
    for grain in Grain:
        vrai = [partie.retournements(grain, Vue.VRAIE).r2 for partie in parties]
        public = [partie.retournements(grain, Vue.PUBLIQUE).r2 for partie in parties]
        vrai_seul = sum(1 for v, p in zip(vrai, public, strict=True) if v and not p)
        public_seul = sum(1 for v, p in zip(vrai, public, strict=True) if p and not v)
        lignes.append(f"  grain {grain.value} :")
        lignes.append(f"    R2 vrai                        : {Proportion(sum(vrai), total)}")
        lignes.append(f"    R2 public                      : {Proportion(sum(public), total)}")
        lignes.append(f"    vrai sans public (invisible)   : {Proportion(vrai_seul, total)}")
        lignes.append(f"    public sans vrai (illusoire)   : {Proportion(public_seul, total)}")

    familles_vrai = sum(
        1
        for partie in parties
        for retournement in partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE)
        if retournement.r2
    )
    familles_public = sum(
        1
        for partie in parties
        for retournement in partie.retournements_par_famille(Grain.TOUR, Vue.PUBLIQUE)
        if retournement.r2
    )
    lignes.append(
        f"  familles retournees (R2, grain tour) : {familles_vrai} en vue vraie, "
        f"{familles_public} en vue publique, ecart {familles_vrai - familles_public}"
    )


def section_refus(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("7. OU REFUSER DE TUER EST POSSIBLE"))
    total = len(parties)
    noeuds = sum(partie.noeuds_ciblage for partie in parties)
    avec_cible = sum(partie.noeuds_avec_cible for partie in parties)
    lignes.append(f"  noeuds de ciblage, toutes parties : {noeuds}")
    lignes.append(
        f"  dont au moins une cible valide    : {Proportion(avec_cible, noeuds)}"
    )
    lignes.append(
        f"  parties avec au moins un tel noeud : "
        f"{Proportion(sum(1 for p in parties if p.noeuds_avec_cible >= 1), total)}"
    )
    lignes.append(
        f"  noeuds a choix par partie          : moyenne "
        f"{mean(partie.noeuds_avec_cible for partie in parties):.2f}, "
        f"max {max(partie.noeuds_avec_cible for partie in parties)}"
    )
    cibles = Counter(
        nb for partie in parties for nb in partie.cibles_par_noeud
    )
    lignes.append("  distribution du nombre de cibles valides par noeud :")
    for nb in sorted(cibles):
        lignes.append(f"    {nb:2d} cible(s) : {cibles[nb]:6d}  {cibles[nb] / noeuds:6.2%}")
    morts = [partie.morts for partie in parties]
    lignes.append(
        f"  cartes tuees par partie : moyenne {mean(morts):.2f}, min {min(morts)}, "
        f"max {max(morts)} -- politique uniforme, donc refus tire au hasard"
    )


def section_controles(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("8. CONTROLES DU COMPTEUR LUI-MEME"))
    violations = 0
    temoins_r1_sans_r3 = 0
    temoins_r3_sans_r1 = 0
    for partie in parties:
        for support in SUPPORTS:
            for retournement in partie.retournements_par_famille(*support):
                if (retournement.r1 and not retournement.r2) or (
                    retournement.r3 and not retournement.r2
                ):
                    violations += 1
                if retournement.r2 and not retournement.r0:
                    violations += 1
                if retournement.r1 and not retournement.r3:
                    temoins_r1_sans_r3 += 1
                if retournement.r3 and not retournement.r1:
                    temoins_r3_sans_r1 += 1
    lignes.append(f"  violations des inclusions R1 ⊆ R2, R3 ⊆ R2, R2 ⊆ R0 : {violations}")
    lignes.append(
        f"  familles R1 sans R3 : {temoins_r1_sans_r3}   |   R3 sans R1 : {temoins_r3_sans_r1}"
    )
    lignes.append("    (les deux non nuls confirment que R1 et R3 ne sont pas ordonnees)")
    longueurs = Counter(
        len(suite) for partie in parties for suite in partie.suites[Grain.TOUR, Vue.VRAIE]
    )
    lignes.append(f"  longueurs des suites au grain tour : {dict(longueurs)}")
    lignes.append(
        f"    (attendu {CONFIG.joueurs * CONFIG.tours + 1} = 1 statut initial + "
        f"{CONFIG.joueurs * CONFIG.tours} tours)"
    )


def rapport(parties: Sequence[Partie], duree_totale: float) -> str:
    """Le rapport complet, en texte."""
    lignes: list[str] = []
    lignes.append("=" * 92)
    lignes.append(f"PHASE 1 -- MESURE DE L'INSTANCE entrainement-3j -- {len(parties)} PARTIES")
    seeds = [partie.seed for partie in parties]
    lignes.append(
        f"donne : Engine.reset(seed), seeds {seeds[0]} a {seeds[-1]}  |  "
        f"politique : uniforme, Random({DECALAGE_POLITIQUE} + seed)"
    )
    lignes.append("=" * 92)
    section_instance(lignes)
    section_duree(lignes, parties, duree_totale)
    section_tours(lignes, parties)
    section_scores(lignes, parties)
    section_retournements(lignes, parties)
    section_espions(lignes, parties)
    section_refus(lignes, parties)
    section_controles(lignes, parties)
    lignes.append("")
    return "\n".join(lignes)


def main(argv: Sequence[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--parties", type=int, default=1000, help="nombre de parties")
    analyseur.add_argument("--depart", type=int, default=0, help="premier seed")
    arguments = analyseur.parse_args(argv)

    debut = perf_counter()
    parties = jouer_campagne(arguments.parties, arguments.depart)
    duree = perf_counter() - debut
    print(rapport(parties, duree))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CONFIG",
    "Proportion",
    "Retournements",
    "intervalle_clopper_pearson",
    "jouer_campagne",
    "main",
    "rapport",
]

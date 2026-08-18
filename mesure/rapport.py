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
from math import factorial
from statistics import mean, median, pstdev
from time import perf_counter

from courtisans.cards import Position
from courtisans.config import CARTES_PAR_TOUR
from courtisans.engine import Engine
from mesure.binomiale import intervalle_clopper_pearson
from mesure.instance import ENTRAINEMENT_3J
from mesure.partie import (
    Grain,
    Partie,
    Vue,
    compter_invisible,
    observer,
    politique_uniforme,
    supports,
    vues,
)
from mesure.retournement import Retournements

#: L'instance mesuree. Definie dans `mesure/instance.py`, et nulle part ailleurs.
CONFIG = ENTRAINEMENT_3J

#: Les facteurs de l'espace d'actions de pose (paragraphe 3.2 des regles) : les `3!`
#: assignations des trois cartes aux trois zones, et le choix Estime / Disgrace. Lus dans le
#: moteur, jamais ecrits en dur : une decomposition dont un facteur est un litteral cesse
#: d'etre juste des que la configuration change, sans que rien ne le signale.
ASSIGNATIONS = factorial(CARTES_PAR_TOUR)
POSITIONS = len(Position)

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
        f"  tours/joueur  : {CONFIG.nb_cartes} // ({CARTES_PAR_TOUR} x {CONFIG.joueurs}) "
        f"= {CONFIG.tours}"
    )
    lignes.append(
        f"  cartes jouees : {CARTES_PAR_TOUR} x {CONFIG.joueurs} x {CONFIG.tours} "
        f"= {CONFIG.cartes_jouees}"
    )
    lignes.append(
        f"  non piochees  : {CONFIG.nb_cartes} - {CONFIG.cartes_jouees} "
        f"= {CONFIG.reste_en_pioche}"
    )
    lignes.append(
        f"  actions de pose : {ASSIGNATIONS} x {POSITIONS} x ({CONFIG.joueurs} - 1) "
        f"= {CONFIG.actions_de_pose}"
    )


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
        f"(attendu {CONFIG.cartes_jouees // CARTES_PAR_TOUR} = {CONFIG.joueurs} joueurs "
        f"x {CONFIG.tours} tours)"
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


def _pouvoir_discriminant(
    parties: Sequence[Partie],
) -> list[tuple[str, int, bool]]:
    """Pour chaque critere, la premiere taille d'echantillon qui le satisfait.

    Un seuil franchi par une poignee de parties ne separe rien : il decrit une propriete
    que presque toute instance non triviale aurait. Le rapport doit le dire lui-meme,
    plutot que de presenter les quatre criteres comme s'ils pesaient pareil.

    Rend, par critere : son nom, la plus petite taille de prefixe qui le satisfait, et si
    tous les prefixes plus grands le satisfont aussi.
    """
    criteres = {
        "D1 ecart-type >= 1        ": lambda scores: all(
            pstdev(colonne) >= SEUIL_ECART_TYPE for colonne in scores
        ),
        "D2 >= 8 valeurs distinctes": lambda scores: all(
            len(set(colonne)) >= SEUIL_VALEURS_DISTINCTES for colonne in scores
        ),
        "D3 mode < 50 %            ": lambda scores: all(
            Counter(colonne).most_common(1)[0][1] / len(colonne) < SEUIL_PART_MODALE
            for colonne in scores
        ),
        "D4 trois ex aequo < 50 %  ": lambda scores: sum(
            1 for tirage in zip(*scores, strict=True) if len(set(tirage)) == 1
        )
        / len(scores[0])
        < SEUIL_PART_TRIPLE_EX_AEQUO,
    }
    resultats = []
    for nom, satisfait in criteres.items():
        premier, stable = 0, True
        for taille in range(1, len(parties) + 1):
            colonnes = [
                [partie.scores[siege] for partie in parties[:taille]]
                for siege in range(CONFIG.joueurs)
            ]
            vrai = satisfait(colonnes)
            if vrai and premier == 0:
                premier = taille
            elif not vrai and premier:
                stable = False
        resultats.append((nom, premier, stable))
    return resultats


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

    lignes.append("")
    lignes.append("  Pouvoir discriminant de chaque critere -- a partir de combien de parties")
    lignes.append("  est-il deja satisfait, et le reste-t-il jusqu'a la fin de la campagne ?")
    lignes.append("  Un critere satisfait des la douzieme partie ne discrimine rien a 1 000 :")
    lignes.append("  il constate, il ne teste pas. Releve par l'audit croise sur D2.")
    for nom, premier, stable in _pouvoir_discriminant(parties):
        verdict = "discrimine peu" if premier <= 50 else "discrimine"
        constance = "puis toujours vrai" if stable else "puis a nouveau faux ensuite"
        lignes.append(
            f"    {nom} : satisfait des {premier} partie(s), {constance} -- {verdict}"
        )


def section_retournements(lignes: list[str], parties: Sequence[Partie]) -> None:
    lignes.append(_titre("5. GO/NO-GO 3 -- LES RETOURNEMENTS"))
    total = len(parties)
    lignes.append("  Proportion de parties ou AU MOINS UNE famille satisfait la definition :")
    lignes.append("    support                R0        R1        R2        R3")
    for grain, vue in supports(CONFIG.joueurs):
        cellules = []
        for definition in DEFINITIONS:
            succes = sum(
                1
                for partie in parties
                if getattr(partie.retournements(grain, vue), definition)
            )
            cellules.append(f"{succes / total:8.2%}")
        lignes.append(f"    {grain.value:4s} / {vue.nom:9s} {'  '.join(cellules)}")

    lignes.append("")
    lignes.append("  Parties ou les deux grains ne disent PAS la meme chose (vue vraie) :")
    for definition in DEFINITIONS:
        desaccords = sum(
            1
            for partie in parties
            if getattr(partie.retournements(Grain.FIN, Vue.VRAIE), definition)
            != getattr(partie.retournements(Grain.TOUR, Vue.VRAIE), definition)
        )
        lignes.append(f"    {definition.upper()} : {desaccords:4d} / {total}")
    lignes.append("    (un desaccord est un transitoire intra-tour : le grain fin le voit,")
    lignes.append("     le grain tour ne le voit pas)")

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
    lignes.append(_titre("6. CE QUE LES ESPIONS CACHENT -- QUI VOIT LE RETOURNEMENT"))
    lignes.append("  La vue publique est le savoir COMMUN : elle n'est la vue de personne,")
    lignes.append("  puisque chaque joueur y ajoute ses propres Espions. Les vues par siege")
    lignes.append("  sont donc necessaires pour dire ce que « invisible » veut dire.")
    lignes.append("")
    lignes.append("  RIEN N'EST AGREGE ICI. La premiere version de cette section comparait")
    lignes.append("  `retournements(...)`, deja un OU sur les quatre familles, puis un `any`")
    lignes.append("  sur les trois sieges : la conjonction « vrai oui, aucun siege » etait")
    lignes.append("  alors quasi impossible par construction, et le 0 qu'elle affichait ne")
    lignes.append("  mesurait pas ce que sa phrase annoncait. Defaut bloquant de l'audit")
    lignes.append("  croise. On compte desormais par famille, et par evenement.")

    total = len(parties)
    familles = CONFIG.familles

    lignes.append("")
    lignes.append("  Rappel non comparable, une ligne par vue -- parties ayant au moins une")
    lignes.append("  famille en R2, grain tour (ces cinq nombres ne se soustraient PAS) :")
    for vue in vues(CONFIG.joueurs):
        succes = sum(1 for partie in parties if partie.retournements(Grain.TOUR, vue).r2)
        lignes.append(f"    vue {vue.nom:10s} : {Proportion(succes, total)}")

    comptage = compter_invisible(parties, CONFIG.joueurs, familles)
    familles_vues = total * familles

    lignes.append("")
    lignes.append(
        f"  NIVEAU FAMILLE -- denominateur {total} parties x {familles} familles "
        f"= {familles_vues} familles"
    )
    lignes.append(
        f"    familles en R2, vue vraie                  : {comptage.familles_r2} "
        f"/ {familles_vues}"
    )
    lignes.append(
        f"    dont AUCUN siege n'en voit rien            : "
        f"{Proportion(comptage.familles_invisibles, comptage.familles_r2)}"
    )
    lignes.append(
        f"    parties contenant une telle famille        : "
        f"{Proportion(comptage.parties_avec_famille_invisible, total)}"
    )

    lignes.append("")
    lignes.append(
        f"  NIVEAU EVENEMENT -- une perte d'acquis datee, denominateur {comptage.evenements}"
    )
    lignes.append(
        f"    vues par AUCUN siege au meme instant       : "
        f"{Proportion(comptage.evenements_invisibles, comptage.evenements)}"
    )
    lignes.append(
        f"    parties contenant une telle perte          : "
        f"{Proportion(comptage.parties_avec_evenement_invisible, total)}"
    )
    lignes.append("      (un siege peut voir la famille bouger sans voir CETTE perte-la :")
    lignes.append("       le niveau famille est donc plus indulgent que le niveau evenement)")


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
        for support in supports(CONFIG.joueurs):
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
    # Sortie en ASCII pur : la console Windows encode en cp1252, ou le signe d'inclusion
    # fait lever l'ecriture du rapport entier.
    nb_supports = len(supports(CONFIG.joueurs))
    couples = len(parties) * nb_supports * CONFIG.familles
    lignes.append(
        f"  denominateur de cette section : {len(parties)} parties x {nb_supports} supports "
        f"({len(Grain)} grains x {len(vues(CONFIG.joueurs))} vues) x {CONFIG.familles} familles "
        f"= {couples} couples famille x support"
    )
    lignes.append(
        f"  violations des inclusions R1 dans R2, R3 dans R2, R2 dans R0 : {violations} "
        f"/ {couples}"
    )
    lignes.append(
        f"  familles R1 sans R3 : {temoins_r1_sans_r3} / {couples}   |   "
        f"R3 sans R1 : {temoins_r3_sans_r1} / {couples}"
    )

    # Le chiffre ci-dessus additionne dix supports, dont les cinq vues d'une meme partie :
    # il compte donc plusieurs fois la meme famille. Celui-ci porte sur le seul support de
    # reference, ou une famille n'est comptee qu'une fois.
    r1_sans_r3 = r3_sans_r1 = 0
    for partie in parties:
        for retournement in partie.retournements_par_famille(Grain.TOUR, Vue.VRAIE):
            r1_sans_r3 += retournement.r1 and not retournement.r3
            r3_sans_r1 += retournement.r3 and not retournement.r1
    familles_uniques = len(parties) * CONFIG.familles
    lignes.append(
        f"  sur le seul support de reference (grain tour, vue vraie), "
        f"{familles_uniques} familles :"
    )
    lignes.append(
        f"    R1 sans R3 : {r1_sans_r3} / {familles_uniques}   |   "
        f"R3 sans R1 : {r3_sans_r1} / {familles_uniques}"
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

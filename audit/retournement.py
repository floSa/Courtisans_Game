"""Le compteur de retournements de l'auditeur, et le rejeu d'une partie.

Ma definition, ecrite avant d'avoir lu celle du constructeur :

> Pour une famille, `d` est reevalue apres **chaque evenement capable de le faire bouger**
> -- une pose au banquet, ou un meurtre au banquet. Un **retournement** est un changement
> de statut **dont le statut de depart n'est pas Indifferente** :
>   - *annulation* : Lumiere -> Indifferente, ou Obscurite -> Indifferente ;
>   - *inversion*  : Lumiere -> Obscurite, ou Obscurite -> Lumiere.
> Le passage Indifferente -> Lumiere/Obscurite est un **etablissement**, pas un
> retournement : le compter viderait la metrique, puisque la premiere carte de banquet de
> n'importe quelle famille le declenche.

Pourquoi la reevaluation apres chaque `apply` donne le bon grain d'evenement : une action
de pose place trois cartes d'un bloc, dont **exactement une** au banquet (paragraphe 3.2),
puis chaque Assassin pose ouvre son propre noeud, qui tue au plus une carte. Un `apply` ne
peut donc bouger `d` que d'une seule carte, et aucune transition ne peut etre sautee.

Le retournement est compte dans quatre grains simultanement : la verite, et la vue de
chacun des trois sieges. C'est la verite qui decide les points ; les vues disent si un
joueur pouvait **voir** l'evenement, ce qui n'est pas la meme question.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from audit.statut import INDIFFERENTE, NOM_STATUT, influence_par_famille, points_par_joueur
from courtisans.cards import Carte
from courtisans.engine import Engine, Phase, State

ETABLISSEMENT = "etablissement"
ANNULATION = "annulation"
INVERSION = "inversion"


def classe_transition(statut_avant: int, statut_apres: int) -> str | None:
    """Nomme une transition de statut, ou `None` si le statut n'a pas change.

    `etablissement` quand on part d'Indifferente -- ce n'est **pas** un retournement.
    `annulation` quand on arrive a Indifferente en venant d'ailleurs. `inversion` quand on
    passe de Lumiere a Obscurite ou l'inverse.
    """
    if statut_avant == statut_apres:
        return None
    if statut_avant == INDIFFERENTE:
        return ETABLISSEMENT
    if statut_apres == INDIFFERENTE:
        return ANNULATION
    return INVERSION


def est_retournement(classe: str | None) -> bool:
    """Un retournement est une annulation ou une inversion, jamais un etablissement."""
    return classe in (ANNULATION, INVERSION)


@dataclass(frozen=True)
class Transition:
    """Un changement de statut d'une famille, dans un grain, a un evenement donne."""

    evenement: int
    grain: int | None  # None = verite, sinon le siege qui observe
    famille: int
    d_avant: int
    d_apres: int
    statut_avant: int
    statut_apres: int
    classe: str
    cause: str = "pose"  # "pose" ou "meurtre" -- les deux leviers du paragraphe 2.2

    def __str__(self) -> str:
        grain = "verite" if self.grain is None else f"vue J{self.grain}"
        return (
            f"ev{self.evenement:02d} {grain:8s} f{self.famille} {self.cause:8s} "
            f"d {self.d_avant:+d} -> {self.d_apres:+d} : "
            f"{NOM_STATUT[self.statut_avant]} -> {NOM_STATUT[self.statut_apres]} "
            f"[{self.classe}]"
        )


@dataclass
class Partie:
    """Tout ce qu'une partie rejouee a produit, et rien de plus.

    `transitions` contient les changements de statut de **tous** les grains ; les
    retournements s'en deduisent par `est_retournement`.
    """

    transitions: list[Transition] = field(default_factory=list)
    poses_par_joueur: list[int] = field(default_factory=list)
    noeuds_de_ciblage: int = 0
    noeuds_avec_cible: int = 0
    meurtres: int = 0
    refus: int = 0
    refus_possibles: int = 0
    decisions: int = 0
    scores: list[int] = field(default_factory=list)
    gains: list[float] = field(default_factory=list)

    def retournements(self, grain: int | None = None) -> list[Transition]:
        """Les retournements du grain demande. `None` = la verite."""
        return [
            t
            for t in self.transitions
            if t.grain == grain and est_retournement(t.classe)
        ]

    def retournements_invisibles(self, joueurs: int) -> list[Transition]:
        """Les retournements en verite qu'**aucun** des sieges ne voit comme retournement.

        Un siege « voit » l'evenement s'il compte lui aussi un retournement sur la meme
        famille au meme evenement. La comparaison porte sur (evenement, famille), pas sur
        les statuts : un siege qui verrait un retournement different sur la meme famille
        au meme instant a bien vu qu'il se passait quelque chose.
        """
        vus = {
            (t.evenement, t.famille)
            for t in self.transitions
            if t.grain is not None and est_retournement(t.classe)
        }
        return [t for t in self.retournements(None) if (t.evenement, t.famille) not in vus]


def politique_aleatoire(graine: int) -> Callable[[State], int]:
    """Une politique uniforme sur les actions legales, avec son propre generateur.

    Un generateur dedie par partie : deux parties jouees dans le meme processus ne doivent
    pas s'influencer, et la partie doit etre rejouable a l'identique depuis sa graine.
    """
    tirage = random.Random(graine)

    def choisir(etat: State) -> int:
        return tirage.choice(etat.legal_actions())

    return choisir


def rejoue(
    engine: Engine,
    pioche: Sequence[Carte],
    politique: Callable[[State], int],
) -> Partie:
    """Joue une partie entiere et releve tout ce qui est mesurable.

    Le statut de chaque famille est recalcule, dans les quatre grains, **avant et apres
    chaque action**. Rien n'est lu du moteur qui ressemble a un statut : seule
    `vue_privilegiee().posees` est utilisee, c'est-a-dire la liste brute des cartes
    vivantes sur la table.
    """
    config = engine.config
    etat = engine.reset_depuis_pioche(pioche)
    partie = Partie(poses_par_joueur=[0] * config.joueurs)
    grains: list[int | None] = [None, *range(config.joueurs)]
    evenement = 0

    def influences() -> dict[int | None, dict[int, int]]:
        vivantes = etat.vue_privilegiee().posees
        return {
            grain: influence_par_famille(vivantes, config.familles, grain)
            for grain in grains
        }

    from audit.statut import statut_de

    while not etat.is_terminal():
        if etat.phase() is Phase.CHANCE:  # pragma: no cover - pioche fixee ici
            raise AssertionError("une pioche fixee ne doit pas ouvrir de noeud de chance")

        phase = etat.phase()
        joueur = etat.current_player()
        if phase is Phase.CIBLAGE:
            cibles = etat.cibles_courantes()
            partie.noeuds_de_ciblage += 1
            if cibles:
                partie.noeuds_avec_cible += 1
                partie.refus_possibles += 1

        avant = influences()
        action = politique(etat)
        partie.decisions += 1
        cause = "pose"
        if phase is Phase.POSE:
            partie.poses_par_joueur[joueur] += 1
        else:
            if action == len(etat.cibles_courantes()):
                partie.refus += 1
            else:
                partie.meurtres += 1
                cause = "meurtre"
        etat.apply(action)
        apres = influences()

        evenement += 1
        for grain in grains:
            for famille in range(config.familles):
                d_avant, d_apres = avant[grain][famille], apres[grain][famille]
                if d_avant == d_apres:
                    continue
                classe = classe_transition(statut_de(d_avant), statut_de(d_apres))
                if classe is None:
                    continue
                partie.transitions.append(
                    Transition(
                        evenement=evenement,
                        grain=grain,
                        famille=famille,
                        d_avant=d_avant,
                        d_apres=d_apres,
                        statut_avant=statut_de(d_avant),
                        statut_apres=statut_de(d_apres),
                        classe=classe,
                        cause=cause,
                    )
                )

    vivantes = etat.vue_privilegiee().posees
    partie.scores = points_par_joueur(vivantes, config.familles, config.joueurs)
    partie.gains = gains_auditeur(partie.scores)
    return partie


def gains_auditeur(scores: Sequence[int]) -> list[float]:
    """La formule du paragraphe 5.2, retranscrite ici et non importee du moteur."""
    n = len(scores)
    meilleur = max(scores)
    k = sum(1 for s in scores if s == meilleur)
    gain = (n - k) / (k * (n - 1))
    perte = -1 / (n - 1)
    return [gain if s == meilleur else perte for s in scores]

"""Fabrique de parties **construites a la main**, pour tester le compteur de retournements.

Le compteur produit les chiffres du go/no-go de la phase 1. Un chiffre dont personne ne peut
verifier le calcul n'est pas un resultat : c'est exactement la faute qui a coute trois mois au
projet. On teste donc le compteur sur des parties dont **on ecrit soi-meme les douze cartes
posees au banquet**, et dont on calcule la suite des statuts de tete, sans faire tourner le
moteur pour obtenir l'attendu.

Le principe. Seules les cartes **du banquet** changent l'influence d'une famille
(`rules.influence`) : une carte de domaine ne la touche pas. Il suffit donc de fixer les
douze cartes de banquet -- une par tour, la structure du tour en impose exactement une -- et
de laisser les vingt-quatre autres cartes tomber ou elles veulent dans les domaines, ou elles
sont sans effet sur le statut des familles.

Le script dit, pour chaque tour : quelle carte va au banquet, dans quelle position, et si
l'Assassin du banquet -- quand la carte du banquet **est** un Assassin -- tue sa premiere
cible. Tous les autres Assassins refusent, ce qui garantit qu'aucune carte ne meurt en
dehors de ce que le script demande.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from courtisans import rules
from courtisans.cards import Carte, GenreZone, Position, Role
from courtisans.config import GameConfig
from courtisans.engine import Engine, Phase, State


@dataclass(frozen=True)
class TourScripte:
    """Ce qu'un joueur fait a son tour, dans une partie construite a la main.

    Attributes:
        famille: la famille de la carte posee au banquet.
        role: son role.
        position: Estime ou Disgrace.
        tuer_au_banquet: si la carte du banquet est un Assassin, tuer sa cible d'indice 0.
            Sans effet sinon. Tout autre Assassin du tour refuse toujours.
    """

    famille: int
    role: Role
    position: Position
    tuer_au_banquet: bool = False


def pioche_scriptee(config: GameConfig, script: Sequence[TourScripte]) -> tuple[Carte, ...]:
    """La pioche qui met la carte voulue dans la main du joueur, a chaque tour.

    Les trois premieres cartes vont au joueur 0, les trois suivantes au joueur 1, et ainsi de
    suite (`Engine.reset_depuis_pioche`). On reserve donc, pour chaque tour du script, la
    carte designee, puis on complete chaque main avec deux cartes quelconques du reste.

    Raises:
        ValueError: si le script demande plus de tours que la configuration n'en a, ou une
            carte que le paquet ne contient pas en assez d'exemplaires.
    """
    tours_totaux = config.tours * config.joueurs
    if len(script) != tours_totaux:
        raise ValueError(
            f"le script decrit {len(script)} tours, la configuration en compte {tours_totaux}"
        )

    reste = list(rules.paquet(config))
    designees: list[Carte] = []
    for tour in script:
        candidate = next(
            (c for c in reste if c.famille == tour.famille and c.role is tour.role), None
        )
        if candidate is None:
            raise ValueError(
                f"le paquet n'a plus de carte (famille {tour.famille}, {tour.role.name}) : "
                f"le script en demande trop d'exemplaires"
            )
        reste.remove(candidate)
        designees.append(candidate)

    # Les Assassins non designes passent en fin de reste, donc en fin de partie : sans cela,
    # ils ouvriraient des noeuds de ciblage des les premiers tours et l'ordre des noeuds ne
    # serait plus calculable de tete. Ils ne changent rien aux statuts -- ils sont poses dans
    # des domaines et refusent toujours -- mais ils changent le numero des noeuds.
    reste.sort(key=lambda carte: carte.role in rules.ROLES_ASSASSINS)

    pioche: list[Carte] = []
    for designee in designees:
        pioche.append(designee)
        pioche.append(reste.pop(0))
        pioche.append(reste.pop(0))
    pioche.extend(reste)
    return tuple(pioche)


def politique_scriptee(script: Sequence[TourScripte]):
    """Une politique qui joue le script : la bonne carte au banquet, et rien d'autre.

    Elle ne lit l'etat que pour retrouver l'indice d'action correspondant a la carte voulue.
    Ce n'est ni une IA ni une heuristique : le coup est ecrit d'avance, elle le traduit.
    """
    tours_joues = 0

    def politique(etat: State) -> int:
        nonlocal tours_joues
        if etat.phase() is Phase.POSE:
            tour = script[tours_joues]
            tours_joues += 1
            return _action_qui_pose_au_banquet(etat, tour)

        assassin = etat.assassin_en_resolution()
        assert assassin is not None
        tour = script[tours_joues - 1]
        au_banquet = assassin.zone.genre is GenreZone.BANQUET
        cibles = etat.cibles_courantes()
        if tour.tuer_au_banquet and au_banquet and cibles:
            return 0
        return len(cibles)

    return politique


def _action_qui_pose_au_banquet(etat: State, tour: TourScripte) -> int:
    """L'action legale qui envoie la carte voulue au banquet, dans la position voulue."""
    joueur = etat.current_player()
    main = etat.vue_privilegiee().mains[joueur]
    for action in etat.legal_actions():
        pose = rules.decoder_action_pose(action, etat.config)
        carte = main[pose.indices_main[0]]
        if (
            carte.famille == tour.famille
            and carte.role is tour.role
            and pose.position is tour.position
        ):
            return action
    raise AssertionError(
        f"aucune action ne pose (famille {tour.famille}, {tour.role.name}) en "
        f"{tour.position.name} : la main du joueur {joueur} est {main}"
    )


def etat_scripte(config: GameConfig, script: Sequence[TourScripte]) -> State:
    """L'etat initial d'une partie construite a la main."""
    return Engine(config).reset_depuis_pioche(pioche_scriptee(config, script))

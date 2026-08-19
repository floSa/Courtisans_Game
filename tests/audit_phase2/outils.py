"""Constructions a la main pour les controles hostiles de l'audit de la phase 2.

Un etat est bati **champ par champ**, sans passer par `reset` : c'est la seule facon
d'obtenir la position exacte dont l'attendu se calcule de tete. Le moteur ne valide pas
ces etats, et c'est voulu -- un test qui devrait jouer douze coups pour atteindre la
position qu'il veut tester ne teste plus ce qu'il croit.
"""

from __future__ import annotations

from courtisans.cards import Carte, CartePosee, Position, Role, Zone
from courtisans.config import GameConfig
from courtisans.engine import Phase, State

#: L'instance de la phase 2, celle que le protocole a fixee en phase 1.
INSTANCE = GameConfig(familles=4, roles=tuple(Role), exemplaires=2, joueurs=3)

#: La meme instance **sans Assassin**. Elle reste conforme : 4 familles > 3 joueurs, et
#: `32 // 9 = 3` tours, soit exactement le plancher du paragraphe 8 des regles.
SANS_ASSASSIN = GameConfig(
    familles=4,
    roles=(Role.GARDE, Role.NOBLE, Role.ESPION, Role.NEUTRE),
    exemplaires=2,
    joueurs=3,
)


def banquet(carte: Carte, position: Position, poseur: int) -> CartePosee:
    """Une carte au banquet, du cote demande."""
    return CartePosee(carte, Zone.banquet(position), poseur)


def domaine(carte: Carte, proprietaire: int, poseur: int) -> CartePosee:
    """Une carte dans le domaine de `proprietaire`, posee par `poseur`."""
    return CartePosee(carte, Zone.domaine(proprietaire), poseur)


def etat_de_ciblage(
    posees: list[CartePosee],
    assassin: CartePosee,
    joueur: int,
    *,
    config: GameConfig = INSTANCE,
    pioche: list[Carte] | None = None,
    mains: list[list[Carte]] | None = None,
    tours_joues: int = 0,
) -> State:
    """Un etat arrete sur le noeud de ciblage de `assassin`, a `joueur` de choisir."""
    return State(
        config=config,
        _pioche=list(pioche or []),
        _mains=[list(main) for main in (mains or [[] for _ in range(config.joueurs)])],
        _posees=list(posees),
        _joueur=joueur,
        _tours_joues=tours_joues,
        _assassins_en_attente=[assassin],
        _phase=Phase.CIBLAGE,
    )


def etat_de_pose(
    posees: list[CartePosee],
    main: list[Carte],
    joueur: int,
    *,
    config: GameConfig = INSTANCE,
    pioche: list[Carte] | None = None,
    tours_joues: int = 0,
) -> State:
    """Un etat arrete sur la pose de `joueur`, main imposee."""
    mains: list[list[Carte]] = [[] for _ in range(config.joueurs)]
    mains[joueur] = list(main)
    return State(
        config=config,
        _pioche=list(pioche or []),
        _mains=mains,
        _posees=list(posees),
        _joueur=joueur,
        _tours_joues=tours_joues,
        _phase=Phase.POSE,
    )

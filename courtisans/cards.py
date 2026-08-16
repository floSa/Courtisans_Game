"""Cartes, roles et zones.

L'ordre de declaration des enumerations est **canonique** : c'est lui qui sert a trier, a
indexer et a comparer. Le modifier change l'ordre canonique de la main
(03_specification_moteur.md paragraphe 4.2) et donc la carte designee par une action de
pose.

Ce module ne contient aucune regle de jeu : il decrit ce qu'une carte **est** -- sa
famille, son role, sa valeur, sa visibilite -- et ou elle peut se trouver. Ce qu'on a le
droit d'en faire est dans `rules.py`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from types import MappingProxyType


class Role(IntEnum):
    """Les cinq roles du jeu complet, dans l'ordre du paragraphe 3.1 des regles.

    Une instance reduite peut retirer des roles entiers, jamais modifier l'effet d'un role
    conserve (paragraphe 8).
    """

    ASSASSIN = 0
    GARDE = 1
    NOBLE = 2
    ESPION = 3
    NEUTRE = 4


class Position(IntEnum):
    """Les deux positions du banquet, chez la Reine (paragraphe 3.2 des regles).

    Une carte en Estime ajoute sa valeur a l'influence de sa famille, une carte en
    Disgrace la retranche (paragraphe 5.1).
    """

    ESTIME = 0
    DISGRACE = 1


class GenreZone(IntEnum):
    """Les deux genres de zone : le banquet, chez la Reine, et les domaines des joueurs."""

    BANQUET = 0
    DOMAINE = 1


#: Valeur de chaque role, paragraphe 4 des regles. **Le Noble pese 2, tous les autres 1**,
#: au banquet comme dans les domaines. C'est la seule table de valeurs du moteur : le
#: decompte des points et le calcul d'influence la lisent tous les deux.
VALEURS: Mapping[Role, int] = MappingProxyType(
    {
        Role.ASSASSIN: 1,
        Role.GARDE: 1,
        Role.NOBLE: 2,
        Role.ESPION: 1,
        Role.NEUTRE: 1,
    }
)

#: Roles poses face cachee (paragraphe 4.2). Seul le poseur en connait l'identite ; les
#: autres ne voient qu'un dos, dont la position, elle, est connue.
ROLES_CACHES: frozenset[Role] = frozenset({Role.ESPION})


@dataclass(frozen=True, order=True)
class Carte:
    """Une carte du paquet, unique par (famille, role, exemplaire).

    L'ordre naturel du tuple -- famille, puis role, puis exemplaire -- est l'ordre
    canonique de la main. L'exemplaire ne departage que des cartes interchangeables : il
    ne sert qu'a rendre le tri deterministe (invariant I10).
    """

    famille: int
    role: Role
    exemplaire: int

    @property
    def valeur(self) -> int:
        """Ce que la carte pese, en influence comme en points (paragraphe 4)."""
        return VALEURS[self.role]

    @property
    def face_cachee(self) -> bool:
        """Vrai si la carte est posee face cachee (paragraphe 4.2)."""
        return self.role in ROLES_CACHES


@dataclass(frozen=True)
class Zone:
    """Un emplacement du plateau : une position du banquet, ou le domaine d'un joueur.

    Les deux attributs existent toujours, l'un des deux valant `None`. Les zones sont
    deux a deux disjointes : c'est ce qui garantit qu'un Assassin pose ce tour-ci ne peut
    jamais cibler ses deux compagnons de tour (paragraphe 3.2).
    """

    genre: GenreZone
    position: Position | None = None
    proprietaire: int | None = None

    @classmethod
    def banquet(cls, position: Position) -> Zone:
        """La zone Estime ou Disgrace du banquet."""
        return cls(GenreZone.BANQUET, position=position)

    @classmethod
    def domaine(cls, proprietaire: int) -> Zone:
        """Le domaine d'un joueur, celui qui encaisse les points de ses cartes."""
        return cls(GenreZone.DOMAINE, proprietaire=proprietaire)


@dataclass(frozen=True)
class CartePosee:
    """Une carte sur le plateau : ce qu'elle est, ou elle est, et qui l'y a mise.

    Le poseur n'est trace que pour les cartes cachees, ou c'est le seul indice disponible
    (question Q3 des regles) ; pour une carte visible il ne sert qu'a l'affichage et aux
    tests. **Il ne donne aucun point** : les points vont au proprietaire du domaine.
    """

    carte: Carte
    zone: Zone
    poseur: int

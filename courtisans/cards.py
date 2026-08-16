"""Cartes, roles et zones.

**Etat a l'etape 3 : ce module ne contient que les deux enumerations dont `config.py` a
besoin.** `Carte`, `Zone`, `GenreZone` et `CartePosee` arrivent a l'etape 4, avec la valeur
des roles et leur visibilite.

L'ordre de declaration des deux enumerations est **canonique** : c'est lui qui sert a
trier, a indexer et a comparer. Le modifier change l'ordre canonique de la main
(03_specification_moteur.md paragraphe 4.2) et donc la carte designee par une action de
pose.
"""

from __future__ import annotations

from enum import IntEnum


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

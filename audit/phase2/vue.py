"""La vue legale d'un siege : ce qu'un joueur a le droit de savoir, et rien de plus.

**C'est le garde-fou central de cet audit.** Un greedy qui lit `etat.vue_privilegiee()`
voit les Espions adverses ; son winrate est alors gonfle et il fixe une echelle fausse
pour toutes les phases suivantes. Plutot que de faire confiance a une relecture, cette
structure **retire physiquement** l'identite des dos adverses : elle ne contient pas les
`Carte` cachees, seulement leur zone et leur poseur. Une politique qui ne consomme que
`VueLegale` ne peut pas tricher, meme par accident.

Le contenu suit le tableau du paragraphe 2.6 des regles, ligne a ligne :

  - toutes les cartes face visible du plateau, famille, role et zone   -> `connues`
  - sa propre main                                                     -> `main`
  - l'identite des Espions qu'il a lui-meme poses                      -> `connues`
  - la composition totale du paquet                                    -> `config`
  - le nombre de tours restants                                        -> `tours_restants`
  - la defausse, publique (paragraphe 4.1)                             -> `defausse`
  - la position des dos adverses, sans leur identite                   -> `dos`
"""

from __future__ import annotations

from dataclasses import dataclass

from courtisans.cards import ROLES_CACHES, Carte, CartePosee, Zone
from courtisans.config import GameConfig
from courtisans.engine import State


@dataclass(frozen=True)
class Dos:
    """Un Espion adverse : ou il est, qui l'a pose. **Pas ce qu'il est.**"""

    zone: Zone
    poseur: int


@dataclass(frozen=True)
class VueLegale:
    """Tout ce qu'un siege sait, et rien de plus (paragraphe 2.6 des regles)."""

    config: GameConfig
    moi: int
    main: tuple[Carte, ...]
    connues: tuple[CartePosee, ...]
    dos: tuple[Dos, ...]
    defausse: tuple[CartePosee, ...]
    taille_pioche: int
    tours_restants: tuple[int, ...]


def vue_legale(etat: State, joueur: int) -> VueLegale:
    """Extrait la vue de `joueur`. Seule porte d'entree d'une politique sur l'etat.

    Le predicat de separation est celui du paragraphe 4.2 des regles : une carte face
    cachee posee par quelqu'un d'autre est un dos, tout le reste est connu de son poseur
    et des autres selon sa face.
    """
    if not 0 <= joueur < etat.config.joueurs:
        raise ValueError(f"joueur {joueur} ne designe aucun siege")
    dieu = etat.vue_privilegiee()
    connues: list[CartePosee] = []
    dos: list[Dos] = []
    for posee in dieu.posees:
        if posee.carte.role in ROLES_CACHES and posee.poseur != joueur:
            dos.append(Dos(posee.zone, posee.poseur))
        else:
            connues.append(posee)
    return VueLegale(
        config=etat.config,
        moi=joueur,
        main=tuple(dieu.mains[joueur]),
        connues=tuple(connues),
        dos=tuple(dos),
        defausse=tuple(dieu.defausse),
        taille_pioche=len(dieu.pioche),
        tours_restants=tuple(
            etat.tours_restants(autre) for autre in range(etat.config.joueurs)
        ),
    )

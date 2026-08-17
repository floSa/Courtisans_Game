"""Jouer une partie et relever ce qu'elle produit, sans rien decider.

Le releve porte sur la **vue privilegiee** -- la vue de dieu. C'est legitime ici : le
paragraphe 4 de la specification la reserve aux tests et a la mesure, et l'interdit a une
IA. Rien de ce module n'est lu par un agent.

**Deux grains, parce que la reponse en depend.** Le statut d'une famille est releve apres
chaque `apply()` (grain fin) et a la fin de chaque tour de joueur (grain tour). Le
paragraphe 2.3 des regles fait des trois cartes **et** des Assassins un seul coup : un
statut qui va et revient entre la pose d'un Assassin et son meurtre est un transitoire que
le grain fin voit et que le grain tour ne voit pas. Les tests de
`tests/mesure/test_parties_construites.py` construisent exactement ce cas.

**Deux vues, parce qu'un retournement invisible n'est pas planifiable.** Le statut vrai
compte les Espions poses face cachee ; le statut public ne compte que les cartes face
visible, c'est-a-dire ce que **tout le monde** voit.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from time import perf_counter

from courtisans import rules
from courtisans.cards import CartePosee, Role
from courtisans.engine import Phase, State
from courtisans.rules import Statut
from mesure.retournement import Retournements, analyser_suite

#: Une politique lit un etat et rend une action legale. La seule de ce paquet est uniforme.
Politique = Callable[[State], int]


class Grain(Enum):
    """A quel moment le statut des familles est releve."""

    FIN = "fin"
    TOUR = "tour"


class Vue(Enum):
    """Sur quelles cartes le statut est calcule."""

    VRAIE = "vraie"
    PUBLIQUE = "publique"


#: Les quatre combinaisons relevees pour chaque partie.
SUPPORTS: tuple[tuple[Grain, Vue], ...] = tuple(
    (grain, vue) for grain in Grain for vue in Vue
)


@dataclass(frozen=True)
class Partie:
    """Tout ce qu'une partie a produit. Aucun jugement, que des relevés.

    Attributes:
        seed: le seed de la donne, ou `None` sur une partie a pioche explicite.
        poses_par_joueur: nombre de tours joues par chaque siege.
        cibles_par_noeud: nombre de cibles valides a chaque noeud de ciblage, dans l'ordre.
        scores: points bruts finaux, par siege.
        gains: `returns()` finaux, par siege.
        cartes_mortes: `(famille, role)` de chaque carte tuee, dans l'ordre des meurtres.
        cartes_non_piochees: cartes restees en pioche, jamais revelees.
        suites: pour chaque support, la suite des statuts de chaque famille.
        duree_s: temps mural de la partie, en secondes.
    """

    seed: int | None
    poses_par_joueur: tuple[int, ...]
    cibles_par_noeud: tuple[int, ...]
    scores: tuple[int, ...]
    gains: tuple[float, ...]
    cartes_mortes: tuple[tuple[int, Role], ...]
    cartes_non_piochees: int
    suites: Mapping[tuple[Grain, Vue], tuple[tuple[Statut, ...], ...]]
    duree_s: float

    @property
    def morts(self) -> int:
        """Nombre de cartes tuees sur la partie."""
        return len(self.cartes_mortes)

    @property
    def noeuds_ciblage(self) -> int:
        """Nombre de decisions d'Assassin, cibles ou non : un Assassin pose decide toujours."""
        return len(self.cibles_par_noeud)

    @property
    def noeuds_avec_cible(self) -> int:
        """Noeuds ou **refuser de tuer est un choix**, c'est-a-dire ou une cible existe.

        Un noeud sans cible n'offre que le refus : l'Assassin ne choisit pas, il constate.
        """
        return sum(1 for cibles in self.cibles_par_noeud if cibles >= 1)

    def retournements_par_famille(self, grain: Grain, vue: Vue) -> tuple[Retournements, ...]:
        """Les quatre definitions, famille par famille, sur le support demande."""
        return tuple(analyser_suite(suite) for suite in self.suites[grain, vue])

    def retournements(self, grain: Grain, vue: Vue) -> Retournements:
        """Les quatre definitions au niveau de la partie : au moins une famille les tient."""
        return Retournements.ou(self.retournements_par_famille(grain, vue))


def politique_uniforme(alea: random.Random) -> Politique:
    """Tire une action au hasard parmi les legales, sans lire l'etat.

    **Ce n'est pas une IA.** Elle n'evalue rien, ne compare rien, ne prefere rien : elle
    tire un indice dans une liste. La phase 1 mesure le jeu, elle n'y joue pas.
    """

    def politique(etat: State) -> int:
        return alea.choice(etat.legal_actions())

    return politique


def observer(etat: State, politique: Politique, seed: int | None = None) -> Partie:
    """Joue la partie jusqu'au bout et rend son releve.

    Args:
        etat: un etat initial, a pioche fixee. Un etat a noeuds de chance est refuse : les
            parties de mesure doivent etre reproductibles a partir de leur seul seed.
        politique: ce qui choisit l'action a chaque decision.
        seed: le seed de la donne, recopie tel quel dans le releve.

    Raises:
        ValueError: si la partie atteint un noeud de chance.
    """
    debut = perf_counter()
    familles = etat.config.familles
    poses = [0] * etat.config.joueurs
    cibles_par_noeud: list[int] = []
    morts_avant = 0
    cartes_mortes: list[tuple[int, Role]] = []

    releves: dict[tuple[Grain, Vue], list[list[Statut]]] = {
        support: [[] for _ in range(familles)] for support in SUPPORTS
    }
    _relever(etat, releves, Grain.FIN)
    _relever(etat, releves, Grain.TOUR)

    while not etat.is_terminal():
        if etat.phase() is Phase.CHANCE:
            raise ValueError(
                "la mesure refuse un etat a noeuds de chance : une partie mesuree doit etre "
                "reproductible depuis son seul seed (reset ou reset_depuis_pioche)"
            )
        if etat.phase() is Phase.POSE:
            poses[etat.current_player()] += 1
        else:
            cibles_par_noeud.append(len(etat.cibles_courantes()))

        etat.apply(politique(etat))

        defausse = etat.vue_privilegiee().defausse
        if len(defausse) > morts_avant:
            cartes_mortes.extend(_identites(defausse[morts_avant:]))
            morts_avant = len(defausse)

        _relever(etat, releves, Grain.FIN)
        if etat.phase() is not Phase.CIBLAGE:
            _relever(etat, releves, Grain.TOUR)

    scores = etat.scores()
    return Partie(
        seed=seed,
        poses_par_joueur=tuple(poses),
        cibles_par_noeud=tuple(cibles_par_noeud),
        scores=tuple(scores[joueur] for joueur in range(etat.config.joueurs)),
        gains=tuple(etat.returns()),
        cartes_mortes=tuple(cartes_mortes),
        cartes_non_piochees=len(etat.vue_privilegiee().pioche),
        suites={
            support: tuple(tuple(suite) for suite in par_famille)
            for support, par_famille in releves.items()
        },
        duree_s=perf_counter() - debut,
    )


def _identites(posees: Sequence[CartePosee]) -> list[tuple[int, Role]]:
    """L'identite des cartes tuees. Publique : une carte tuee est revelee (paragraphe 4.1)."""
    return [(posee.carte.famille, posee.carte.role) for posee in posees]


def _relever(
    etat: State, releves: dict[tuple[Grain, Vue], list[list[Statut]]], grain: Grain
) -> None:
    """Ajoute le statut courant de chaque famille, dans les deux vues, pour ce grain."""
    posees = etat.vue_privilegiee().posees
    familles = etat.config.familles
    par_vue = {
        Vue.VRAIE: rules.statuts(posees, familles),
        Vue.PUBLIQUE: rules.statuts(
            [posee for posee in posees if not posee.carte.face_cachee], familles
        ),
    }
    for vue, statuts in par_vue.items():
        for famille in range(familles):
            releves[grain, vue][famille].append(statuts[famille])

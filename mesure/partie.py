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

**Trois sortes de vues, parce qu'un retournement invisible n'est pas planifiable.** Le
statut vrai compte les Espions poses face cachee ; le statut public ne compte que les cartes
face visible, c'est-a-dire le savoir commun ; le statut vu par un siege ajoute au savoir
commun **ses propres Espions**, dont il connait l'identite. Les vues par siege ont ete
ajoutees a l'audit du resultat : sans elles, l'ecart entre vue vraie et vue publique aurait
ete presente comme « invisible de tous », alors qu'il compte aussi les retournements que
leur poseur, lui, voyait parfaitement -- ceux-la sont justement les seuls planifiables.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import ClassVar

from courtisans import rules
from courtisans.cards import CartePosee, Role
from courtisans.engine import Phase, State
from courtisans.rules import Statut
from mesure.retournement import Retournements, analyser_suite, evenements_r2

#: Une politique lit un etat et rend une action legale. La seule de ce paquet est uniforme.
Politique = Callable[[State], int]


class Grain(Enum):
    """A quel moment le statut des familles est releve."""

    FIN = "fin"
    TOUR = "tour"


@dataclass(frozen=True)
class Vue:
    """Sur quelles cartes du banquet le statut est calcule.

    Trois sortes de vues, et il faut les trois. **La vue publique n'est la vue de personne** :
    elle est le savoir commun, c'est-a-dire ce que voient les trois joueurs a la fois. Un
    Espion pose face cachee n'y figure pas, alors que **son poseur, lui, sait ce que c'est**
    (paragraphe 4.2 des regles). Conclure d'un ecart entre vue vraie et vue publique qu'un
    retournement est invisible de tous serait donc faux : il peut etre visible de celui qui
    l'a arme -- ce qui est precisement le cas ou il a pu etre planifie.

    Attributes:
        nom: son intitule dans le rapport.
        joueur: le siege dont c'est la vue, ou `None` pour la vue vraie et la vue publique.
        tout_voir: vrai pour la seule vue de dieu.
    """

    VRAIE: ClassVar[Vue]
    PUBLIQUE: ClassVar[Vue]

    nom: str
    joueur: int | None = None
    tout_voir: bool = False

    def retient(self, posee: CartePosee) -> bool:
        """Vrai si cette carte compte dans le statut, pour cette vue."""
        if self.tout_voir:
            return True
        if not posee.carte.face_cachee:
            return True
        return self.joueur is not None and posee.poseur == self.joueur

    @classmethod
    def du_joueur(cls, joueur: int) -> Vue:
        """La vue d'un siege : les cartes visibles, plus ses propres Espions."""
        return cls(nom=f"joueur {joueur}", joueur=joueur)


Vue.VRAIE = Vue(nom="vraie", tout_voir=True)
Vue.PUBLIQUE = Vue(nom="publique")


def vues(joueurs: int) -> tuple[Vue, ...]:
    """La vue de dieu, le savoir commun, et la vue de chaque siege."""
    return (Vue.VRAIE, Vue.PUBLIQUE, *(Vue.du_joueur(joueur) for joueur in range(joueurs)))


def supports(joueurs: int) -> tuple[tuple[Grain, Vue], ...]:
    """Toutes les combinaisons grain x vue relevees pour chaque partie."""
    return tuple((grain, vue) for grain in Grain for vue in vues(joueurs))


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
        """Les quatre definitions au niveau de la partie : au moins une famille les tient.

        **A ne jamais comparer a une autre vue.** C'est deja un OU sur les familles : deux
        vues peuvent le rendre vrai toutes les deux sur des familles differentes, et une
        comparaison de ces booleens ne dit alors rien de ce qui se voit. L'audit croise a
        rejete la premiere version de la mesure exactement la-dessus. Pour comparer des
        vues, passer par `retournements_par_famille` ou `evenements_r2_par_famille`.
        """
        return Retournements.ou(self.retournements_par_famille(grain, vue))

    def evenements_r2_par_famille(self, grain: Grain, vue: Vue) -> tuple[tuple[int, ...], ...]:
        """Pour chaque famille, les instants ou elle perd un acquis. Non agrege."""
        return tuple(evenements_r2(suite) for suite in self.suites[grain, vue])


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
        support: [[] for _ in range(familles)] for support in supports(etat.config.joueurs)
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
    for vue in vues(etat.config.joueurs):
        # `rules.statuts` reste la seule formule d'influence du projet : la vue ne choisit
        # que les cartes qu'on lui donne, elle ne recalcule rien.
        statuts = rules.statuts([posee for posee in posees if vue.retient(posee)], familles)
        for famille in range(familles):
            releves[grain, vue][famille].append(statuts[famille])


@dataclass(frozen=True)
class ComptageInvisible:
    """Ce que les Espions caches soustraient a la connaissance des joueurs.

    **Aucun de ces six nombres n'agrege les familles ni les sieges.** C'est la lecon du
    rejet de l'audit croise : le compte precedent comparait un booleen de partie -- deja un
    OU sur quatre familles -- a un `any` sur trois sieges, et la conjonction resultante
    etait quasi impossible par construction. Le zero qu'elle affichait ne mesurait pas
    l'invisibilite, il mesurait l'improbabilite d'une double agregation.

    Attributes:
        familles_r2: familles ayant perdu un acquis, en vue vraie.
        familles_invisibles: parmi elles, celles dont **aucun** siege ne voit la moindre
            perte d'acquis.
        parties_avec_famille_invisible: parties contenant au moins une telle famille.
        evenements: pertes d'acquis vraies, datees, toutes familles confondues.
        evenements_invisibles: parmi elles, celles qu'aucun siege ne voit **au meme
            instant**. Plus severe que le niveau famille : un siege peut voir la famille
            bouger sans voir cette perte-la.
        parties_avec_evenement_invisible: parties contenant au moins une telle perte.
    """

    familles_r2: int
    familles_invisibles: int
    parties_avec_famille_invisible: int
    evenements: int
    evenements_invisibles: int
    parties_avec_evenement_invisible: int


def compter_invisible(
    parties: Sequence[Partie], joueurs: int, familles: int, grain: Grain = Grain.TOUR
) -> ComptageInvisible:
    """Compte, sans agreger, ce qu'aucun siege ne voit."""
    totaux = [0] * 6
    for partie in parties:
        vrais = partie.evenements_r2_par_famille(grain, Vue.VRAIE)
        par_siege = [
            partie.evenements_r2_par_famille(grain, Vue.du_joueur(siege))
            for siege in range(joueurs)
        ]
        famille_ici = evenement_ici = 0
        for famille in range(familles):
            vus: set[int] = set()
            for siege in par_siege:
                vus |= set(siege[famille])
            if vrais[famille]:
                totaux[0] += 1
                if not vus:
                    totaux[1] += 1
                    famille_ici += 1
            totaux[3] += len(vrais[famille])
            invisibles = set(vrais[famille]) - vus
            totaux[4] += len(invisibles)
            evenement_ici += len(invisibles)
        totaux[2] += famille_ici > 0
        totaux[5] += evenement_ici > 0
    return ComptageInvisible(*totaux)

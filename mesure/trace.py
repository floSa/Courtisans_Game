"""La trace d'une partie, decision par decision. Le support des sept compteurs.

`mesure/partie.py` releve des agregats -- suites de statuts, comptes de cibles, scores. Les
comportements B1 a B7 ont besoin d'autre chose : **ce que chaque decideur voyait, et ce qu'il
a fait**, nœud par nœud. Ce module produit cette trace ; `mesure/comportements.py` en tire les
sept chiffres. `partie.py` n'est pas touche : ses deux reserves de la phase 1 sont ouvertes, et
l'elargir pour un besoin de phase 2 les melangerait.

Trois choses que la trace porte et sans lesquelles aucun compteur n'est definissable
------------------------------------------------------------------------------------
1. **La vue du decideur avant son coup** (`connues`), parce qu'un comportement qualifie un
   choix et qu'un choix se prend sur ce qu'on sait. La vue publique **n'est la vue de
   personne** : un joueur connait en plus ses propres Espions.
2. **La verite avant son coup** (`posees`), parce que ce qui PAIE se calcule sur la vue vraie
   -- tous les Espions sont retournes avant le decompte (paragraphes 4.2 et 5 des regles).
3. **L'evaluation de chaque action legale** (`valeurs`), parce que B4 doit dire si un refus
   etait strictement meilleur, a egalite, ou moins bon. L'etalon est
   `agents.greedy.evaluer_actions` pour **tout** agent trace, y compris celui de la phase 3 :
   deux agents juges par deux etalons differents ne se comparent pas.

Une politique par siege
-----------------------
`tracer` prend un tuple de politiques indexe par siege, la ou `partie.observer` en prend une
seule. La campagne B oppose **un greedy a deux aleatoires** : sans cette signature, on ne
pourrait pas la jouer.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from time import perf_counter

from agents.greedy import evaluer_actions
from agents.perception import CibleVue, percevoir
from courtisans import rules
from courtisans.cards import Carte, CartePosee, GenreZone, Position
from courtisans.engine import Phase, State
from courtisans.rules import Statut

#: Meme signature que `mesure.partie.Politique`.
Politique = Callable[[State], int]


@dataclass(frozen=True)
class Decision:
    """Un nœud de decision, avec ce que le decideur voyait et ce qu'il a fait.

    Attributes:
        numero: rang du nœud dans la partie, a partir de 0.
        joueur: le siege qui decide.
        phase: POSE ou CIBLAGE.
        tour: le tour de ce joueur, de 1 a `config.tours`.
        action: l'action jouee.
        main: sa main avant le coup, ordre canonique. Vide en CIBLAGE, la pose l'a videe.
        connues: **sa** vue des cartes posees vivantes, avant le coup.
        posees: la verite des cartes posees vivantes, avant le coup.
        mortes: les cartes tuees avant le coup. **Publiques** : une carte tuee est revelee et
            la defausse est publique (paragraphe 4.1). B7 en a besoin pour le residu.
        tours_restants: tours restants de chaque siege, avant le coup.
        cartes_posees: en POSE, les trois cartes, dans l'ordre banquet / domaine propre /
            domaine adverse -- qui est aussi l'ordre de resolution des Assassins
            (paragraphe 3.2).
        destinataire: en POSE, le proprietaire du domaine adverse vise.
        cibles: en CIBLAGE, les cibles **redigees** : un dos y porte `carte=None`.
        tuee: en CIBLAGE, la carte tuee, ou `None` si refus.
        valeurs: l'ecart evalue de chaque action legale, par `greedy.evaluer_actions`.
    """

    numero: int
    joueur: int
    phase: Phase
    tour: int
    action: int
    main: tuple[Carte, ...]
    connues: tuple[CartePosee, ...]
    posees: tuple[CartePosee, ...]
    mortes: tuple[Carte, ...]
    tours_restants: tuple[int, ...]
    cartes_posees: tuple[CartePosee, ...] = ()
    destinataire: int | None = None
    cibles: tuple[CibleVue, ...] = ()
    tuee: CartePosee | None = None
    valeurs: dict[int, int] = field(default_factory=dict)

    # -- Lectures dont les compteurs ont besoin, ecrites une fois ---------------------

    def carte_de_banquet(self) -> CartePosee | None:
        """La carte que ce coup a posee au banquet. `None` hors POSE."""
        return self.cartes_posees[0] if self.cartes_posees else None

    def carte_chez_soi(self) -> CartePosee | None:
        """La carte que ce coup a posee dans son propre domaine. `None` hors POSE."""
        return self.cartes_posees[1] if self.cartes_posees else None

    def carte_chez_l_adversaire(self) -> CartePosee | None:
        """La carte que ce coup a posee chez un adversaire. `None` hors POSE."""
        return self.cartes_posees[2] if self.cartes_posees else None

    def dos_du_plateau(self) -> tuple[CartePosee, ...]:
        """Les cartes posees que le decideur ne peut pas identifier, avant son coup.

        La difference entre la verite et sa vue. Leur **position** est connue de tous
        (paragraphe 2.6 des regles) ; leur identite ne l'est pas, et aucun compteur ne doit
        s'en servir autrement que comme « il y a un dos la ».
        """
        connues = set(self.connues)
        return tuple(posee for posee in self.posees if posee not in connues)

    def refus(self) -> bool:
        """Vrai si ce nœud de ciblage est un refus de tuer."""
        return self.phase is Phase.CIBLAGE and self.tuee is None

    def cibles_offertes(self) -> int:
        """Nombre de cibles valides. `len(cibles)`, nomme pour que le compte soit lisible."""
        return len(self.cibles)

    def toutes_les_cibles_sont_des_dos(self) -> bool:
        """Vrai si aucune cible n'est identifiable par le decideur.

        Sur un tel nœud, **toutes** les actions ont la meme valeur -- un dos ne compte pas
        dans l'influence percue, donc le tuer ne change rien -- et c'est la regle de departage
        qui choisit, pas l'heuristique. Le paragraphe 5.4.1 de la pre-inscription en tire la
        decomposition de B4.
        """
        return bool(self.cibles) and all(cible.carte is None for cible in self.cibles)


@dataclass(frozen=True)
class TracePartie:
    """Tout ce qu'une partie a produit, decision par decision. Aucun jugement.

    Attributes:
        seed: le seed de la donne, ou `None` sur une pioche explicite.
        replicat: l'indice du replicat de politique, pour l'appariement par donne.
        decisions: les nœuds, dans l'ordre.
        scores: points bruts finaux, par siege.
        gains: `returns()` finaux, par siege.
        posees_finales: les cartes posees **vivantes** a l'etat terminal.
        statuts_finaux: le statut vrai de chaque famille au decompte.
        duree_s: temps mural de la partie.
    """

    seed: int | None
    replicat: int
    decisions: tuple[Decision, ...]
    scores: tuple[int, ...]
    gains: tuple[float, ...]
    posees_finales: tuple[CartePosee, ...]
    statuts_finaux: dict[int, Statut]
    duree_s: float

    def poses(self) -> tuple[Decision, ...]:
        """Les nœuds de pose, tous sieges confondus."""
        return tuple(d for d in self.decisions if d.phase is Phase.POSE)

    def ciblages(self) -> tuple[Decision, ...]:
        """Les nœuds de ciblage, tous sieges confondus."""
        return tuple(d for d in self.decisions if d.phase is Phase.CIBLAGE)

    def cartes_vivantes_du_domaine(self, proprietaire: int) -> tuple[CartePosee, ...]:
        """Les cartes vivantes du domaine de `proprietaire`, a l'etat terminal."""
        return tuple(
            posee
            for posee in self.posees_finales
            if posee.zone.genre is GenreZone.DOMAINE
            and posee.zone.proprietaire == proprietaire
        )


def tracer(
    etat: State, politiques: Sequence[Politique], seed: int | None = None, replicat: int = 0
) -> TracePartie:
    """Joue la partie et rend sa trace complete.

    Args:
        etat: un etat initial a pioche fixee. Un nœud de chance est refuse -- une partie
            mesuree doit etre reproductible depuis son seul seed.
        politiques: une politique par siege, indexee en absolu.
        seed: le seed de la donne, recopie tel quel.
        replicat: l'indice du replicat, recopie tel quel. C'est lui qui permet le bootstrap
            par donne : sans lui, on ne saurait pas quelles parties partagent une pioche.

    Raises:
        ValueError: si la partie atteint un nœud de chance, ou si le nombre de politiques ne
            correspond pas au nombre de sieges.
    """
    if len(politiques) != etat.config.joueurs:
        raise ValueError(
            f"{len(politiques)} politique(s) pour {etat.config.joueurs} sieges : "
            f"il en faut une par siege, indexee en absolu"
        )
    debut = perf_counter()
    decisions: list[Decision] = []
    tours_par_joueur = [0] * etat.config.joueurs

    while not etat.is_terminal():
        if etat.phase() is Phase.CHANCE:
            raise ValueError(
                "la trace refuse un etat a nœuds de chance : une partie mesuree doit etre "
                "reproductible depuis son seul seed (reset ou reset_depuis_pioche)"
            )
        joueur = etat.current_player()
        perception = percevoir(etat, joueur)
        avant = etat.vue_privilegiee().posees
        mortes = tuple(posee.carte for posee in etat.vue_privilegiee().defausse)
        if etat.phase() is Phase.POSE:
            tours_par_joueur[joueur] += 1

        action = politiques[joueur](etat)
        valeurs = evaluer_actions(perception)
        cibles = perception.cibles
        tuee = (
            etat.cibles_courantes()[action]
            if etat.phase() is Phase.CIBLAGE and action < len(cibles)
            else None
        )

        etat.apply(action)
        apres = etat.vue_privilegiee().posees
        posees_du_coup = tuple(posee for posee in apres if posee not in avant)
        destinataire = None
        if posees_du_coup:
            adverse = posees_du_coup[-1]
            destinataire = adverse.zone.proprietaire

        decisions.append(
            Decision(
                numero=len(decisions),
                joueur=joueur,
                phase=perception.phase,
                tour=tours_par_joueur[joueur],
                action=action,
                main=perception.main,
                connues=perception.connues,
                posees=avant,
                mortes=mortes,
                tours_restants=perception.tours_restants,
                cartes_posees=posees_du_coup,
                destinataire=destinataire,
                cibles=cibles,
                tuee=tuee,
                valeurs=valeurs,
            )
        )

    scores = etat.scores()
    posees_finales = etat.vue_privilegiee().posees
    return TracePartie(
        seed=seed,
        replicat=replicat,
        decisions=tuple(decisions),
        scores=tuple(scores[siege] for siege in range(etat.config.joueurs)),
        gains=tuple(etat.returns()),
        posees_finales=posees_finales,
        statuts_finaux=rules.statuts(posees_finales, etat.config.familles),
        duree_s=perf_counter() - debut,
    )


def influence_vue(connues: Sequence[CartePosee], familles: int) -> dict[int, int]:
    """`d` par famille, sur un sous-ensemble de cartes. Delegue a `rules.influence`.

    Passer la vue d'un decideur donne son `d` percu ; passer la verite donne le vrai. La
    formule n'est pas reecrite : une seule source de verite (paragraphe 2 des conventions).
    """
    return rules.influence(connues, familles)


def est_au_banquet(posee: CartePosee, position: Position | None = None) -> bool:
    """Vrai si la carte est au banquet, et dans `position` si elle est donnee."""
    if posee.zone.genre is not GenreZone.BANQUET:
        return False
    return position is None or posee.zone.position is position

"""Le parametrage d'une instance de Courtisans.

**Il n'y a qu'un seul jeu, parametre.** Une variante n'est jamais un nouveau fichier :
c'est une `GameConfig` differente. Si une variante ne peut pas s'exprimer en
configuration, c'est la configuration qu'il faut etendre
(04_conventions_code.md paragraphe 2).

**Une configuration non conforme n'existe pas.** Toutes les contraintes sont verifiees a la
construction, et il n'y a aucun drapeau pour les contourner : ni pour un test, ni pour
reproduire une instance historique. Les quatre instances de la tentative precedente --
mini, assassin, redeal, combo -- violaient les regles ; les rendre constructibles
reintroduirait les defauts que cette reecriture corrige.

`tours` n'est pas un parametre : il est derive de la taille du paquet et du nombre de
joueurs. Le paragraphe 8 des regles interdit de toucher a la duree d'une partie, et la
seule facon de garantir qu'on n'y touche pas est de ne pas exposer le levier.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import factorial

from courtisans.cards import Position, Role

#: Nombre de cartes jouees par un joueur a chaque tour, une par zone : banquet, domaine
#: propre, domaine d'un adversaire (01_regles.md paragraphe 3.2). Structure fixe, sans
#: exception : ce n'est pas un parametre d'instance.
CARTES_PAR_TOUR = 3

#: Plancher du paragraphe 8 des regles : en dessous de 3 tours, un retournement n'est pas
#: realisable, et la reduction devient une troncature deguisee.
TOURS_MINIMUM = 3

#: Le moteur est specifie pour 2 a 4 joueurs (03_specification_moteur.md paragraphe 8).
#: 5 joueurs et plus ne sont pas specifies : la configuration est refusee, pas devinee.
JOUEURS_AUTORISES = (2, 3, 4)


def _entier(nom: str, valeur: object, minimum: int) -> int:
    """Valide un entier de configuration. Leve `ValueError` avec le detail du refus."""
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise ValueError(f"{nom} doit etre un entier, recu {valeur!r} de type "
                         f"{type(valeur).__name__}")
    if valeur < minimum:
        raise ValueError(f"{nom} doit valoir au moins {minimum}, recu {valeur}")
    return valeur


@dataclass(frozen=True)
class GameConfig:
    """Le parametrage complet d'une instance. Immuable, valide a la construction.

    Args:
        familles: nombre de familles, **strictement superieur** au nombre de joueurs.
        roles: les roles conserves. L'ordre de saisie est sans importance : ils sont
            ranges dans l'ordre canonique de l'enumeration `Role`.
        exemplaires: nombre d'exemplaires de chaque couple (famille, role).
        joueurs: 2, 3 ou 4.

    Raises:
        ValueError: des que l'une des contraintes du paragraphe 8 des regles est violee.

    Note:
        Le tableau du paragraphe 3 de la specification liste un champ `canonicalisation`.
        Il est **volontairement absent** : rien ne le lisait et aucun test ne le couvrait.
        Il reviendra a l'etape 6, dans `infoset.py`, quand il aura un effet et un test.
    """

    familles: int
    roles: tuple[Role, ...]
    exemplaires: int
    joueurs: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", self._roles_canoniques())
        _entier("familles", self.familles, minimum=1)
        _entier("exemplaires", self.exemplaires, minimum=1)

        if self.joueurs not in JOUEURS_AUTORISES:
            raise ValueError(
                f"joueurs doit valoir {' ou '.join(map(str, JOUEURS_AUTORISES))}, recu "
                f"{self.joueurs} -- au-dela, le jeu n'est pas specifie"
            )
        if self.familles <= self.joueurs:
            raise ValueError(
                f"il faut strictement plus de familles que de joueurs, recu "
                f"{self.familles} familles pour {self.joueurs} joueurs -- a familles egales, "
                f"chacun se replie sur la sienne et aucune alliance n'emerge "
                f"(01_regles.md paragraphe 8)"
            )
        if self.tours < TOURS_MINIMUM:
            raise ValueError(
                f"il faut au moins {TOURS_MINIMUM} tours par joueur, recu {self.tours} : "
                f"{self.nb_cartes} cartes // ({CARTES_PAR_TOUR} x {self.joueurs}) -- en "
                f"dessous, un retournement n'est pas realisable "
                f"(01_regles.md paragraphe 8)"
            )

    def _roles_canoniques(self) -> tuple[Role, ...]:
        """Range les roles dans l'ordre de l'enumeration, apres avoir refuse les doublons.

        Deux configurations qui different par l'ordre de saisie des roles sont la meme
        configuration : sans ce rangement, elles produiraient deux encodages differents.
        """
        roles = tuple(self.roles)
        if not roles:
            raise ValueError("il faut au moins un role")
        for candidat in roles:
            if not isinstance(candidat, Role):
                raise ValueError(
                    f"roles doit ne contenir que des Role, recu {candidat!r} de type "
                    f"{type(candidat).__name__}"
                )
        if len(set(roles)) != len(roles):
            raise ValueError(f"un role est fourni en double : {[r.name for r in roles]}")
        return tuple(sorted(roles))

    @property
    def nb_roles(self) -> int:
        """Nombre de roles conserves dans cette instance."""
        return len(self.roles)

    @property
    def nb_cartes(self) -> int:
        """Taille du paquet : familles x roles x exemplaires (paragraphe 3.1)."""
        return self.familles * self.nb_roles * self.exemplaires

    @property
    def tours(self) -> int:
        """Tours joues par chaque joueur, identique pour tous (paragraphe 3.4).

        Derive, jamais fourni : la partie s'arrete quand la pioche ne permet plus un tour
        de table complet, jamais parce qu'on l'interrompt.
        """
        return self.nb_cartes // (CARTES_PAR_TOUR * self.joueurs)

    @property
    def cartes_jouees(self) -> int:
        """Cartes effectivement posees sur une partie entiere (paragraphe 3.4)."""
        return CARTES_PAR_TOUR * self.joueurs * self.tours

    @property
    def reste_en_pioche(self) -> int:
        """Cartes jamais piochees, donc jamais revelees : `nb_cartes mod (3 x joueurs)`."""
        return self.nb_cartes - self.cartes_jouees

    @property
    def actions_de_pose(self) -> int:
        """Taille de l'espace d'actions de pose (paragraphe 3.2).

        `3!` assignations des trois cartes aux trois zones, x le choix Estime / Disgrace,
        x le choix de l'adversaire.
        """
        return factorial(CARTES_PAR_TOUR) * len(Position) * (self.joueurs - 1)

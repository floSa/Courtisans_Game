"""La machine a etats : reset, actions legales, transition, fin de partie, decompte.

Le moteur ne decide rien. Il applique les regles de `rules.py` et refuse tout ce qu'elles
n'autorisent pas. **Aucune heuristique, aucune evaluation, aucun score de position.**

Trois points sur lesquels les implementations precedentes se sont trompees, tenus ici par
construction :

1. **La partie s'arrete avant d'entamer un tour de table** si la pioche ne permet plus a
   *tous* les joueurs de jouer trois cartes (paragraphe 3.4). Tester la fin joueur par
   joueur ferait jouer un tour de plus aux premiers de l'ordre.
2. **Une action de pose est atomique** : les trois cartes sont placees d'un bloc, puis les
   Assassins se resolvent, dans l'ordre banquet, domaine propre, domaine adverse
   (paragraphe 3.2).
3. **Le meurtre est facultatif.** L'indice `len(cibles)` est le refus, et il est toujours
   legal, y compris quand des cibles existent (paragraphe 4.1, arbitrage R2).

`reset(seed)` n'est rien d'autre que `reset_depuis_pioche(pioche_depuis_seed(seed))` : le
seed ne produit que l'ordre de la pioche, tout ce qui suit est commun aux deux chemins.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum

from courtisans import rules
from courtisans.cards import Carte, CartePosee, Zone
from courtisans.config import CARTES_PAR_TOUR, GameConfig

#: Identifiants reserves, memes conventions qu'OpenSpiel, pour que l'adaptateur n'ait rien
#: a traduire.
JOUEUR_HASARD = -1
JOUEUR_TERMINAL = -4


class Phase(IntEnum):
    """Les phases d'un etat.

    `CHANCE` n'est **jamais** rendue par le coeur : la pioche est fixee a la construction
    de l'etat. Elle existe pour l'adaptateur OpenSpiel, qui expose la distribution et
    chaque repioche comme de vrais noeuds de hasard.
    """

    POSE = 0
    CIBLAGE = 1
    CHANCE = 2
    TERMINAL = 3


@dataclass(frozen=True)
class VuePrivilegiee:
    """Vue de dieu : tout ce qui est sur la table, cache ou non.

    **Reservee aux tests et a l'interface.** Ce que voit un joueur, c'est
    `information_state_string` et `information_state_tensor`, jamais ceci.
    """

    pioche: tuple[Carte, ...]
    mains: tuple[tuple[Carte, ...], ...]
    posees: tuple[CartePosee, ...]
    defausse: tuple[CartePosee, ...]


@dataclass
class State:
    """Un etat de partie. Mutable : `apply` avance l'etat, `clone` en donne une copie."""

    config: GameConfig
    _pioche: list[Carte]
    _mains: list[list[Carte]]
    _posees: list[CartePosee] = field(default_factory=list)
    _defausse: list[CartePosee] = field(default_factory=list)
    _joueur: int = 0
    _tours_joues: int = 0
    _assassins_en_attente: list[CartePosee] = field(default_factory=list)
    _phase: Phase = Phase.POSE

    # -- Lecture -------------------------------------------------------------------

    def phase(self) -> Phase:
        """La phase courante."""
        return self._phase

    def current_player(self) -> int:
        """Le joueur a qui appartient la decision, ou `JOUEUR_TERMINAL` a la fin."""
        if self._phase is Phase.TERMINAL:
            return JOUEUR_TERMINAL
        return self._joueur

    def is_terminal(self) -> bool:
        """Vrai quand plus aucun tour de table complet n'est possible."""
        return self._phase is Phase.TERMINAL

    def legal_actions(self) -> list[int]:
        """Les actions legales de la phase courante.

        En POSE, les actions qui font double emploi sont masquees. En CIBLAGE, il y en a
        `len(cibles) + 1`, la derniere etant le refus de tuer.
        """
        if self._phase is Phase.TERMINAL:
            return []
        if self._phase is Phase.POSE:
            return list(rules.actions_de_pose_legales(self._mains[self._joueur], self.config))
        return list(range(len(self.cibles_courantes()) + 1))

    def assassin_en_resolution(self) -> CartePosee | None:
        """L'Assassin dont c'est le tour de choisir, ou `None` hors phase de ciblage."""
        if self._phase is not Phase.CIBLAGE:
            return None
        return self._assassins_en_attente[0]

    def cibles_courantes(self) -> tuple[CartePosee, ...]:
        """Les cibles de l'Assassin en cours. L'indice `i` est l'action `i`.

        Vide hors phase de ciblage. L'indice `len(cibles)` est le refus de tuer.
        """
        assassin = self.assassin_en_resolution()
        if assassin is None:
            return ()
        return rules.cibles_valides(self._posees, assassin)

    def vue_privilegiee(self) -> VuePrivilegiee:
        """La vue de dieu. Voir l'avertissement de `VuePrivilegiee`."""
        return VuePrivilegiee(
            pioche=tuple(self._pioche),
            mains=tuple(tuple(main) for main in self._mains),
            posees=tuple(self._posees),
            defausse=tuple(self._defausse),
        )

    def scores(self) -> dict[int, int]:
        """Les points bruts de chaque joueur, disponibles a tout instant.

        Provisoires tant que la partie dure : le signe d'une famille peut encore changer
        jusqu'au dernier tour (paragraphe 2.1).
        """
        statuts = rules.statuts(self._posees, self.config.familles)
        totaux = rules.points(self._posees, statuts, self.config.joueurs)
        return dict(enumerate(totaux))

    def returns(self) -> list[float]:
        """Les gains a somme nulle. Tous nuls tant que la partie dure (paragraphe 2.1)."""
        if not self.is_terminal():
            return [0.0] * self.config.joueurs
        scores = self.scores()
        return rules.gains_depuis_scores([scores[j] for j in range(self.config.joueurs)])

    def information_state_string(self, player: int) -> str:
        """Non implemente : arrive avec `infoset.py`, a l'etape 6."""
        raise NotImplementedError(
            "information_state_string arrive avec infoset.py (etape 6)"
        )

    def information_state_tensor(self, player: int) -> list[float]:
        """Non implemente : arrive avec `infoset.py`, a l'etape 6."""
        raise NotImplementedError(
            "information_state_tensor arrive avec infoset.py (etape 6)"
        )

    def clone(self) -> State:
        """Une copie independante : la jouer ne touche pas l'original."""
        return State(
            config=self.config,
            _pioche=list(self._pioche),
            _mains=[list(main) for main in self._mains],
            _posees=list(self._posees),
            _defausse=list(self._defausse),
            _joueur=self._joueur,
            _tours_joues=self._tours_joues,
            _assassins_en_attente=list(self._assassins_en_attente),
            _phase=self._phase,
        )

    # -- Transition ----------------------------------------------------------------

    def apply(self, action: int) -> None:
        """Joue une action legale. Leve `ValueError` sur toute autre."""
        legales = self.legal_actions()
        if action not in legales:
            raise ValueError(
                f"action {action} illegale en phase {self._phase.name} : "
                f"legales = {legales}"
            )
        if self._phase is Phase.POSE:
            self._poser(action)
        else:
            self._resoudre_assassin(action)

    def _poser(self, action: int) -> None:
        """Place les trois cartes d'un bloc, puis ouvre la resolution des Assassins.

        Les trois zones sont distinctes par construction, donc un Assassin pose ici ne
        peut jamais cibler ses deux compagnons de tour.
        """
        pose = rules.decoder_action_pose(action, self.config)
        main = self._mains[self._joueur]
        adversaire = rules.destinataire(
            self._joueur, pose.adversaire_relatif, self.config.joueurs
        )
        zones = (
            Zone.banquet(pose.position),
            Zone.domaine(self._joueur),
            Zone.domaine(adversaire),
        )

        posees = [
            CartePosee(main[indice], zone, self._joueur)
            for indice, zone in zip(pose.indices_main, zones, strict=True)
        ]
        self._mains[self._joueur] = []
        self._posees.extend(posees)

        # L'ordre de cette liste EST l'ordre de resolution : banquet, domaine propre,
        # domaine adverse (paragraphe 3.2).
        self._assassins_en_attente = [
            posee for posee in posees if posee.carte.role in rules.ROLES_ASSASSINS
        ]
        self._phase = Phase.CIBLAGE if self._assassins_en_attente else Phase.POSE
        if self._phase is Phase.POSE:
            self._joueur_suivant()

    def _resoudre_assassin(self, action: int) -> None:
        """Tue la cible d'indice `action`, ou refuse si `action == len(cibles)`."""
        cibles = self.cibles_courantes()
        if action < len(cibles):
            victime = cibles[action]
            self._posees.remove(victime)
            self._defausse.append(victime)

        self._assassins_en_attente.pop(0)
        if not self._assassins_en_attente:
            self._phase = Phase.POSE
            self._joueur_suivant()

    def _joueur_suivant(self) -> None:
        """Passe la main, en arretant la partie avant un tour de table incomplet."""
        self._joueur = (self._joueur + 1) % self.config.joueurs
        if self._joueur == 0:
            self._tours_joues += 1
            if not rules.peut_entamer_un_tour_de_table(
                len(self._pioche), self.config.joueurs
            ):
                self._phase = Phase.TERMINAL
                return
        self._piocher()

    def _piocher(self) -> None:
        """Complete la main du joueur courant a trois cartes (paragraphe 3.3)."""
        tirees = self._pioche[:CARTES_PAR_TOUR]
        del self._pioche[:CARTES_PAR_TOUR]
        self._mains[self._joueur] = list(
            rules.main_canonique(self._mains[self._joueur] + tirees)
        )


class Engine:
    """Fabrique d'etats pour une configuration donnee."""

    def __init__(self, config: GameConfig) -> None:
        self.config = config

    def pioche_depuis_seed(self, seed: int) -> tuple[Carte, ...]:
        """L'ordre de pioche produit par un seed. **Seul effet du seed.**

        Une instance `Random` dediee, jamais le generateur global : deux parties lancees
        dans le meme processus ne doivent pas s'influencer.
        """
        cartes = list(rules.paquet(self.config))
        random.Random(seed).shuffle(cartes)
        return tuple(cartes)

    def reset(self, seed: int) -> State:
        """Une partie neuve, reproductible : meme seed, meme partie."""
        return self.reset_depuis_pioche(self.pioche_depuis_seed(seed))

    def reset_depuis_pioche(self, cartes: Sequence[Carte]) -> State:
        """Une partie neuve sur une pioche explicite, consommee dans l'ordre donne.

        Les `CARTES_PAR_TOUR` premieres cartes vont au joueur 0, les suivantes au joueur 1,
        et ainsi de suite (regle R-b). Leve si le multiensemble fourni n'est pas exactement
        le paquet de la configuration : sans ce controle, un test pourrait fabriquer un
        etat impossible et le certifier.
        """
        attendu = sorted(rules.paquet(self.config))
        if sorted(cartes) != attendu:
            raise ValueError(
                f"la pioche fournie n'est pas le paquet de la configuration : "
                f"{len(cartes)} cartes recues pour {self.config.nb_cartes} attendues"
            )
        etat = State(
            config=self.config,
            _pioche=list(cartes),
            _mains=[[] for _ in range(self.config.joueurs)],
        )
        etat._piocher()
        return etat

"""Enveloppe OpenSpiel du moteur.

**Le coeur ne connait pas cet adaptateur.** Il n'importe ni `pyspiel`, ni NumPy, ni rien
d'autre que la bibliotheque standard ; c'est ce module-ci qui importe `pyspiel`, et lui
seul. Un test d'import le verifie (critere A4).

Ce module **ne contient aucune regle**. Il traduit, et c'est tout : reecrire la machine a
etats ici aurait viole le paragraphe 2 des conventions, qui interdit deux implementations
d'une meme regle -- la faute exacte qui a propage un defaut entre quatre fichiers dans la
tentative precedente. La distribution par noeuds de chance vit donc dans `engine.py`, ou
elle partage tout le reste de la machine, et cet adaptateur se contente de l'exposer.

Deux entrees, comme decide le 16/08 :

  - `new_initial_state()` -- l'arbre de jeu au sens d'OpenSpiel, dont la racine est un
    noeud de chance et ou chaque carte tiree en est un ;
  - `reset(seed)` et `reset_depuis_pioche` -- la pioche fixee d'avance, pour le
    determinisme des tests et des parties de mesure.

Les identifiants d'action ne sont **pas** decales entre les phases : une pose et un
ciblage peuvent porter le meme numero, comme dans la plupart des jeux OpenSpiel a phases.
`num_distinct_actions` majore les deux espaces. C'est ce qui permet aux tests de
conformite de tourner a l'identique sur le coeur et a travers cet adaptateur, sans qu'une
seule ligne de test ne change.
"""

from __future__ import annotations

from collections.abc import Sequence

import pyspiel

from courtisans import rules
from courtisans.cards import Carte, Role
from courtisans.config import GameConfig
from courtisans.engine import Engine, Phase, State

NOM_COURT = "courtisans"

#: Valeurs par defaut des parametres, pour `pyspiel.load_game("courtisans")`.
PARAMETRES_PAR_DEFAUT = {
    "familles": 6,
    "exemplaires": 3,
    "joueurs": 3,
    "roles": ",".join(role.name for role in Role),
}


def config_depuis_parametres(parametres: dict) -> GameConfig:
    """Traduit les parametres OpenSpiel en `GameConfig`, qui valide le reste."""
    complets = {**PARAMETRES_PAR_DEFAUT, **(parametres or {})}
    roles = tuple(
        getattr(Role, nom.strip().upper()) for nom in str(complets["roles"]).split(",")
    )
    return GameConfig(
        familles=int(complets["familles"]),
        roles=roles,
        exemplaires=int(complets["exemplaires"]),
        joueurs=int(complets["joueurs"]),
    )


def _type_de_jeu() -> pyspiel.GameType:
    return pyspiel.GameType(
        short_name=NOM_COURT,
        long_name="Courtisans",
        dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
        chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
        information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
        utility=pyspiel.GameType.Utility.ZERO_SUM,
        reward_model=pyspiel.GameType.RewardModel.TERMINAL,
        max_num_players=4,
        min_num_players=2,
        provides_information_state_string=True,
        provides_information_state_tensor=True,
        provides_observation_string=False,
        provides_observation_tensor=False,
        parameter_specification=PARAMETRES_PAR_DEFAUT,
    )


def _info_de_jeu(config: GameConfig) -> pyspiel.GameInfo:
    """Les bornes de l'arbre, toutes derivees de la configuration.

    `num_distinct_actions` majore les deux espaces d'action : la pose et le ciblage. Une
    zone ne peut pas contenir plus de cartes que la partie n'en pose, d'ou la borne du
    ciblage : `cartes_jouees + 1`, le `+ 1` etant le refus de tuer.

    `max_game_length` compte au pire, par tour de joueur : trois tirages, une pose, et
    jusqu'a trois resolutions d'Assassin.
    """
    ciblage = config.cartes_jouees + 1
    return pyspiel.GameInfo(
        num_distinct_actions=max(config.actions_de_pose, ciblage),
        max_chance_outcomes=rules.nb_types_de_carte(config),
        num_players=config.joueurs,
        min_utility=-1.0,
        max_utility=1.0,
        utility_sum=0.0,
        max_game_length=7 * config.joueurs * config.tours,
    )


class CourtisansGame(pyspiel.Game):
    """Le jeu, au sens d'OpenSpiel. Enveloppe un `Engine` et n'ajoute aucune regle."""

    def __init__(self, params: dict | None = None, config: GameConfig | None = None):
        self.config = config if config is not None else config_depuis_parametres(params)
        self.moteur = Engine(self.config)
        super().__init__(_type_de_jeu(), _info_de_jeu(self.config), params or {})

    def new_initial_state(self) -> EtatCourtisans:
        """La racine de l'arbre : un noeud de chance, la premiere carte a distribuer."""
        return EtatCourtisans(self, self.moteur.reset_par_hasard())

    # -- Les trois entrees du coeur, pour que les memes tests tournent a travers -----

    def reset(self, seed: int) -> EtatCourtisans:
        """Une partie sur pioche fixee par un seed. Aucun noeud de chance."""
        return EtatCourtisans(self, self.moteur.reset(seed))

    def reset_depuis_pioche(self, cartes: Sequence[Carte]) -> EtatCourtisans:
        """Une partie sur pioche explicite. Aucun noeud de chance."""
        return EtatCourtisans(self, self.moteur.reset_depuis_pioche(cartes))

    def reset_par_hasard(self) -> EtatCourtisans:
        """Une partie dont chaque carte tiree est un noeud de chance."""
        return self.new_initial_state()

    def pioche_depuis_seed(self, seed: int) -> tuple[Carte, ...]:
        """L'ordre de pioche produit par un seed."""
        return self.moteur.pioche_depuis_seed(seed)

    def information_state_tensor_shape(self) -> list[int]:
        """La taille du tenseur, mesuree sur un etat neuf plutot que recalculee."""
        return [len(self.new_initial_state().information_state_tensor(0))]

    def information_state_tensor_size(self) -> int:
        return self.information_state_tensor_shape()[0]


class EtatCourtisans(pyspiel.State):
    """Un etat OpenSpiel qui delegue tout a un `State` du coeur."""

    def __init__(self, jeu: CourtisansGame, etat: State):
        super().__init__(jeu)
        self._jeu = jeu
        self._etat = etat

    # -- API OpenSpiel --------------------------------------------------------------

    def current_player(self) -> int:
        """Les identifiants du coeur sont deja ceux d'OpenSpiel : -1 hasard, -4 terminal."""
        return self._etat.current_player()

    def _legal_actions(self, player: int) -> list[int]:
        return sorted(self._etat.legal_actions())

    def chance_outcomes(self) -> list[tuple[int, float]]:
        return self._etat.chance_outcomes()

    def _apply_action(self, action: int) -> None:
        self._etat.apply(action)

    def _action_to_string(self, player: int, action: int) -> str:
        """Nom lisible d'une action, pour les traces et le debogage."""
        if player == pyspiel.PlayerId.CHANCE:
            famille, role = rules.decoder_type_carte(action, self._jeu.config)
            return f"tirage f{famille}-{role.name}"
        if self._etat.phase() is Phase.CIBLAGE:
            cibles = self._etat.cibles_courantes()
            if action == len(cibles):
                return "ne pas tuer"
            carte = cibles[action].carte
            return f"tuer f{carte.famille}-{carte.role.name}"
        pose = rules.decoder_action_pose(action, self._jeu.config)
        return (
            f"pose {pose.indices_main} {pose.position.name} "
            f"adversaire+{pose.adversaire_relatif + 1}"
        )

    def is_terminal(self) -> bool:
        return self._etat.is_terminal()

    def returns(self) -> list[float]:
        return self._etat.returns()

    def information_state_string(self, player: int | None = None) -> str:
        return self._etat.information_state_string(
            self.current_player() if player is None else player
        )

    def information_state_tensor(self, player: int | None = None) -> list[float]:
        return self._etat.information_state_tensor(
            self.current_player() if player is None else player
        )

    def clone(self) -> EtatCourtisans:
        return EtatCourtisans(self._jeu, self._etat.clone())

    def __str__(self) -> str:
        return self._etat.information_state_string(0)

    # -- API du coeur, pour que les memes tests tournent a travers --------------------

    def apply(self, action: int) -> None:
        """Alias de `apply_action`, sous le nom qu'emploie le coeur."""
        self.apply_action(action)

    def phase(self) -> Phase:
        return self._etat.phase()

    def scores(self) -> dict[int, int]:
        return self._etat.scores()

    def vue_privilegiee(self):  # noqa: ANN201 - le type vit dans engine
        return self._etat.vue_privilegiee()

    def cibles_courantes(self):  # noqa: ANN201
        return self._etat.cibles_courantes()

    def assassin_en_resolution(self):  # noqa: ANN201
        return self._etat.assassin_en_resolution()

    def assassins_en_attente(self):  # noqa: ANN201
        return self._etat.assassins_en_attente()

    def tours_restants(self, joueur: int) -> int:
        return self._etat.tours_restants(joueur)


def enregistrer() -> None:
    """Rend le jeu accessible par `pyspiel.load_game("courtisans")`.

    Idempotent : appeler deux fois ne leve pas. C'est necessaire parce que ce module peut
    etre importe plusieurs fois dans une meme session de test.
    """
    if NOM_COURT not in pyspiel.registered_names():
        pyspiel.register_game(_type_de_jeu(), CourtisansGame)


enregistrer()

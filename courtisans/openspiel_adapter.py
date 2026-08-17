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

import numpy as np
import pyspiel

from courtisans import rules
from courtisans.cards import Carte, Role
from courtisans.config import JOUEURS_AUTORISES, GameConfig
from courtisans.engine import Engine, Phase, State

NOM_COURT = "courtisans"

#: Ce qui separe les roles **a l'interieur** de la valeur du parametre `roles`.
#:
#: **Pas une virgule.** La grammaire d'OpenSpiel decoupe les parametres d'une chaine de jeu
#: sur la virgule : `courtisans(roles=ASSASSIN,GARDE)` est lu comme deux parametres, dont le
#: second s'appelle `GARDE`. Une liste jointe par des virgules produit donc une chaine que
#: la bibliotheque ne sait pas relire -- `Unknown parameter 'ESPION,NEUTRE)'` -- et casse
#: `load_game`, la serialisation, et tout ce qui distribue un jeu par son nom. Or retirer des
#: roles entiers est une reduction autorisee (paragraphe 8 des regles) : c'est le cas d'usage
#: normal d'une instance d'entrainement, pas un cas limite.
SEPARATEUR_ROLES = "-"

#: La configuration du jeu complet : 6 familles, les 5 roles, 3 exemplaires, 3 joueurs.
#: Construite, donc validee -- un defaut non conforme leverait au chargement du module.
CONFIG_PAR_DEFAUT = GameConfig(familles=6, roles=tuple(Role), exemplaires=3, joueurs=3)


def parametres_depuis_config(config: GameConfig) -> dict:
    """Les parametres OpenSpiel d'une configuration. L'inverse de `config_depuis_parametres`.

    **C'est ce qui rend `pyspiel.load_game(str(jeu))` fidele.** OpenSpiel construit la chaine
    d'un jeu depuis ses parametres, pas depuis son etat interne : un jeu construit par
    l'argument `config=` sans repasser par ici rendait `courtisans()`, et se rechargeait en
    jeu complet -- 6 familles au lieu de 4, sans que rien ne leve.
    """
    return {
        "familles": config.familles,
        "exemplaires": config.exemplaires,
        "joueurs": config.joueurs,
        "roles": SEPARATEUR_ROLES.join(role.name for role in config.roles),
    }


#: Valeurs par defaut des parametres, pour `pyspiel.load_game("courtisans")`. Derivees de
#: `CONFIG_PAR_DEFAUT`, jamais recopiees : deux ecritures du jeu complet pourraient diverger.
PARAMETRES_PAR_DEFAUT = parametres_depuis_config(CONFIG_PAR_DEFAUT)


def config_depuis_parametres(parametres: dict) -> GameConfig:
    """Traduit les parametres OpenSpiel en `GameConfig`, qui valide le reste."""
    complets = {**PARAMETRES_PAR_DEFAUT, **(parametres or {})}
    roles = tuple(
        getattr(Role, nom.strip().upper())
        for nom in str(complets["roles"]).split(SEPARATEUR_ROLES)
    )
    return GameConfig(
        familles=int(complets["familles"]),
        roles=roles,
        exemplaires=int(complets["exemplaires"]),
        joueurs=int(complets["joueurs"]),
    )


def _type_de_jeu() -> pyspiel.GameType:
    """Le type du jeu au sens d'OpenSpiel.

    Les bornes de joueurs sont **derivees** de `config.JOUEURS_AUTORISES`, jamais recopiees.
    Ecrire `max_num_players=4` en dur permettrait d'etendre l'un sans l'autre sans qu'aucun
    test ne le signale -- c'est la classe de faute que le paragraphe 3 des conventions
    interdit, et que `02_audit_conformite.md` designe comme cause racine de N1 et N3.
    """
    return pyspiel.GameType(
        short_name=NOM_COURT,
        long_name="Courtisans",
        dynamics=pyspiel.GameType.Dynamics.SEQUENTIAL,
        chance_mode=pyspiel.GameType.ChanceMode.EXPLICIT_STOCHASTIC,
        information=pyspiel.GameType.Information.IMPERFECT_INFORMATION,
        utility=pyspiel.GameType.Utility.ZERO_SUM,
        reward_model=pyspiel.GameType.RewardModel.TERMINAL,
        max_num_players=max(JOUEURS_AUTORISES),
        min_num_players=min(JOUEURS_AUTORISES),
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


#: Le seul type d'observation que ce jeu fournit : l'info-set. `perfect_recall=True`,
#: information publique incluse, information privee du seul joueur observe -- c'est la
#: definition d'`InformationState` dans `open_spiel/python/observation.py`.
#:
#: Le jeu declare `provides_observation_string=False` et `provides_observation_tensor=False`
#: (voir `_type_de_jeu`) : une observation **sans memoire** n'est pas specifiee. Le
#: paragraphe 4.2 de la specification decrit un seul etat expose au joueur, celui que
#: `infoset.py` produit, et ne dit rien de ce qu'un observateur sans memoire devrait
#: contenir. L'inventer serait exactement ce que le paragraphe 8 des conventions interdit.
TYPE_OBSERVATION_SUPPORTE = pyspiel.IIGObservationType(
    perfect_recall=True,
    public_info=True,
    private_info=pyspiel.PrivateInfoType.SINGLE_PLAYER,
)


def _est_le_type_supporte(iig_obs_type: pyspiel.IIGObservationType) -> bool:
    """Vrai si le type demande est exactement celui de l'info-set.

    Les trois champs sont compares un a un : `IIGObservationType` n'a pas d'egalite
    structurelle utilisable. Le controle sur `private_info` n'est pas cosmetique --
    `ALL_PLAYERS` demande l'information privee de **tous** les joueurs, ce qu'un
    observateur de ce jeu ne peut pas rendre sans violer l'invariant I7.
    """
    return (
        iig_obs_type.perfect_recall == TYPE_OBSERVATION_SUPPORTE.perfect_recall
        and iig_obs_type.public_info == TYPE_OBSERVATION_SUPPORTE.public_info
        and iig_obs_type.private_info == TYPE_OBSERVATION_SUPPORTE.private_info
    )


class ObservateurInfoState:
    """L'observateur au sens d'OpenSpiel. Il n'observe rien de plus qu'`infoset.py`.

    OpenSpiel a deux facons de lire un etat : les methodes `information_state_*` de l'etat,
    et un **observateur** rendu par `Game.make_py_observer`. Les algorithmes de la
    bibliotheque -- et son propre harnais de validite, `random_sim_test` -- passent par le
    second. Sans lui, le jeu n'est pas un jeu OpenSpiel complet, et la validite annoncee
    par les tests de l'adaptateur n'etait etablie que par des controles ecrits a la main.

    **Aucune observation nouvelle n'est definie ici.** `set_from` et `string_from`
    delegurent aux deux memes fonctions d'`infoset.py` que l'etat : une seule source de
    verite, donc rien qui puisse diverger (paragraphe 2 des conventions). En particulier,
    `player` traverse cet objet sans etre substitue ni corrige -- le coeur le valide.
    """

    def __init__(
        self,
        jeu: CourtisansGame,
        iig_obs_type: pyspiel.IIGObservationType,
        params: dict | None,
    ) -> None:
        if params:
            raise ValueError(f"aucun parametre d'observation n'est supporte, recu {params}")
        if not _est_le_type_supporte(iig_obs_type):
            raise ValueError(
                f"seule l'observation d'info-set est fournie (perfect_recall=True, "
                f"public_info=True, private_info=SINGLE_PLAYER), demande "
                f"perfect_recall={iig_obs_type.perfect_recall}, "
                f"public_info={iig_obs_type.public_info}, "
                f"private_info={iig_obs_type.private_info} -- une observation sans memoire "
                f"n'est pas specifiee, et l'information privee de tous les joueurs violerait "
                f"l'invariant I7"
            )
        self.tensor = np.zeros(jeu.information_state_tensor_size(), np.float32)
        #: Un seul bloc plat. La disposition detaillee, bloc par bloc, est celle
        #: d'`infoset.disposition` : la redecouper ici en ferait une seconde description.
        self.dict = {"info_state": self.tensor}

    def set_from(self, state: EtatCourtisans, player: int) -> None:
        """Remplit le tenseur avec la vue de `player`. Leve si `player` n'est pas un joueur."""
        self.tensor[:] = state.information_state_tensor(player)

    def string_from(self, state: EtatCourtisans, player: int) -> str:
        """La vue de `player`, en chaine. Leve si `player` n'est pas un joueur."""
        return state.information_state_string(player)


class CourtisansGame(pyspiel.Game):
    """Le jeu, au sens d'OpenSpiel. Enveloppe un `Engine` et n'ajoute aucune regle."""

    def __init__(self, params: dict | None = None, config: GameConfig | None = None):
        self.config = config if config is not None else config_depuis_parametres(params)
        self.moteur = Engine(self.config)
        # Les parametres transmis a OpenSpiel sont **toujours** ceux de la configuration
        # effective, jamais ceux recus. C'est ce qui fait de `str(jeu)` une description
        # fidele et complete du jeu, donc de `load_game(str(jeu))` le meme jeu : les deux
        # chemins de construction -- `params=` et `config=` -- convergent ici.
        super().__init__(
            _type_de_jeu(), _info_de_jeu(self.config), parametres_depuis_config(self.config)
        )

    def new_initial_state(self) -> EtatCourtisans:
        """La racine de l'arbre : un noeud de chance, la premiere carte a distribuer."""
        return EtatCourtisans(self, self.moteur.reset_par_hasard())

    def make_py_observer(
        self,
        iig_obs_type: pyspiel.IIGObservationType | None = None,
        params: dict | None = None,
    ) -> ObservateurInfoState:
        """L'observateur qu'attendent les algorithmes d'OpenSpiel et son harnais de validite.

        `iig_obs_type` omis vaut l'info-set : c'est la seule observation que ce jeu
        fournit. Tout autre type est refuse, avec le detail du refus -- voir
        `ObservateurInfoState`.
        """
        return ObservateurInfoState(
            self, iig_obs_type or TYPE_OBSERVATION_SUPPORTE, params
        )

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
        """Nom lisible d'une action, pour les traces et le debogage.

        **Deux actions legales distinctes doivent porter deux noms distincts** : OpenSpiel
        l'exige, et son harnais `random_sim_test` le verifie. En phase de ciblage, deux
        exemplaires du meme couple (famille, role) dans une meme zone sont deux cibles
        distinctes -- le controle C15 exige `nb_cibles + 1` actions legales, donc on ne les
        masque pas, contrairement aux actions de pose. Le nom porte donc l'indice de la
        cible, qui est precisement ce que l'action designe.
        """
        if player == pyspiel.PlayerId.CHANCE:
            famille, role = rules.decoder_type_carte(action, self._jeu.config)
            return f"tirage f{famille}-{role.name}"
        if self._etat.phase() is Phase.CIBLAGE:
            cibles = self._etat.cibles_courantes()
            if action == len(cibles):
                return "ne pas tuer"
            carte = cibles[action].carte
            return f"tuer la cible {action} : f{carte.famille}-{carte.role.name}"
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
        """La vue de `player` ; omis, celle du joueur courant.

        **Le defaut est conserve, mais il n'est plus une echappatoire.** C'est le motif
        d'appel de toute la bibliotheque -- 34 appels `information_state_string()` sans
        argument dans `open_spiel/python`, dont `policy.py:309`, `algorithms/best_response.py`
        qui porte l'exploitabilite, et `jax/cfr/jax_cfr.py`. Le supprimer ne corrigeait pas
        le defaut : il le remplacait par un `TypeError` sur un noeud de decision valide.

        Ce qui manquait n'etait pas le defaut, c'etait la **validation** de ce qu'il
        substitue. `current_player()` vaut -1 sur un noeud de chance et -4 au terminal ;
        `engine.State` refuse desormais l'un comme l'autre, donc l'appel sans argument rend
        une vue exactement la ou un joueur decide, et leve partout ailleurs.
        """
        return self._etat.information_state_string(
            self.current_player() if player is None else player
        )

    def information_state_tensor(self, player: int | None = None) -> list[float]:
        """La vue de `player` en vecteur ; omis, celle du joueur courant. Meme regle."""
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

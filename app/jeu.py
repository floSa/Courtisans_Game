"""Moteur du jeu Courtisans.

Module garant des règles. Aucune logique d'IA n'est présente ici.
"""

from __future__ import annotations

import copy
import logging
import random
from enum import IntEnum
from itertools import permutations

import numpy as np

logger = logging.getLogger(__name__)

# ======================================================================================
# 1. CONFIGURATION & CONSTANTES
# ======================================================================================
NUM_FAMILLES = 6
NUM_ROLES = 5
NUM_CARD_TYPES = NUM_FAMILLES * NUM_ROLES

# Reward scaling : on divise les écarts de score par cette constante pour ramener
# la value dans [-1, 1] (cf. tanh en sortie du réseau).
REWARD_SCALE = 20.0


class Famille(IntEnum):
    F1 = 0
    F2 = 1
    F3 = 2
    F4 = 3
    F5 = 4
    F6 = 5


class Role(IntEnum):
    ASSASSIN = 0
    GARDE = 1
    NOBLE = 2
    ESPION = 3
    NEUTRE = 4


class Zone(IntEnum):
    REINE = 0
    SOI = 1
    ADV = 2


# ======================================================================================
# 2. LOGIQUE DE JEU
# ======================================================================================
class Carte:
    """Représente une carte unique du paquet (3 exemplaires par couple famille/role).

    Champs :
      - `famille`, `role`, `id`, `valeur` : identité de la carte.
      - `visible` : True si la carte est posée face visible (vue par tous).
        Seuls les espions se posent face cachée.
      - `position` : "Estime" / "Disgrace" si chez la Reine, sinon None.
      - `domaine_id` : index du joueur dans le domaine duquel est posée la
        carte (-1 pour Reine / Deck). **C'est ce champ qui détermine le
        scoring** (couplé à la majorité Estime/Disgrace de la famille).
      - `proprietaire_idx` : index du joueur qui a **posé** la carte
        (-1 tant qu'elle est dans la pioche). Utilisé pour :
          * Affichage Streamlit (le joueur courant voit ses propres
            espions face visible).
          * Mémoire interne de l'IA des espions qu'elle a posés.
          * Ciblage d'assassin (l'IA peut distinguer mes espions de ceux
            de l'adversaire).
        N'intervient PAS dans le calcul des points.
    """

    __slots__ = (
        "famille",
        "role",
        "id",
        "valeur",
        "proprietaire_idx",
        "visible",
        "position",
        "domaine_id",
        "sort_key",
    )

    def __init__(self, famille: int, role: int, uid: int) -> None:
        self.famille = famille
        self.role = role
        self.id = uid
        self.valeur = 2 if role == Role.NOBLE else 1
        self.proprietaire_idx = -1  # -1 tant que la carte est en pioche
        self.visible = False
        self.position: str | None = None  # 'Estime', 'Disgrace' pour Reine
        self.domaine_id = -1

        # Pour le tri stable (déterminisme de la main)
        self.sort_key = (famille * NUM_ROLES) + role

    @property
    def vector_id(self) -> int:
        return self.famille * NUM_ROLES + self.role

    def __repr__(self) -> str:
        return f"[{Famille(self.famille).name}-{Role(self.role).name}]"

    def copy(self) -> Carte:
        c = Carte(self.famille, self.role, self.id)
        c.proprietaire_idx = self.proprietaire_idx
        c.visible = self.visible
        c.position = self.position
        c.domaine_id = self.domaine_id
        return c


class ActionMapper:
    """Mappe un index d'action unique (pour l'IA) à la sémantique du jeu.

    Structure de l'action :
      1. Permutation des 3 cartes en main : 6 possibilités (Reine, Soi, Adv).
      2. Choix Reine : Estime (0) ou Disgrâce (1) → 2 possibilités.
      3. Choix Cible adversaire : index relatif parmi les N−1 adversaires.

    Total = 6 × 2 × (N − 1).
    """

    QUEEN_POSITIONS = ("Estime", "Disgrace")

    def __init__(self, num_players: int) -> None:
        self.num_players = num_players
        self.perms: list[tuple[int, int, int]] = list(permutations([0, 1, 2]))
        # Table d'inversion permutation → index
        self._perm_to_idx = {p: i for i, p in enumerate(self.perms)}

    def get_action_space_size(self) -> int:
        return 6 * 2 * (self.num_players - 1)

    def decode(self, action_idx: int) -> tuple[tuple[int, int, int], str, int]:
        nb_adv = self.num_players - 1
        target_relative_idx = action_idx % nb_adv
        remainder = action_idx // nb_adv

        queen_pos_idx = remainder % 2
        queen_pos = self.QUEEN_POSITIONS[queen_pos_idx]
        remainder = remainder // 2

        perm_idx = remainder % 6
        perm = self.perms[perm_idx]

        return perm, queen_pos, target_relative_idx

    def encode(
        self,
        perm: tuple[int, int, int],
        queen_pos: str,
        target_relative_idx: int = 0,
    ) -> int:
        """Inverse de `decode`. Lève ValueError si les arguments sont invalides."""
        if perm not in self._perm_to_idx:
            raise ValueError(f"Permutation invalide : {perm}")
        if queen_pos not in self.QUEEN_POSITIONS:
            raise ValueError(f"queen_pos doit être 'Estime' ou 'Disgrace', reçu {queen_pos!r}")
        nb_adv = self.num_players - 1
        if not 0 <= target_relative_idx < nb_adv:
            raise ValueError(f"target_relative_idx hors bornes : {target_relative_idx}")

        perm_idx = self._perm_to_idx[perm]
        queen_pos_idx = self.QUEEN_POSITIONS.index(queen_pos)
        return ((perm_idx * 2) + queen_pos_idx) * nb_adv + target_relative_idx


class GameEnv:
    """État du jeu Courtisans et règles de transition.

    Note sur la fin de partie : la partie se termine lorsque la pioche est vide
    **et** que plus aucun joueur n'a de cartes en main. Le reward final est
    calculé via `_calcul_scores`.

    Note sur les assassins multiples dans un même tour :
        - Pour les bots, tous les assassins joués dans le tour sont résolus
          séquentiellement (auto-résolution).
        - Pour le joueur humain, la résolution se fait en chaîne via plusieurs
          appels successifs à `resolve_assassin_manual` (un assassin à la fois).
    """

    def __init__(self, num_players: int = 2, seed: int | None = None) -> None:
        self.num_players = num_players
        self.mapper = ActionMapper(num_players)
        self.pending_assassin_context: dict | None = None
        # File d'attente des assassins du joueur humain restant à résoudre dans le tour
        self._pending_assassins_queue: list[Carte] = []
        self._rng: random.Random = random.Random(seed) if seed is not None else random.Random()
        self.reset()

    def reset(self) -> GameEnv:
        # Création Deck (3 exemplaires de chaque carte)
        self.cartes: list[Carte] = []
        uid = 0
        for _ in range(3):
            for f in range(NUM_FAMILLES):
                for r in range(NUM_ROLES):
                    self.cartes.append(Carte(f, r, uid))
                    uid += 1

        self.deck_indices = list(range(len(self.cartes)))
        self._rng.shuffle(self.deck_indices)
        self.plateau_indices: list[int] = []
        self.current_player = 0
        self.mains: dict[int, list[int]] = {i: [] for i in range(self.num_players)}
        self._piocher(self.current_player)
        return self

    # ------------------------------------------------------------------ helpers
    def _piocher(self, p_idx: int) -> None:
        """Complète la main du joueur jusqu'à 3 cartes (ou moins si pioche vide)."""
        needed = 3 - len(self.mains[p_idx])
        for _ in range(needed):
            if self.deck_indices:
                self.mains[p_idx].append(self.deck_indices.pop())
        # Tri obligatoire : la main est toujours vue triée par l'IA et l'ActionMapper.
        self.mains[p_idx].sort(key=lambda idx: self.cartes[idx].sort_key)

    def get_legal_actions(self) -> list[int]:
        if len(self.mains[self.current_player]) < 3:
            return []
        return list(range(self.mapper.get_action_space_size()))

    def is_done(self) -> bool:
        """Partie terminée.

        Critères (dans l'ordre) :
          1. Si la pioche n'est pas vide → la partie continue.
          2. Si la pioche est vide et toutes les mains sont vides → terminé.
          3. Si la pioche est vide et le joueur courant ne peut plus former
             un tour complet (< 3 cartes) → terminé (cartes résiduelles
             défaussées).
        """
        if self.deck_indices:
            return False
        if not any(self.mains.values()):
            return True
        return len(self.mains[self.current_player]) < 3

    # -------------------------------------------------------------------- step
    def step(self, action_idx: int) -> tuple[np.ndarray, float, bool, dict]:
        """Joue un tour complet. action_idx : int entre 0 et action_space_size."""
        perm, queen_pos, target_relative_idx = self.mapper.decode(action_idx)

        hand_indices = self.mains[self.current_player]
        if len(hand_indices) < 3:
            return self.get_state_vector(), 0.0, True, {}

        c_reine_idx = hand_indices[perm[0]]
        c_soi_idx = hand_indices[perm[1]]
        c_adv_idx = hand_indices[perm[2]]
        target_abs_idx = (self.current_player + 1 + target_relative_idx) % self.num_players

        # --- APPLICATION REINE ---
        # Un espion posé chez la Reine reste face cachée (règle officielle).
        # `proprietaire_idx` = joueur qui a posé la carte (info utile pour
        # l'affichage et la mémoire des espions, pas pour le scoring).
        c_reine = self.cartes[c_reine_idx]
        c_reine.position = queen_pos
        c_reine.visible = c_reine.role != Role.ESPION
        c_reine.proprietaire_idx = self.current_player
        c_reine.domaine_id = -1  # chez la Reine, pas dans un domaine
        self.plateau_indices.append(c_reine_idx)

        # --- APPLICATION SOI ---
        c_soi = self.cartes[c_soi_idx]
        c_soi.domaine_id = self.current_player
        c_soi.position = None
        c_soi.proprietaire_idx = self.current_player
        c_soi.visible = c_soi.role != Role.ESPION
        self.plateau_indices.append(c_soi_idx)

        # --- APPLICATION ADV ---
        # La carte va dans le domaine de target_abs_idx (scoring), mais
        # c'est le joueur courant qui l'a posée (proprietaire_idx).
        c_adv = self.cartes[c_adv_idx]
        c_adv.domaine_id = target_abs_idx
        c_adv.position = None
        c_adv.proprietaire_idx = self.current_player
        c_adv.visible = c_adv.role != Role.ESPION
        self.plateau_indices.append(c_adv_idx)

        self.mains[self.current_player] = []

        # --- EFFETS ASSASSIN ---
        # Le moteur enfile TOUS les assassins joués et raise `assassin_pending`
        # pour le premier, peu importe qui joue. C'est au caller de résoudre
        # la chaîne avec sa stratégie : MCTS (via mcts.search en mode target),
        # heuristique (`resolve_pending_with_heuristic`), UI humaine, etc.
        assassins_joues = [c for c in (c_reine, c_soi, c_adv) if c.role == Role.ASSASSIN]
        if assassins_joues:
            self._pending_assassins_queue = list(assassins_joues)
            return self._raise_first_pending_assassin()

        return self._finish_turn()

    def _raise_first_pending_assassin(self) -> tuple[np.ndarray, float, bool, dict]:
        """Met en pause le tour et expose le premier assassin de la file."""
        while self._pending_assassins_queue:
            ass = self._pending_assassins_queue[0]
            targets = self._get_valid_assassin_targets(ass)
            if not targets:
                # Pas de cible → on saute cet assassin.
                self._pending_assassins_queue.pop(0)
                continue
            self.pending_assassin_context = {"assassin_card": ass, "targets": targets}
            return self.get_state_vector(), 0.0, False, {"assassin_pending": True}
        # Plus d'assassin à résoudre → on termine le tour.
        self.pending_assassin_context = None
        return self._finish_turn()

    def resolve_assassin_manual(
        self, victim_idx: int | None
    ) -> tuple[np.ndarray, float, bool, dict]:
        """Résout l'assassin en attente. `victim_idx=None` ou hors cibles → skip."""
        if not self.pending_assassin_context:
            logger.warning("resolve_assassin_manual appelé sans assassin en attente")
            return self.get_state_vector(), 0.0, self.is_done(), {}

        targets = self.pending_assassin_context["targets"]
        if victim_idx is not None and victim_idx in targets:
            self.plateau_indices.remove(victim_idx)

        # On retire l'assassin résolu de la file et on passe au suivant.
        if self._pending_assassins_queue:
            self._pending_assassins_queue.pop(0)
        self.pending_assassin_context = None
        return self._raise_first_pending_assassin()

    def _finish_turn(self) -> tuple[np.ndarray, float, bool, dict]:
        done = self.is_done()
        reward = 0.0
        if done:
            self._reveal_spies()
            scores = self._calcul_scores()
            if self.num_players == 2:
                reward = (scores[0] - scores[1]) / REWARD_SCALE
            else:
                my_score = scores[self.current_player]
                avg_others = sum(s for i, s in scores.items() if i != self.current_player) / (
                    self.num_players - 1
                )
                reward = (my_score - avg_others) / REWARD_SCALE

        if not done:
            self.current_player = (self.current_player + 1) % self.num_players
            self._piocher(self.current_player)

        return self.get_state_vector(), reward, done, {}

    # ---------------------------------------------------------------- assassins
    def _get_valid_assassin_targets(self, assassin_card: Carte) -> list[int]:
        """Cartes pouvant être tuées par `assassin_card`.

        Règles :
          - On ne se tue pas soi-même (`c.id == assassin_card.id`).
          - Seul le **Garde** est immunisé (un assassin peut tuer un autre
            assassin).
          - L'assassin tue dans sa propre zone (même position Reine, ou
            même domaine de joueur).
        """
        targets: list[int] = []
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.id == assassin_card.id:
                continue
            if c.role == Role.GARDE:
                continue

            match = False
            if assassin_card.position is not None:
                if c.position == assassin_card.position:
                    match = True
            elif assassin_card.domaine_id != -1:
                if c.domaine_id == assassin_card.domaine_id:
                    match = True

            if match:
                targets.append(i)
        return targets

    def _pick_target_heuristic(
        self, assassin_card: Carte, targets: list[int]
    ) -> int | None:
        """Heuristique B1 — choisit la cible qui maximise l'avantage de score
        du joueur ayant posé l'assassin. Tie-break aléatoire. Renvoie l'id
        de la cible, ou None si la liste est vide / pas de poseur connu.
        """
        if not targets:
            return None

        assassin_player = assassin_card.proprietaire_idx
        if assassin_player < 0:
            # Sécurité : si on ne sait pas qui a posé, on retombe sur random.
            return self._rng.choice(targets)

        best_advantage = -float("inf")
        candidates: list[int] = []
        for victim_id in targets:
            # Évaluation "et si on retire victim_id ?"
            self.plateau_indices.remove(victim_id)
            scores = self._calcul_scores()
            advantage = self._player_advantage(scores, assassin_player)
            self.plateau_indices.append(victim_id)

            if advantage > best_advantage:
                best_advantage = advantage
                candidates = [victim_id]
            elif advantage == best_advantage:
                candidates.append(victim_id)

        return self._rng.choice(candidates)

    def _resolve_assassin_auto(self, assassin_card: Carte) -> None:
        """Résout un assassin avec l'heuristique B1. Utilisé en tests ou
        comme fallback hors-MCTS. Le code de jeu principal passe désormais
        par `resolve_pending_with_heuristic`."""
        targets = self._get_valid_assassin_targets(assassin_card)
        victim = self._pick_target_heuristic(assassin_card, targets)
        if victim is not None:
            self.plateau_indices.remove(victim)

    def resolve_pending_with_heuristic(self) -> tuple[np.ndarray, float, bool, dict]:
        """Résout TOUS les assassins pending en chaîne avec l'heuristique B1.

        Pour les callers qui ne veulent pas piloter le ciblage eux-mêmes
        (tests, Streamlit AI sans MCTS, fallback). Le caller MCTS lui-même
        boucle sur `resolve_assassin_manual` après ses propres décisions.
        """
        if not self.pending_assassin_context:
            return self.get_state_vector(), 0.0, self.is_done(), {}
        last_ret: tuple[np.ndarray, float, bool, dict] = (
            self.get_state_vector(),
            0.0,
            self.is_done(),
            {},
        )
        while self.pending_assassin_context:
            ctx = self.pending_assassin_context
            assassin = ctx["assassin_card"]
            targets = ctx["targets"]
            victim = self._pick_target_heuristic(assassin, targets) if targets else None
            last_ret = self.resolve_assassin_manual(victim)
        return last_ret

    @staticmethod
    def _player_advantage(scores: dict[int, int], player: int) -> float:
        """Avantage du joueur `player` = son score moins la moyenne des autres."""
        if player not in scores:
            return 0.0
        others = [v for k, v in scores.items() if k != player]
        if not others:
            return float(scores[player])
        return float(scores[player] - sum(others) / len(others))

    # ------------------------------------------------------------------ scoring
    def _reveal_spies(self) -> None:
        """Révèle tous les espions encore cachés sur le plateau (fin de partie)."""
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.role == Role.ESPION:
                c.visible = True

    def _calcul_scores(self) -> dict[int, int]:
        # 1. Influence des familles (majorité estime/disgrâce).
        infl = {f: 0 for f in range(NUM_FAMILLES)}
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.position == "Estime":
                infl[c.famille] += 1
            elif c.position == "Disgrace":
                infl[c.famille] -= 1

        # 2. Points par joueur. Tous les espions sont comptés en fin de partie
        # (révélés par _reveal_spies).
        scores = {p: 0 for p in range(self.num_players)}
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.domaine_id == -1:
                continue
            fam_stat = infl[c.famille]
            val = c.valeur
            if fam_stat > 0:
                scores[c.domaine_id] += val
            elif fam_stat < 0:
                scores[c.domaine_id] -= val

        return scores

    # ---------------------------------------------------------------- encoding
    def _knows_identity(self, c: Carte) -> bool:
        """Le joueur courant connaît-il l'identité réelle de cette carte ?

        Une carte est "connue" du joueur courant si :
          - elle est face visible (vue de tous), OU
          - elle a été posée par le joueur courant (mémoire des espions
            via `proprietaire_idx`).
        """
        return c.visible or c.proprietaire_idx == self.current_player

    # Taille de la partie "permutable par symétrie de familles" du state_vector.
    # Section 1 : (Reine Estime + Reine Disgrâce + N domaines + main du joueur)
    # × NUM_CARD_TYPES.
    def _permutable_section_size(self) -> int:
        total_zones = 2 + self.num_players + 1  # +1 pour la main
        return total_zones * NUM_CARD_TYPES

    # Section 2 (non permutable) : compteurs d'espions cachés par (zone, poseur).
    def _hidden_spy_section_size(self) -> int:
        # zones : Estime, Disgrace, et N domaines. Pas la main (pas d'espions
        # cachés en main pendant qu'on joue).
        num_zones = 2 + self.num_players
        return num_zones * self.num_players

    def _hidden_spy_counts(self) -> np.ndarray:
        """Renvoie un vecteur aplati de shape (num_zones × num_players,).

        Chaque cellule `(z, p_rel)` = nombre d'espions face cachée dans la
        zone `z`, posés par le joueur relatif `p_rel` (relatif au
        `current_player`). Zones :
          z=0 : Reine Estime
          z=1 : Reine Disgrâce
          z=2 + rel_owner : domaine du joueur dont rel_owner est l'index
                            relatif (z=2 = moi).
        """
        num_zones = 2 + self.num_players
        counts = np.zeros((num_zones, self.num_players), dtype=np.float32)
        for i in self.plateau_indices:
            c = self.cartes[i]
            if c.role != Role.ESPION or c.visible:
                continue
            # Type de zone
            if c.position == "Estime":
                z = 0
            elif c.position == "Disgrace":
                z = 1
            elif c.domaine_id != -1:
                z = 2 + (c.domaine_id - self.current_player) % self.num_players
            else:
                continue
            # Poseur relatif (0 = moi, 1 = adv suivant, ...).
            if c.proprietaire_idx < 0:
                continue
            rel_placer = (c.proprietaire_idx - self.current_player) % self.num_players
            counts[z, rel_placer] += 1
        return counts.flatten()

    def get_state_vector(self) -> np.ndarray:
        """Encodage de l'état pour le réseau de neurones.

        Structure du vecteur (deux sections) :

        SECTION 1 — Counts par type (famille × rôle), permutable par σ familles :
          - zone 0 : Reine — Estime
          - zone 1 : Reine — Disgrâce
          - zone 2..N+1 : domaines (rel : 2 = moi, 3 = adv suivant, …)
          - zone N+2 : main du joueur courant

        SECTION 2 — Compteurs d'espions cachés par (zone, poseur relatif) :
          Pour chaque (zone, joueur relatif), nb d'espions face cachée que
          ce joueur a posés dans cette zone. Cette section donne au réseau
          le signal "il y a N espions cachés posés par tel joueur dans Estime"
          sans révéler leur identité.

        Une carte n'est ENCODÉE PAR FAMILLE (section 1) que si le joueur
        courant en connaît l'identité (`_knows_identity`). Mais SON
        EXISTENCE et SON POSEUR sont toujours capturés en section 2 pour
        les espions cachés.
        """
        total_zones = 2 + 1 + (self.num_players - 1)
        permutable_size = self._permutable_section_size()

        vec = np.zeros(permutable_size + self._hidden_spy_section_size(), dtype=np.float32)

        def fill(offset_zone: int, card_vec_id: int) -> None:
            vec[offset_zone * NUM_CARD_TYPES + card_vec_id] += 1

        # --- Section 1 : identités connues du joueur courant ---
        for i in self.plateau_indices:
            c = self.cartes[i]
            if not self._knows_identity(c):
                continue
            vid = c.vector_id
            if c.position == "Estime":
                fill(0, vid)
            elif c.position == "Disgrace":
                fill(1, vid)
            elif c.domaine_id != -1:
                rel_owner = (c.domaine_id - self.current_player) % self.num_players
                zone_idx = 2 + rel_owner
                fill(zone_idx, vid)

        # Main du joueur courant
        main_zone_idx = total_zones
        for i in self.mains[self.current_player]:
            c = self.cartes[i]
            fill(main_zone_idx, c.vector_id)

        # --- Section 2 : compteurs d'espions cachés par (zone, poseur) ---
        vec[permutable_size:] = self._hidden_spy_counts()

        return vec

    def get_state_vector_size(self) -> int:
        return self._permutable_section_size() + self._hidden_spy_section_size()

    # ---------------------------------------------------------------- MCTS hook
    def clone_determinized(self, randomize: bool = True) -> GameEnv:
        """Déterminisation PIMC pour la simulation MCTS.

        Construit un clone profond, puis (si `randomize=True`) re-mélange les
        identités (`famille`, `role`) des cartes que le joueur courant ne
        peut pas voir :

          - cartes en main des autres joueurs ;
          - cartes face cachée que le joueur courant n'a PAS posées
            (espions adverses, peu importe la zone — Reine ou domaine) ;
          - cartes encore dans la pioche.

        Contrainte de cohérence : toute carte face cachée sur le plateau
        est un espion (les autres rôles se posent face visible), donc ces
        slots reçoivent forcément une identité `Role.ESPION` lors de la
        randomisation.

        Mettre `randomize=False` permet de cloner sans toucher aux identités
        (utile pour les tests d'invariants).
        """
        clone = copy.deepcopy(self)
        if randomize:
            clone._randomize_unseen(perspective=self.current_player)
        return clone

    def _randomize_unseen(self, perspective: int) -> None:
        """Permute les identités des cartes non vues par `perspective`.

        Critère "non vue" : `not c.visible AND c.proprietaire_idx != perspective`.
        Le joueur courant garde donc la connaissance de l'identité de
        TOUS les espions qu'il a posés, peu importe la zone (Reine,
        domaine adverse, ou son propre domaine).
        """
        # 1. Slots cachés sur le plateau : forcément des espions par la règle
        # (seuls les espions se posent face cachée).
        hidden_plateau: list[int] = []
        for i in self.plateau_indices:
            c = self.cartes[i]
            if not c.visible and c.proprietaire_idx != perspective:
                hidden_plateau.append(i)

        # 2. Mains adverses et pioche : identités libres.
        other_unseen: list[int] = []
        for p, hand in self.mains.items():
            if p != perspective:
                other_unseen.extend(hand)
        other_unseen.extend(self.deck_indices)

        if not hidden_plateau and not other_unseen:
            return

        # 3. Récupérer les identités actuellement à ces slots.
        identities = [
            (self.cartes[i].famille, self.cartes[i].role)
            for i in (hidden_plateau + other_unseen)
        ]

        # 4. Partition espions / non-espions.
        espions = [t for t in identities if t[1] == Role.ESPION]
        non_espions = [t for t in identities if t[1] != Role.ESPION]

        # Par construction, le nb d'espions dans le pool inconnu est >= au nb
        # de slots "face cachée" (qui contenaient eux-mêmes des espions avant
        # la deepcopy).
        assert len(espions) >= len(hidden_plateau), (
            f"Pool espions insuffisant : {len(espions)} pour {len(hidden_plateau)} slots"
        )

        rng = random.Random()
        rng.shuffle(espions)
        rng.shuffle(non_espions)

        # 5. Assigner les K premiers espions aux slots face cachée du plateau.
        for slot, ident in zip(hidden_plateau, espions[: len(hidden_plateau)], strict=True):
            self._set_card_identity(slot, ident)

        # 6. Mélanger le reste (espions restants + non-espions) et l'assigner
        # aux mains adverses + pioche.
        remaining = espions[len(hidden_plateau) :] + non_espions
        rng.shuffle(remaining)
        for slot, ident in zip(other_unseen, remaining, strict=True):
            self._set_card_identity(slot, ident)

        # 6. Re-trier les mains adverses (le sort_key a changé).
        for p in self.mains:
            if p != perspective:
                self.mains[p].sort(key=lambda idx: self.cartes[idx].sort_key)

    def _set_card_identity(self, card_idx: int, identity: tuple[int, int]) -> None:
        """Remplace (famille, role) d'une carte. Met à jour valeur et sort_key."""
        fam, role = identity
        c = self.cartes[card_idx]
        c.famille = fam
        c.role = role
        c.valeur = 2 if role == Role.NOBLE else 1
        c.sort_key = (fam * NUM_ROLES) + role


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    env = GameEnv(num_players=2, seed=42)
    logger.info("Action space size (2p): %d", env.mapper.get_action_space_size())
    logger.info("State vector size: %d", env.get_state_vector_size())

    s, r, d, _ = env.step(0)
    logger.info("Step done. Reward: %.3f, Done: %s", r, d)

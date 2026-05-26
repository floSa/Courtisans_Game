"""Implémentation AlphaZero-like (MCTS + ResNet) pour Courtisans."""

from __future__ import annotations

import logging
import os
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from app.augmentation import augment_sample, augment_target_sample
from app.jeu import GameEnv

logger = logging.getLogger(__name__)

# ======================================================================================
# CONFIGURATION
# ======================================================================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


@dataclass
class TrainConfig:
    """Hyper-paramètres centralisés pour l'entraînement self-play."""

    num_players: int = 2
    iterations: int = 100
    num_sims: int = 50  # L1#1.2 : 30 -> 50 (meilleurs labels MCTS)
    c_puct: float = 1.5
    lr: float = 1e-3
    weight_decay: float = 1e-4  # L1#1.4 : AdamW regularization
    memory_size: int = 50_000  # L1#1.1 : 5k -> 50k (moins de stale samples)
    batch_size: int = 64
    # Exploration (L1#1.3 — température schedule par-coup)
    # Pendant les `temperature_threshold` premiers coups d'une partie, on
    # échantillonne selon les visites MCTS (T=1) ; au-delà, argmax (T -> 0).
    temperature_threshold: int = 10
    dirichlet_alpha: float = 0.3
    dirichlet_epsilon: float = 0.25
    # L2#2.1 : nb de déterminisations agrégées par appel MCTS.search().
    # 1 = PIMC simple (un seul monde). >1 = PIMC multi (moins de variance,
    # coût compute linéaire). Pour Courtisans, viser 3-5 sur CPU.
    num_worlds: int = 1
    # L2#2.2 : augmentation par symétrie des familles.
    # Si True, chaque sample tiré du buffer pendant l'optimisation est
    # multiplié par une permutation aléatoire des 6 familles (state + policy
    # sont remappés en cohérence). Coût : négligeable.
    family_augmentation: bool = True
    # L3#3.1 : taille du batch de l'évaluateur MCTS.
    #   1  -> code séquentiel historique (un forward par simulation).
    #   >1 -> évaluateur batché avec virtual loss. Recommandé : 8-16 sur CPU,
    #         32-64 sur GPU.
    mcts_batch_size: int = 1
    # Checkpoint
    checkpoint_every: int = 25
    model_dir: str = "models"
    seed: int | None = None
    # Arena (évaluation candidate vs best)
    arena_every: int = 50  # 0 pour désactiver
    arena_games: int = 20
    arena_num_sims: int = 30
    arena_win_threshold: float = 0.55


# ======================================================================================
# 1. RESEAU DE NEURONES (ResNet)
# ======================================================================================
class ResidualBlock(nn.Module):
    """Bloc résiduel avec LayerNorm (robuste au batch=1, contrairement à BatchNorm)."""

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.ln1 = nn.LayerNorm(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.ln2 = nn.LayerNorm(hidden_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.ln1(self.fc1(x)))
        out = self.ln2(self.fc2(out))
        out += residual
        return F.relu(out)


# L3#B2 : nombre maximum de cibles candidates pour un assassinat. La dernière
# cellule de la target_policy (`index == MAX_TARGETS`) représente l'option
# "passer" (ne tuer personne).
MAX_TARGETS = 16


class CourtisansNet(nn.Module):
    """ResNet (style AlphaZero) avec LayerNorm.

    Deux têtes de policy (architecture α de B2) :
      - `policy_head_main`  : `action_dim` logits, pour les décisions
        principales (poser les 3 cartes).
      - `policy_head_target`: `MAX_TARGETS + 1` logits, pour le choix de
        cible d'un assassinat. La dernière cellule = "passer".

    Une seule tête `value` partagée.

    Format du checkpoint : `state_dict` standard. Les modèles entraînés avec
    une version BatchNorm antérieure (ou sans target_head) ne sont pas
    chargeables ; `load_model()` détecte la régression et logge un
    avertissement clair.
    """

    def __init__(self, input_dim: int, action_dim: int, num_blocks: int = 5) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.action_dim = action_dim

        self.start_fc = nn.Linear(input_dim, 512)
        self.ln_start = nn.LayerNorm(512)
        self.res_blocks = nn.ModuleList([ResidualBlock(512) for _ in range(num_blocks)])

        self.policy_head_main = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, action_dim),  # logits coups principaux
        )
        self.policy_head_target = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, MAX_TARGETS + 1),  # logits ciblage d'assassin (+ skip)
        )
        self.value_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Renvoie `(policy_main, policy_target, value)`.

        `policy_main`  : logits de taille `action_dim` (coups principaux).
        `policy_target`: logits de taille `MAX_TARGETS + 1` (ciblage assassin).
        `value`        : scalaire dans `[-1, +1]`.
        """
        x = F.relu(self.ln_start(self.start_fc(x)))
        for block in self.res_blocks:
            x = block(x)
        return self.policy_head_main(x), self.policy_head_target(x), self.value_head(x)


# ======================================================================================
# 2. MCTS
# ======================================================================================
class MCTSNode:
    __slots__ = (
        "parent",
        "children",
        "visit_count",
        "value_sum",
        "prior",
        "player",
        "mode",
        "target_to_victim",
    )

    def __init__(
        self, parent: MCTSNode | None = None, prior: float = 0.0, player: int = 0
    ) -> None:
        self.parent = parent
        self.children: dict[int, MCTSNode] = {}
        self.visit_count = 0
        self.value_sum = 0.0
        self.prior = prior
        # Joueur dont c'est le tour AU MOMENT où on entre dans ce nœud.
        self.player = player
        # Mode (B2) : "main" (décision de coup principal, 12 actions) ou
        # "target" (décision de ciblage d'assassin, MAX_TARGETS+1 actions).
        # Le mode est fixé par `_expand` selon `env.pending_assassin_context`.
        self.mode: str = "main"
        # En mode target uniquement : mapping action_idx -> victim_id (None
        # pour le slot "skip"). Aligné sur la liste des cibles candidates
        # au moment de l'expansion.
        self.target_to_victim: list[int | None] | None = None

    def value(self) -> float:
        if self.visit_count == 0:
            return 0.0
        return self.value_sum / self.visit_count


class MCTS:
    """Monte Carlo Tree Search guidé par le réseau (style AlphaZero).

    Notes :
      - Le masque des actions illégales est appliqué *sur les logits* avant le
        softmax (et non sur les probabilités), pour ne pas biaiser la
        normalisation.
      - Un bruit de Dirichlet est injecté à la racine en self-play (configurable
        via `add_root_noise`).
      - Pour N ≥ 3 joueurs, la value est back-propagée selon le joueur du nœud
        (zero-sum entre `current_player` du nœud et la moyenne des autres,
        approximation suffisante pour notre reward de fin de partie).
    """

    # L3#3.1 : magnitude de la "virtual loss" appliquée aux nœuds traversés
    # pendant une descente batchée. Plus grand = chemins déjà sélectionnés
    # plus pénalisés pour les descentes suivantes du même batch.
    VIRTUAL_LOSS: int = 3

    def __init__(
        self,
        model: CourtisansNet,
        num_sims: int = 50,
        c_puct: float = 1.5,
        dirichlet_alpha: float = 0.3,
        dirichlet_epsilon: float = 0.25,
        num_worlds: int = 1,
        batch_size: int = 1,
    ) -> None:
        self.model = model
        self.num_sims = num_sims
        self.c_puct = c_puct
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_epsilon = dirichlet_epsilon
        # L2#2.1 : nombre de déterminisations indépendantes par appel search().
        # Chaque monde a son propre arbre MCTS ; on agrège les visit_counts.
        self.num_worlds = max(1, num_worlds)
        # L3#3.1 : taille du batch d'évaluation MCTS.
        #   1  -> code séquentiel historique (un forward par sim).
        #   >1 -> évaluateur batché : on collecte K feuilles avec virtual loss
        #         puis un seul forward(batch=K). Gros gain sur GPU.
        self.batch_size = max(1, batch_size)

    def search(self, env: GameEnv, add_root_noise: bool = False) -> np.ndarray:
        """Lance `num_worlds` recherches MCTS indépendantes (déterminisations
        différentes) et renvoie la moyenne des visit_counts normalisée.

        Détecte automatiquement le mode :
          - `env.pending_assassin_context` None  → mode "main", taille `action_dim`.
          - `env.pending_assassin_context` set   → mode "target", taille `MAX_TARGETS + 1`.
            Le caller mappe `slot` → `victim_id` via :
              env.pending_assassin_context["targets"][slot]  pour slot < N
              None (skip)                                    pour slot == MAX_TARGETS

        Si `num_worlds == 1`, c'est le PIMC simple : une seule déterminisation.
        Pour `num_worlds > 1`, c'est du "PIMC multi-déterminisation" qui réduit
        la variance liée au tirage du monde caché.
        """
        if env.pending_assassin_context is not None:
            size = MAX_TARGETS + 1
        else:
            size = env.mapper.get_action_space_size()
        accumulated = np.zeros(size, dtype=np.float32)

        for _ in range(self.num_worlds):
            world_counts = self._search_single_world(env, add_root_noise=add_root_noise)
            accumulated += world_counts

        total = accumulated.sum()
        if total > 0:
            accumulated /= total
        return accumulated

    def _search_single_world(self, env: GameEnv, add_root_noise: bool) -> np.ndarray:
        """Dispatcher : code séquentiel si `batch_size == 1`, sinon batché."""
        if self.batch_size > 1:
            return self._search_single_world_batched(env, add_root_noise)
        return self._search_single_world_sequential(env, add_root_noise)

    def _search_single_world_sequential(
        self, env: GameEnv, add_root_noise: bool
    ) -> np.ndarray:
        """Une recherche MCTS dans une seule déterminisation, un `forward` par
        simulation. Code historique, conservé pour `batch_size=1` et pour la
        clarté pédagogique."""
        root_env = env.clone_determinized()
        root = MCTSNode(player=root_env.current_player)
        self._expand(root, root_env)

        if add_root_noise:
            self._apply_dirichlet(root)

        for _ in range(self.num_sims):
            node = root
            # Toutes les sims d'UN MÊME monde partagent la même
            # déterminisation : on deepcopy sans re-randomiser, sinon
            # les identités changeraient entre sims et casseraient la
            # cohérence des modes (main/target) du tree.
            sim_env = root_env.clone_determinized(randomize=False)

            # 1. Sélection — dispatch step/resolve selon le mode du parent.
            while node.children and not self._is_terminal(sim_env):
                best_child, best_action = self._puct_select(node)
                if best_child is None:
                    break
                self._apply_action(node, sim_env, best_action)
                node = best_child

            # 2. Expansion / Évaluation
            if not self._is_terminal(sim_env):
                value = self._expand(node, sim_env)
            else:
                value = self._terminal_value(sim_env)

            # 3. Backprop
            self._backprop(node, value)

        counts = self._counts_from_root(root, env)
        return counts

    def _apply_action(self, parent: MCTSNode, sim_env: GameEnv, action: int) -> None:
        """Applique une action MCTS sur `sim_env` en respectant le mode du
        parent : `step` pour les coups principaux, `resolve_assassin_manual`
        pour les nœuds de ciblage."""
        if parent.mode == "target":
            assert parent.target_to_victim is not None, (
                "Nœud target sans mapping target_to_victim"
            )
            victim = parent.target_to_victim[action]
            sim_env.resolve_assassin_manual(victim)
        else:
            sim_env.step(action)

    def _counts_from_root(self, root: MCTSNode, env: GameEnv) -> np.ndarray:
        """Visit counts à la racine, dimensionnés selon le mode."""
        if root.mode == "target":
            size = MAX_TARGETS + 1
        else:
            size = env.mapper.get_action_space_size()
        counts = np.zeros(size, dtype=np.float32)
        for act, child in root.children.items():
            counts[act] = child.visit_count
        return counts

    def _search_single_world_batched(
        self, env: GameEnv, add_root_noise: bool
    ) -> np.ndarray:
        """Évaluateur MCTS batché avec "virtual loss" (L3#3.1).

        Algorithme :
          1. Phase de descente : on collecte `batch_size` feuilles. À chaque
             descente, on ajoute une *virtual loss* sur les enfants traversés
             pour rendre ces chemins moins attractifs aux descentes suivantes
             du même batch (sans ça, les K descentes prendraient la même
             branche puisque les visit_count ne sont pas encore mis à jour).
          2. Phase d'évaluation : un seul `forward(batch=K)` pour les feuilles
             non terminales. Les feuilles terminales gardent leur value
             calculée par `_terminal_value`.
          3. Phase de backprop : on annule la virtual loss puis on applique la
             vraie value, classique alternance de signes.

        Gain attendu : x2-3 sur CPU (cache + matmul plus larges), x10-20 sur
        GPU (saturation de la bande passante).
        """
        root_env = env.clone_determinized()
        root = MCTSNode(player=root_env.current_player)
        # L'expansion racine reste batch=1 (rare, une fois par appel).
        self._expand(root, root_env)

        if add_root_noise:
            self._apply_dirichlet(root)

        sims_done = 0
        while sims_done < self.num_sims:
            n_collect = min(self.batch_size, self.num_sims - sims_done)

            # ---- Phase 1 : descente avec virtual loss ----
            pending: list[dict] = []
            for _ in range(n_collect):
                node = root
                # Toutes les sims du même monde partagent la déterminisation
                # racine ; pas de re-randomisation ici (sinon mode mismatch
                # entre sims dans le tree).
                sim_env = root_env.clone_determinized(randomize=False)
                path: list[MCTSNode] = [node]

                while node.children and not self._is_terminal(sim_env):
                    best_child, best_action = self._puct_select(node)
                    if best_child is None:
                        break
                    # Virtual loss pour discourager les chemins déjà pris.
                    best_child.visit_count += self.VIRTUAL_LOSS
                    best_child.value_sum -= self.VIRTUAL_LOSS
                    # Dispatch step / resolve selon le mode du parent.
                    self._apply_action(node, sim_env, best_action)
                    node = best_child
                    path.append(node)

                terminal_v = (
                    self._terminal_value(sim_env) if self._is_terminal(sim_env) else None
                )
                pending.append(
                    {
                        "node": node,
                        "sim_env": sim_env,
                        "path": path,
                        "terminal_value": terminal_v,
                        "nn_value": None,
                    }
                )

            # ---- Phase 2 : un forward batché pour les feuilles non terminales ----
            non_terminal = [p for p in pending if p["terminal_value"] is None]
            if non_terminal:
                states = np.stack(
                    [p["sim_env"].get_state_vector() for p in non_terminal]
                )
                tensor = torch.from_numpy(states).to(DEVICE)
                self.model.eval()
                with torch.no_grad():
                    logits_main_batch, logits_target_batch, values_batch = self.model(tensor)

                for i, p in enumerate(non_terminal):
                    # Dispatch main / target expansion selon l'état de la
                    # feuille (env.pending_assassin_context).
                    leaf_env = p["sim_env"]
                    if leaf_env.pending_assassin_context is not None:
                        targets = list(leaf_env.pending_assassin_context["targets"])
                        self._expand_target_with_logits(
                            p["node"], leaf_env, logits_target_batch[i], targets
                        )
                    else:
                        self._expand_with_logits(
                            p["node"], leaf_env, logits_main_batch[i]
                        )
                    p["nn_value"] = float(values_batch[i].item())

            # ---- Phase 3 : annulation de la virtual loss + backprop ----
            for p in pending:
                for n in p["path"][1:]:
                    n.visit_count -= self.VIRTUAL_LOSS
                    n.value_sum += self.VIRTUAL_LOSS
                value = (
                    p["terminal_value"]
                    if p["terminal_value"] is not None
                    else p["nn_value"]
                )
                self._backprop(p["node"], value)

            sims_done += n_collect

        counts = self._counts_from_root(root, env)
        return counts

    def _puct_select(self, node: MCTSNode) -> tuple[MCTSNode | None, int]:
        """Sélection PUCT standard. Renvoie (meilleur enfant, action).

        Q vu depuis le parent : pour 2 joueurs c'est `-child.value()` (somme
        nulle). Pour N joueurs on garde la même approximation zéro-sum.
        """
        best_score = -float("inf")
        best_child: MCTSNode | None = None
        best_action = -1
        total_visits = sum(c.visit_count for c in node.children.values())
        sqrt_total = float(np.sqrt(total_visits)) if total_visits > 0 else 1.0

        for action, child in node.children.items():
            q_value = -child.value()
            u = self.c_puct * child.prior * sqrt_total / (1 + child.visit_count)
            score = q_value + u
            if score > best_score:
                best_score = score
                best_action = action
                best_child = child
        return best_child, best_action

    @staticmethod
    def _backprop(leaf: MCTSNode, value: float) -> None:
        """Remonte la value le long du chemin, en alternant les signes."""
        cur: MCTSNode | None = leaf
        cur_value = value
        while cur is not None:
            cur.value_sum += cur_value
            cur.visit_count += 1
            cur_value = -cur_value
            cur = cur.parent

    def _apply_dirichlet(self, root: MCTSNode) -> None:
        if not root.children:
            return
        actions = list(root.children.keys())
        noise = np.random.dirichlet([self.dirichlet_alpha] * len(actions))
        for a, n in zip(actions, noise, strict=True):
            root.children[a].prior = (
                (1 - self.dirichlet_epsilon) * root.children[a].prior + self.dirichlet_epsilon * n
            )

    def _terminal_value(self, env: GameEnv) -> float:
        scores = env._calcul_scores()
        cp = env.current_player
        if env.num_players == 2:
            adv = (cp + 1) % 2
            return float((scores[cp] - scores[adv]) / 20.0)
        my = scores[cp]
        others = [v for k, v in scores.items() if k != cp]
        avg = sum(others) / len(others)
        return float((my - avg) / 20.0)

    def _expand(self, node: MCTSNode, env: GameEnv) -> float:
        """Forward `batch=1` + expansion. Retourne la value estimée.

        Dispatch entre mode "main" (décision principale, 12 actions) et mode
        "target" (ciblage d'un assassin, MAX_TARGETS+1 actions). Le mode est
        déterminé par la présence de `env.pending_assassin_context`.
        """
        vec = env.get_state_vector()
        tensor = torch.from_numpy(vec).unsqueeze(0).to(DEVICE)

        self.model.eval()
        with torch.no_grad():
            logits_main, logits_target, v = self.model(tensor)

        if env.pending_assassin_context is not None:
            targets = list(env.pending_assassin_context["targets"])
            self._expand_target_with_logits(node, env, logits_target[0], targets)
        else:
            self._expand_with_logits(node, env, logits_main[0])
        return float(v.item())

    def _expand_with_logits(
        self, node: MCTSNode, env: GameEnv, logits_1d: torch.Tensor
    ) -> None:
        """Expansion mode "main" à partir de logits déjà calculés."""
        node.mode = "main"
        legal = env.get_legal_actions()
        if not legal:
            return

        # Masquage AVANT softmax : logits illégaux à -inf.
        mask = torch.full_like(logits_1d, float("-inf"))
        mask[legal] = logits_1d[legal]
        probs = F.softmax(mask, dim=0).cpu().numpy()

        if not np.isfinite(probs).all() or probs.sum() <= 0:
            probs = np.zeros_like(probs)
            probs[legal] = 1.0 / len(legal)

        child_player = env.current_player
        for idx in legal:
            if probs[idx] > 0:
                node.children[idx] = MCTSNode(
                    node, prior=float(probs[idx]), player=child_player
                )

    def _expand_target_with_logits(
        self,
        node: MCTSNode,
        env: GameEnv,
        logits_1d: torch.Tensor,
        targets: list[int],
    ) -> None:
        """Expansion mode "target" : enfants = cibles candidates + skip.

        Slots dans le vecteur de logits :
          - 0..len(targets)-1  : index dans `targets` (= victim_id réel).
          - MAX_TARGETS        : option "skip" (ne tuer personne).

        `node.target_to_victim` est rempli pour la descente ultérieure.
        """
        node.mode = "target"
        skip_idx = MAX_TARGETS
        n = len(targets)

        # Mapping action_slot -> victim_id (None pour skip).
        target_to_victim: list[int | None] = [None] * (MAX_TARGETS + 1)
        for i, tid in enumerate(targets):
            if i >= MAX_TARGETS:
                # Sécurité : si jamais on a plus de cibles que MAX_TARGETS,
                # on tronque (cas pathologique, plateau saturé).
                break
            target_to_victim[i] = tid
        target_to_victim[skip_idx] = None
        node.target_to_victim = target_to_victim

        # Slots légaux : N cibles (clampées à MAX_TARGETS) + skip.
        n_used = min(n, MAX_TARGETS)
        legal_slots = list(range(n_used)) + [skip_idx]

        mask = torch.full_like(logits_1d, float("-inf"))
        for s in legal_slots:
            mask[s] = logits_1d[s]
        probs = F.softmax(mask, dim=0).cpu().numpy()

        if not np.isfinite(probs).all() or probs.sum() <= 0:
            probs = np.zeros_like(probs)
            for s in legal_slots:
                probs[s] = 1.0 / len(legal_slots)

        # Le tour ne change pas : c'est toujours le même joueur qui décide
        # de la cible (il vient juste de jouer son assassin).
        child_player = env.current_player
        for s in legal_slots:
            if probs[s] > 0:
                node.children[s] = MCTSNode(
                    node, prior=float(probs[s]), player=child_player
                )

    @staticmethod
    def _is_terminal(env: GameEnv) -> bool:
        return env.is_done()


# ======================================================================================
# 3. ENTRAINEMENT
# ======================================================================================
def _seed_everything(seed: int | None) -> None:
    if seed is None:
        return
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _play_one_arena_game(
    net_a: CourtisansNet,
    net_b: CourtisansNet,
    num_players: int,
    num_sims: int,
    a_starts: bool,
) -> int | None:
    """Joue une partie entre net_a et net_b. Renvoie l'identifiant du gagnant
    (0 = a, 1 = b) ou None en cas d'égalité.

    Si `a_starts` est True, net_a joue le joueur 0 ; sinon net_b joue le 0.
    """
    env = GameEnv(num_players)
    mcts_a = MCTS(net_a, num_sims=num_sims)
    mcts_b = MCTS(net_b, num_sims=num_sims)

    def net_for(player_idx: int) -> MCTS:
        if (player_idx == 0) == a_starts:
            return mcts_a
        return mcts_b

    while not env.is_done():
        mcts = net_for(env.current_player)
        probs = mcts.search(env)
        action = int(np.argmax(probs))
        _, _, _, info = env.step(action)
        if info.get("assassin_pending"):
            # Arena : résolution heuristique pour comparer les deux modèles
            # sur leur policy principale, sans biaiser par MCTS targeting.
            env.resolve_pending_with_heuristic()

    scores = env._calcul_scores()
    # Identifier le slot a/b
    a_slot = 0 if a_starts else 1
    b_slot = 1 if a_starts else 0
    if scores[a_slot] > scores[b_slot]:
        return 0  # a gagne
    if scores[b_slot] > scores[a_slot]:
        return 1  # b gagne
    return None


def arena(
    challenger: CourtisansNet,
    champion: CourtisansNet,
    num_games: int = 20,
    num_sims: int = 30,
    num_players: int = 2,
) -> dict[str, int | float]:
    """Joue `num_games` parties entre `challenger` et `champion`.

    Les positions de départ sont alternées pour neutraliser l'avantage du
    premier joueur. Le résultat inclut `winrate` = victoires_challenger / parties_décisives.
    """
    challenger.eval()
    champion.eval()

    wins = losses = draws = 0
    for g in range(num_games):
        a_starts = (g % 2 == 0)
        result = _play_one_arena_game(
            challenger, champion, num_players, num_sims, a_starts=a_starts
        )
        if result is None:
            draws += 1
        elif result == 0:
            wins += 1
        else:
            losses += 1

    decisive = wins + losses
    winrate = wins / decisive if decisive > 0 else 0.0
    return {"wins": wins, "losses": losses, "draws": draws, "winrate": winrate}


def _clone_network(src: CourtisansNet, env: GameEnv) -> CourtisansNet:
    """Crée une copie indépendante du réseau (même architecture, mêmes poids)."""
    tgt = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(DEVICE)
    tgt.load_state_dict({k: v.detach().clone() for k, v in src.state_dict().items()})
    return tgt


def train(
    config: TrainConfig | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
    # API rétro-compatible avec l'ancien appel `train(num_players=2, iterations=50, ...)`
    num_players: int | None = None,
    iterations: int | None = None,
) -> CourtisansNet:
    if config is None:
        config = TrainConfig()
    if num_players is not None:
        config.num_players = num_players
    if iterations is not None:
        config.iterations = iterations

    _seed_everything(config.seed)

    env_tmp = GameEnv(config.num_players, seed=config.seed)
    input_dim = env_tmp.get_state_vector_size()
    action_dim = env_tmp.mapper.get_action_space_size()

    net = CourtisansNet(input_dim, action_dim).to(DEVICE)
    # L1#1.4 : AdamW pour un decoupled weight decay propre.
    optimizer = optim.AdamW(net.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    mcts = MCTS(
        net,
        num_sims=config.num_sims,
        c_puct=config.c_puct,
        dirichlet_alpha=config.dirichlet_alpha,
        dirichlet_epsilon=config.dirichlet_epsilon,
        num_worlds=config.num_worlds,
        batch_size=config.mcts_batch_size,
    )

    # Memory : (state, policy, value, hand_keys_or_None, mode).
    #   mode in {"main", "target"} (B2 step γ).
    #   hand_keys est requis pour l'augmentation famille du mode main ;
    #   None pour les samples target (policy invariante par σ).
    memory: deque[
        tuple[np.ndarray, np.ndarray, float, tuple[int, int, int] | None, str]
    ] = deque(maxlen=config.memory_size)
    os.makedirs(config.model_dir, exist_ok=True)

    # Convention de fichiers :
    #   models/model_{N}.pth            -> best (utilisé par Streamlit / play_vs_ai)
    #   models/model_{N}_candidate.pth  -> dernier candidat entraîné
    best_path = os.path.join(config.model_dir, f"model_{config.num_players}.pth")
    candidate_path = os.path.join(config.model_dir, f"model_{config.num_players}_candidate.pth")

    # Champion : best déjà sur disque s'il existe, sinon poids initiaux du net.
    best_net = load_model(best_path, env_tmp)
    if best_net is None:
        best_net = _clone_network(net, env_tmp)
        logger.info("Aucun champion préexistant — poids initiaux comme baseline.")

    for it in range(config.iterations):
        if progress_callback:
            progress_callback(it / max(1, config.iterations), f"Iteration {it}/{config.iterations}")

        env = GameEnv(config.num_players)
        # History entry : (state, policy, player, hand_keys_or_None, mode).
        HistEntry = tuple[
            np.ndarray, np.ndarray, int, tuple[int, int, int] | None, str
        ]
        history: list[HistEntry] = []
        done = False
        move_in_game = 0

        # Self-play
        while not done:
            # --- Décision principale (mode "main") ---
            s_vec = env.get_state_vector()
            hand_keys = tuple(
                sorted(env.cartes[i].sort_key for i in env.mains[env.current_player])
            )
            if len(hand_keys) != 3:
                break  # main < 3 cartes -> on ne peut pas jouer

            probs_main = mcts.search(env, add_root_noise=True)
            if move_in_game < config.temperature_threshold:
                action = int(np.random.choice(len(probs_main), p=probs_main))
            else:
                action = int(np.argmax(probs_main))

            history.append((s_vec, probs_main, env.current_player, hand_keys, "main"))
            _, _, done, info = env.step(action)
            move_in_game += 1

            # --- Décisions de ciblage (mode "target", B2 step γ) ---
            # Tant qu'il y a un assassin en attente, on demande à MCTS de
            # choisir la cible. Chaque appel génère un sample target dans
            # l'historique, qui servira à entraîner `policy_head_target`.
            while info.get("assassin_pending") and not done:
                target_state = env.get_state_vector()
                target_player = env.current_player
                ctx = env.pending_assassin_context
                ctx_targets = list(ctx["targets"]) if ctx else []

                probs_target = mcts.search(env, add_root_noise=False)
                if move_in_game < config.temperature_threshold:
                    slot = int(np.random.choice(len(probs_target), p=probs_target))
                else:
                    slot = int(np.argmax(probs_target))

                # Map slot -> victim_id (None pour skip / slot hors cibles).
                if 0 <= slot < len(ctx_targets):
                    victim = ctx_targets[slot]
                else:
                    victim = None

                history.append(
                    (target_state, probs_target, target_player, None, "target")
                )
                _, _, done, info = env.resolve_assassin_manual(victim)

        # Reward final attribué à chaque état selon le joueur qui devait jouer.
        scores = env._calcul_scores()
        for s, p, player_id, hk, mode in history:
            my_score = scores[player_id]
            others = [v for k, v in scores.items() if k != player_id]
            avg_others = sum(others) / len(others)
            val = max(-1.0, min(1.0, (my_score - avg_others) / 20.0))
            memory.append((s, p, val, hk, mode))

        # Étape d'optimisation
        if len(memory) > config.batch_size:
            raw_batch = random.sample(memory, config.batch_size)

            # Pré-augmenter chaque sample. Les samples main subissent
            # `augment_sample` (état + remap policy). Les samples target
            # subissent `augment_target_sample` (état seul ; policy
            # invariante par σ).
            aug_states: list[np.ndarray] = []
            aug_values: list[float] = []
            aug_modes: list[str] = []
            aug_main_policies: list[np.ndarray] = []
            aug_target_policies: list[np.ndarray] = []
            for s, p, v, hk, mode in raw_batch:
                if mode == "main":
                    if config.family_augmentation and hk is not None:
                        new_s, new_p, _ = augment_sample(s, p, hk, env_tmp.mapper)
                    else:
                        new_s, new_p = s, p
                    aug_states.append(new_s)
                    aug_values.append(v)
                    aug_modes.append("main")
                    aug_main_policies.append(new_p)
                else:  # target
                    if config.family_augmentation:
                        new_s, new_p = augment_target_sample(s, p, env_tmp.mapper)
                    else:
                        new_s, new_p = s, p
                    aug_states.append(new_s)
                    aug_values.append(v)
                    aug_modes.append("target")
                    aug_target_policies.append(new_p)

            states_tensor = torch.from_numpy(np.array(aug_states)).to(DEVICE)
            values_tensor = torch.from_numpy(
                np.array(aug_values, dtype=np.float32)
            ).unsqueeze(1).to(DEVICE)

            net.train()
            pi_main_pred, pi_target_pred, v_pred = net(states_tensor)

            # Indices des samples par mode (pour slicer les sorties).
            main_idx = [i for i, m in enumerate(aug_modes) if m == "main"]
            target_idx = [i for i, m in enumerate(aug_modes) if m == "target"]

            zero = torch.zeros((), device=DEVICE)
            loss_pi_main = zero
            loss_pi_target = zero

            if main_idx:
                main_logits = pi_main_pred[main_idx]
                main_targets = torch.from_numpy(np.array(aug_main_policies)).to(DEVICE)
                loss_pi_main = (
                    -torch.sum(main_targets * F.log_softmax(main_logits, dim=1))
                    / len(main_idx)
                )

            if target_idx:
                target_logits = pi_target_pred[target_idx]
                target_targets = torch.from_numpy(np.array(aug_target_policies)).to(
                    DEVICE
                )
                loss_pi_target = (
                    -torch.sum(target_targets * F.log_softmax(target_logits, dim=1))
                    / len(target_idx)
                )

            loss_v = F.mse_loss(v_pred, values_tensor)
            loss = loss_pi_main + loss_pi_target + loss_v

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if it % 10 == 0:
                logger.info(
                    "Iter %d | loss=%.4f | top_score=%d", it, loss.item(), max(scores.values())
                )

        # Checkpoint intermédiaire
        if config.checkpoint_every and (it + 1) % config.checkpoint_every == 0:
            ckpt = os.path.join(
                config.model_dir, f"model_{config.num_players}_ckpt_{it + 1}.pth"
            )
            torch.save(net.state_dict(), ckpt)
            logger.info("Checkpoint saved: %s", ckpt)

        # Arena : on confronte la version courante au meilleur connu.
        if config.arena_every and (it + 1) % config.arena_every == 0:
            stats = arena(
                challenger=net,
                champion=best_net,
                num_games=config.arena_games,
                num_sims=config.arena_num_sims,
                num_players=config.num_players,
            )
            logger.info(
                "Arena (iter %d): wins=%d losses=%d draws=%d winrate=%.2f",
                it + 1,
                stats["wins"],
                stats["losses"],
                stats["draws"],
                stats["winrate"],
            )
            if stats["winrate"] >= config.arena_win_threshold:
                best_net = _clone_network(net, env_tmp)
                torch.save(best_net.state_dict(), best_path)
                logger.info(
                    "Champion promu : %s (winrate %.2f >= %.2f)",
                    best_path,
                    stats["winrate"],
                    config.arena_win_threshold,
                )
            else:
                logger.info(
                    "Champion conservé (winrate %.2f < %.2f)",
                    stats["winrate"],
                    config.arena_win_threshold,
                )

    # Sauvegarde finale du candidat.
    torch.save(net.state_dict(), candidate_path)
    logger.info("Final candidate saved: %s", candidate_path)
    # Si aucun champion n'a jamais été promu, on sauvegarde le best courant
    # (initial ou dernière promotion) en model_{N}.pth pour que load_model
    # côté UI/CLI trouve quelque chose à charger.
    if not os.path.exists(best_path):
        torch.save(best_net.state_dict(), best_path)
        logger.info("Initial best saved: %s", best_path)
    return net


def load_model(model_path: str, env: GameEnv) -> CourtisansNet | None:
    """Charge un modèle si présent, sinon None. Utilise weights_only=True.

    Si le checkpoint provient d'une ancienne architecture (BatchNorm), on
    détecte la mismatch de clés et on logge une instruction de ré-entraînement
    plutôt que de planter.
    """
    if not os.path.exists(model_path):
        logger.info("No model at %s", model_path)
        return None
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(DEVICE)
    try:
        state = torch.load(model_path, map_location=DEVICE, weights_only=True)
        net.load_state_dict(state)
    except FileNotFoundError as exc:
        logger.warning("Could not load model %s : %s", model_path, exc)
        return None
    except RuntimeError as exc:
        msg = str(exc)
        if "bn1" in msg or "bn2" in msg or "bn_start" in msg or "Missing key(s)" in msg:
            logger.warning(
                "Le checkpoint %s semble provenir de l'ancienne architecture "
                "BatchNorm — incompatible avec la version LayerNorm actuelle. "
                "Ré-entraîner via: python main.py train --iterations 100",
                model_path,
            )
        else:
            logger.warning("Could not load model %s : %s", model_path, exc)
        return None
    net.eval()
    return net


def play_vs_ai(model_path: str = "models/model_2.pth", num_sims: int = 50) -> None:
    """Boucle de jeu console : humain (joueur 0) vs IA (joueur 1)."""
    num_players = 2
    env = GameEnv(num_players)
    net = load_model(model_path, env)
    if net is None:
        logger.warning("Pas de modèle chargé, l'IA utilisera des poids aléatoires.")
        net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(
            DEVICE
        )
    mcts = MCTS(net, num_sims=num_sims)
    net.eval()

    print("=== IA vs HUMAIN (Console) ===")
    while not env.is_done():
        print(f"\n--- Tour Joueur {env.current_player} ---")
        if env.current_player == 0:
            print("Votre main :", env.mains[0])
            actions = env.get_legal_actions()
            for a in actions:
                perm, q, t = env.mapper.decode(a)
                print(f" {a}: M{perm}->[R({q}), S, A({t})]")
            try:
                c = int(input("Choix > "))
            except ValueError:
                print("Entrée invalide, on rejoue le tour.")
                continue
            if c not in actions:
                print("Action illégale, on rejoue le tour.")
                continue
            _, _, _, info = env.step(c)
        else:
            print("IA réfléchit...")
            probs = mcts.search(env)
            action = int(np.argmax(probs))
            _, _, _, info = env.step(action)

        if info.get("assassin_pending"):
            # play_vs_ai console : résolution heuristique pour l'IA.
            # Note : pour le joueur humain on pourrait afficher un menu
            # console, ici on garde simple en utilisant la même heuristique.
            env.resolve_pending_with_heuristic()

    print("Scores:", env._calcul_scores())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    train(config=TrainConfig(num_players=2, iterations=50))

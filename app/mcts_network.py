"""Implémentation AlphaZero-like (MCTS + ResNet) pour Courtisans."""

from __future__ import annotations

import glob
import logging
import os
import random
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

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
    # Nb de parties self-play lancées en parallèle (threads Python).
    # PyTorch relâche le GIL pendant les ops CUDA → les threads s'intercalent
    # sur le GPU sans se bloquer. Recommandé : 4-8 sur 9600X + 4060Ti.
    num_parallel_games: int = 1
    # Checkpoint
    checkpoint_every: int = 25
    model_dir: str = "models"
    seed: int | None = None
    # Arena (évaluation candidate vs best)
    arena_every: int = 50  # 0 pour désactiver
    # 200 parties → ±7 % CI (vs ±22 % pour 20). ~10 min/arena à 30 sims.
    arena_games: int = 200
    arena_num_sims: int = 30
    arena_win_threshold: float = 0.55
    # Améliorations v2
    # Fraction de parties self-play jouées contre un checkpoint passé aléatoire.
    # Réduit le catastrophic forgetting sans replay buffer illimité.
    past_checkpoint_ratio: float = 0.25
    # Schedule progressif : iter 0-100 → min(num_sims, 100) |
    # iter 100-250 → min(num_sims, 200) | iter 250+ → num_sims.
    # Sans effet si num_sims ≤ 100.
    progressive_sims: bool = True
    # Benchmark contre le greedy bot tous les N iters (0 = désactivé).
    greedy_benchmark_every: int = 50
    greedy_benchmark_games: int = 100
    # Discount temporel sur la valeur : γ^(T-k) × valeur_finale.
    # 1.0 = pas de discount (comportement v1). 0.99 = les coups récents
    # reçoivent plus de crédit que les coups du début de partie.
    value_discount: float = 0.99
    # Inférence en float16 sur GPU (Tensor Cores). Entraînement reste float32.
    use_fp16: bool = True
    # torch.compile() sur le réseau. Gain ~20-40% après warmup (~30s au départ).
    # Nécessite gcc dans l'environnement (Triton). Désactivé par défaut sous WSL2.
    use_compile: bool = False
    # Cosine annealing : LR décroît de lr à lr_min sur `iterations` steps.
    lr_min: float = 1e-5
    # Nombre de passes d'optimisation par itération de self-play.
    # K>1 extrait plus de signal du buffer sans générer plus de parties.
    train_steps_per_iter: int = 1
    # Held-out buffer pour v_corr hors-distribution (mesure honnête de la value).
    # held_out_ratio : fraction des parties routées vers le buffer held-out (jamais entraîné).
    # 0.0 = désactivé. Recommandé : 0.05–0.10.
    held_out_ratio: float = 0.0
    held_out_size: int = 2000
    # v9 : remplace la value réseau aux feuilles par une heuristique de score.
    heuristic_value: bool = False
    # Fork 2 : self-play direct sans MCTS (expert iteration sur outcomes réels).
    # use_mcts=False → échantillonnage température depuis les logits policy.
    # entropy_coef    → bonus d'entropie dans la loss policy (maintient stochasticité).
    # policy_temperature → température d'exploration en début de partie.
    use_mcts: bool = True
    entropy_coef: float = 0.0
    policy_temperature: float = 1.0
    # AWR (Advantage Weighted Regression) — remplace l'Option A (max(z,0)).
    # loss = -exp((z - z_mean) / awr_beta) * log π(a).
    # Utilise les parties perdues (poids négatif), off-policy-safe.
    # awr_beta=0.0 → désactivé (Option A). awr_beta=1.0 → recommandé pour démarrer.
    # awr_weight_clip : plafond du poids pour éviter qu'un seul échantillon domine.
    awr_beta: float = 0.0
    awr_weight_clip: float = 20.0
    # Pool ancré (fictitious play) — checkpoints TOUJOURS présents comme adversaires,
    # en plus des checkpoints récents tirés au hasard. Ancrer le meilleur modèle connu
    # (ex. v8_250) empêche le self-play de dériver hors du bon bassin.
    # anchor_ratio : dans la branche "adversaire passé" (prob past_checkpoint_ratio),
    # fraction du temps où l'on tire un ancre plutôt qu'un checkpoint récent.
    anchor_checkpoints: list[str] = field(default_factory=list)
    anchor_ratio: float = 0.5


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
        use_fp16: bool = False,
    ) -> None:
        self.model = model
        self.num_sims = num_sims
        self.c_puct = c_puct
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_epsilon = dirichlet_epsilon
        # float16 uniquement si GPU dispo et demandé
        self.use_fp16 = use_fp16 and DEVICE.type == "cuda"
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
                    if self.use_fp16:
                        with torch.autocast(device_type="cuda", dtype=torch.float16):
                            logits_main_batch, logits_target_batch, values_batch = self.model(tensor)
                    else:
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
            if self.use_fp16:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    logits_main, logits_target, v = self.model(tensor)
            else:
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


class MCTSReDeterminize(MCTS):
    """ISMCTS : 1 arbre partagé, monde frais par simulation (Cowling et al. 2012).

    Coût = N sims (identique au mono-monde) : on ajoute juste N clone_determinized()
    — trivial devant un forward pass réseau. Pas de compromis profondeur/diversité.

    Quand un monde frais diverge du mode du nœud courant (ex. l'adversaire joue
    un assassin dans ce monde mais pas dans celui qui a construit le nœud), on
    arrête la descente et on évalue depuis le nœud courant — approximation ISMCTS
    standard pour les modes variables (main / target) de Courtisans.
    """

    def _search_single_world_sequential(
        self, env: GameEnv, add_root_noise: bool
    ) -> np.ndarray:
        root_env = env.clone_determinized()
        root = MCTSNode(player=root_env.current_player)
        self._expand(root, root_env)

        if add_root_noise:
            self._apply_dirichlet(root)

        for _ in range(self.num_sims):
            node = root
            # Monde frais : chaque simulation explore depuis un état caché différent.
            sim_env = env.clone_determinized()

            while node.children and not self._is_terminal(sim_env):
                # Vérification de cohérence de mode : si le monde frais diverge
                # (l'adversaire a/n'a pas d'assassin dans ce monde), on arrête la
                # descente et on évalue depuis ce nœud — approximation ISMCTS.
                sim_is_target = sim_env.pending_assassin_context is not None
                node_is_target = node.mode == "target"
                if sim_is_target != node_is_target:
                    break

                best_child, best_action = self._puct_select(node)
                if best_child is None:
                    break
                self._apply_action(node, sim_env, best_action)
                node = best_child

            if not self._is_terminal(sim_env):
                value = self._expand(node, sim_env)
            else:
                value = self._terminal_value(sim_env)

            self._backprop(node, value)

        return self._counts_from_root(root, env)


class MCTSISMCTSZeroValue(MCTSReDeterminize):
    """ISMCTS + value=0 partout — discriminateur pur (B) sans pollution de la value.

    Même budget et même profondeur que MCTSZeroValue mono-monde, mais chaque
    simulation tire un monde frais. Si ce mode bat policy_only alors que
    MCTSZeroValue (mono) ne le bat pas → strategy fusion confirmée.
    """

    def _expand(self, node: MCTSNode, env: GameEnv) -> float:
        vec = env.get_state_vector()
        tensor = torch.from_numpy(vec).unsqueeze(0).to(DEVICE)
        self.model.eval()
        with torch.no_grad():
            if self.use_fp16:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    logits_main, logits_target, _ = self.model(tensor)
            else:
                logits_main, logits_target, _ = self.model(tensor)
        if env.pending_assassin_context is not None:
            targets = list(env.pending_assassin_context["targets"])
            self._expand_target_with_logits(node, env, logits_target[0], targets)
        else:
            self._expand_with_logits(node, env, logits_main[0])
        return 0.0

    def _terminal_value(self, env: GameEnv) -> float:
        return 0.0


class MCTSHeuristicValue(MCTS):
    """MCTS utilisant le prior réseau + value heuristique (score courant normalisé).

    Remplace la value apprise par tanh(margin/SCALE) où margin = score_moi - moy(autres).
    Objectif v9 : rendre l'opérateur d'amélioration positif (mcts_on > policy_only)
    quand v_corr_ood est trop faible (<0.6) pour que la value réseau aide.
    _terminal_value garde le vrai résultat (hérité de MCTS).
    """

    SCALE: float = 15.0

    def _expand(self, node: MCTSNode, env: GameEnv) -> float:
        super()._expand(node, env)  # construit les enfants avec les priors réseau
        cp = env.current_player
        scores = env._calcul_scores()
        my_score = scores.get(cp, 0)
        others = [v for j, v in scores.items() if j != cp]
        margin = my_score - (sum(others) / len(others) if others else 0)
        return float(np.tanh(margin / self.SCALE))


class MCTSZeroValue(MCTS):
    """MCTS avec value=0 partout (feuilles ET terminaux) — PUCT pur sur prior.

    Sert de baseline diagnostique : si MCTS-normal > MCTSZeroValue, la value
    aide la recherche. Si MCTSZeroValue > MCTS-normal, la value est nuisible.
    """

    def _expand(self, node: MCTSNode, env: GameEnv) -> float:
        vec = env.get_state_vector()
        tensor = torch.from_numpy(vec).unsqueeze(0).to(DEVICE)
        self.model.eval()
        with torch.no_grad():
            if self.use_fp16:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    logits_main, logits_target, _ = self.model(tensor)
            else:
                logits_main, logits_target, _ = self.model(tensor)
        if env.pending_assassin_context is not None:
            targets = list(env.pending_assassin_context["targets"])
            self._expand_target_with_logits(node, env, logits_target[0], targets)
        else:
            self._expand_with_logits(node, env, logits_main[0])
        return 0.0

    def _terminal_value(self, env: GameEnv) -> float:
        return 0.0


class MCTSGreedyRollout(MCTS):
    """MCTS avec rollout greedy jusqu'au terminal comme signal de feuille.

    Remplace la value réseau aux feuilles par un rollout greedy complet dans le
    monde déterminisé courant. Signal réel (±1), non plafonné à r=0.4.
    Priors PUCT toujours fournis par le réseau. Terminaux : vrai résultat.

    Ultime tiebreak MCTS : si ce mode ne bat pas policy_only, la famille MCTS
    est inadaptée au jeu → Fork 2 (self-play direct sans MCTS-professeur).
    """

    def _expand(self, node: MCTSNode, env: GameEnv) -> float:
        vec = env.get_state_vector()
        tensor = torch.from_numpy(vec).unsqueeze(0).to(DEVICE)
        self.model.eval()
        with torch.no_grad():
            if self.use_fp16:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    logits_main, logits_target, _ = self.model(tensor)
            else:
                logits_main, logits_target, _ = self.model(tensor)
        if env.pending_assassin_context is not None:
            targets = list(env.pending_assassin_context["targets"])
            self._expand_target_with_logits(node, env, logits_target[0], targets)
        else:
            self._expand_with_logits(node, env, logits_main[0])
        return self._greedy_rollout(env)

    def _greedy_rollout(self, env: GameEnv) -> float:
        """Rollout greedy depuis l'état courant (monde déjà déterminisé)."""
        sim = env.clone_determinized(randomize=False)
        cp = sim.current_player
        while not sim.is_done():
            if sim.pending_assassin_context is not None:
                # Greedy target : choisit la victime qui maximise le score immédiat
                ctx = sim.pending_assassin_context
                targets = list(ctx["targets"])
                best_victim: int | None = None
                best_score = -float("inf")
                for victim in (None, *targets):
                    trial = sim.clone_determinized(randomize=False)
                    trial.resolve_assassin_manual(victim)
                    score = trial._calcul_scores().get(cp, 0)
                    if score > best_score:
                        best_score = score
                        best_victim = victim
                sim.resolve_assassin_manual(best_victim)
            else:
                legal = sim.get_legal_actions()
                if not legal:
                    break
                best_action = legal[0]
                best_score = -float("inf")
                for action in legal:
                    trial = sim.clone_determinized(randomize=False)
                    trial.step(action)
                    score = trial._calcul_scores().get(cp, 0)
                    if score > best_score:
                        best_score = score
                        best_action = action
                sim.step(best_action)
        scores = sim._calcul_scores()
        my_score = scores.get(cp, 0)
        others = [v for j, v in scores.items() if j != cp]
        margin = my_score - sum(others) / len(others) if others else my_score
        return 1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)


# ======================================================================================
# 3. ENTRAINEMENT
# ======================================================================================
def _get_effective_sims(config: TrainConfig, it: int) -> int:
    """Nombre de simulations MCTS effectif selon le schedule progressif."""
    if not config.progressive_sims:
        return config.num_sims
    if it < 100:
        return min(config.num_sims, 100)
    if it < 250:
        return min(config.num_sims, 200)
    return config.num_sims


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


def _run_one_game(
    net: CourtisansNet,
    config: TrainConfig,
    opponent_net: CourtisansNet | None = None,
    effective_sims: int | None = None,
) -> tuple[list[tuple], dict]:
    """Joue une partie complète. Thread-safe : MCTS locaux, nets partagés en lecture.

    net joue le joueur 0. opponent_net (ou net si None) joue le joueur 1.
    effective_sims écrase config.num_sims si fourni (pour le schedule progressif).
    """
    sims = effective_sims if effective_sims is not None else config.num_sims
    net_by_player = [net, opponent_net if opponent_net is not None else net]

    if config.use_mcts:
        _mcts_kwargs = dict(
            num_sims=sims,
            c_puct=config.c_puct,
            dirichlet_alpha=config.dirichlet_alpha,
            dirichlet_epsilon=config.dirichlet_epsilon,
            num_worlds=config.num_worlds,
            batch_size=config.mcts_batch_size,
            use_fp16=config.use_fp16,
        )
        mcts_cls = MCTSHeuristicValue if config.heuristic_value else MCTS
        mcts_0 = mcts_cls(net, **_mcts_kwargs)
        mcts_1 = mcts_cls(opponent_net, **_mcts_kwargs) if opponent_net is not None else mcts_0
        mcts_by_player = [mcts_0, mcts_1]

    env = GameEnv(config.num_players)
    history: list[tuple] = []
    done = False
    move_in_game = 0

    while not done:
        s_vec = env.get_state_vector()
        hand_keys = tuple(sorted(env.cartes[i].sort_key for i in env.mains[env.current_player]))
        if len(hand_keys) != 3:
            break

        if config.use_mcts:
            local_mcts = mcts_by_player[env.current_player % 2]
            probs_main = local_mcts.search(env, add_root_noise=True)
            action = (
                int(np.random.choice(len(probs_main), p=probs_main))
                if move_in_game < config.temperature_threshold
                else int(np.argmax(probs_main))
            )
            history.append((s_vec, probs_main, env.current_player, hand_keys, "main"))
        else:
            # Fork 2 : échantillonnage direct depuis les logits policy (sans MCTS).
            local_net = net_by_player[env.current_player % 2]
            local_net.eval()
            tensor = torch.from_numpy(s_vec).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits_main, _, _ = local_net(tensor)
            legal = env.get_legal_actions()
            logits = logits_main[0].cpu().numpy()
            masked = np.full(len(logits), -1e9, dtype=np.float32)
            masked[legal] = logits[legal]
            if move_in_game < config.temperature_threshold:
                scaled = masked / max(config.policy_temperature, 1e-6)
                scaled -= scaled.max()
                probs_main = np.exp(scaled)
                probs_main /= probs_main.sum()
                action = int(np.random.choice(len(probs_main), p=probs_main))
            else:
                action = int(np.argmax(masked))
            # Cible one-hot : l'action jouée (pondérée par z en entraînement).
            policy_target = np.zeros(len(logits), dtype=np.float32)
            policy_target[action] = 1.0
            history.append((s_vec, policy_target, env.current_player, hand_keys, "main"))

        _, _, done, info = env.step(action)
        move_in_game += 1

        while info.get("assassin_pending") and not done:
            target_state = env.get_state_vector()
            target_player = env.current_player
            ctx = env.pending_assassin_context
            ctx_targets = list(ctx["targets"]) if ctx else []

            if config.use_mcts:
                local_mcts = mcts_by_player[env.current_player % 2]
                probs_target = local_mcts.search(env, add_root_noise=False)
                slot = (
                    int(np.random.choice(len(probs_target), p=probs_target))
                    if move_in_game < config.temperature_threshold
                    else int(np.argmax(probs_target))
                )
                history.append((target_state, probs_target, target_player, None, "target"))
            else:
                local_net = net_by_player[target_player % 2]
                local_net.eval()
                tensor = torch.from_numpy(target_state).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    _, logits_target, _ = local_net(tensor)
                n_slots = len(ctx_targets) + 1  # cibles + skip
                logits = logits_target[0].cpu().numpy()[:n_slots]
                if move_in_game < config.temperature_threshold:
                    scaled = logits / max(config.policy_temperature, 1e-6)
                    scaled -= scaled.max()
                    pt = np.exp(scaled); pt /= pt.sum()
                    slot = int(np.random.choice(len(pt), p=pt))
                else:
                    slot = int(np.argmax(logits))
                target_oh = np.zeros(MAX_TARGETS + 1, dtype=np.float32)
                target_oh[slot] = 1.0
                history.append((target_state, target_oh, target_player, None, "target"))

            victim = ctx_targets[slot] if 0 <= slot < len(ctx_targets) else None
            _, _, done, info = env.resolve_assassin_manual(victim)

    scores = env._calcul_scores()
    samples = []
    for s, p, player_id, hk, mode in history:
        my_score = scores[player_id]
        others = [v for j, v in scores.items() if j != player_id]
        margin = my_score - sum(others) / len(others)
        # Cible canonique AlphaZero : résultat final de partie (sans discount).
        # γ^(T-1-k) était non apprenable car T et k ne sont pas dans le state vector.
        val = 1.0 if margin > 0 else (-1.0 if margin < 0 else 0.0)
        samples.append((s, p, val, hk, mode))
    return samples, scores


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
    if config.use_compile and DEVICE.type == "cuda" and hasattr(torch, "compile"):
        try:
            net = torch.compile(net, mode="reduce-overhead")
            logger.info("torch.compile() activé (warmup ~30s à la première itération).")
        except Exception as e:
            logger.warning("torch.compile() indisponible (%s) — entraînement sans compilation.", e)
    # L1#1.4 : AdamW pour un decoupled weight decay propre.
    optimizer = optim.AdamW(net.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, config.iterations), eta_min=config.lr_min
    )
    # Memory : (state, policy, value, hand_keys_or_None, mode).
    #   mode in {"main", "target"} (B2 step γ).
    #   hand_keys est requis pour l'augmentation famille du mode main ;
    #   None pour les samples target (policy invariante par σ).
    memory: deque[
        tuple[np.ndarray, np.ndarray, float, tuple[int, int, int] | None, str]
    ] = deque(maxlen=config.memory_size)
    # Held-out buffer : échantillons jamais utilisés pour l'entraînement.
    # Sert à calculer un v_corr hors-distribution (OOD) — seul thermomètre
    # honnête de la generalisation de la value head.
    held_out: deque[
        tuple[np.ndarray, np.ndarray, float, tuple[int, int, int] | None, str]
    ] = deque(maxlen=config.held_out_size)
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
    else:
        # Warm-start : le candidat part des poids du champion, pas de zéro.
        # Sans ça, le candidat doit réapprendre de zéro à chaque run et ne
        # dépasse jamais le seuil arena de 0.55.
        net.load_state_dict({k: v.detach().clone() for k, v in best_net.state_dict().items()})
        logger.info("Warm-start : candidat initialisé depuis le champion (%s).", best_path)

    # Checkpoints disponibles pour l'adversaire aléatoire (25 %).
    checkpoint_paths: list[str] = sorted(
        glob.glob(os.path.join(config.model_dir, f"model_{config.num_players}_ckpt_*.pth"))
    )

    # Pool ancré (fictitious play) : charge une fois les checkpoints toujours présents.
    # Restent figés en mémoire — ancrent le self-play sur le bon bassin (anti-dérive).
    anchor_nets: list[CourtisansNet] = []
    for apath in config.anchor_checkpoints:
        anet = load_model(apath, env_tmp)
        if anet is not None:
            anet.eval()
            anchor_nets.append(anet)
            logger.info("Ancre chargée dans le pool : %s", apath)
        else:
            logger.warning("Ancre introuvable, ignorée : %s", apath)

    for it in range(config.iterations):
        if progress_callback:
            progress_callback(it / max(1, config.iterations), f"Iteration {it}/{config.iterations}")

        # Schedule progressif de simulations.
        eff_sims = _get_effective_sims(config, it)

        # Adversaire pour cette itération : 25 % du temps un checkpoint passé,
        # sinon None (self-play pur du champion). Décidé une fois par itération.
        opponent_net: CourtisansNet | None = None
        has_pool = bool(checkpoint_paths) or bool(anchor_nets)
        if config.past_checkpoint_ratio > 0 and has_pool and random.random() < config.past_checkpoint_ratio:
            # Branche "adversaire passé" : ancre (figée) vs checkpoint récent (aléatoire).
            use_anchor = anchor_nets and (
                not checkpoint_paths or random.random() < config.anchor_ratio
            )
            if use_anchor:
                opponent_net = random.choice(anchor_nets)
            else:
                opponent_net = load_model(random.choice(checkpoint_paths), env_tmp)

        # Self-play avec le CHAMPION (best_net), pas le candidat (net).
        # Empêche les parties dégradées du candidat de polluer le buffer.
        n_games = max(1, config.num_parallel_games)
        best_net.eval()
        if n_games > 1:
            with ThreadPoolExecutor(max_workers=n_games) as executor:
                game_results = list(
                    executor.map(
                        lambda _: _run_one_game(best_net, config, opponent_net, eff_sims),
                        range(n_games),
                    )
                )
        else:
            game_results = [_run_one_game(best_net, config, opponent_net, eff_sims)]

        scores = game_results[-1][1]
        for game_samples, _ in game_results:
            for sample in game_samples:
                # Route held_out_ratio des samples vers le buffer held-out (jamais entraîné).
                if config.held_out_ratio > 0 and random.random() < config.held_out_ratio:
                    held_out.append(sample)
                else:
                    memory.append(sample)

        # Étapes d'optimisation (train_steps_per_iter passes sur des batchs distincts).
        last_loss = last_loss_pi = last_loss_v = 0.0
        last_v_corr = last_pi_entropy = float("nan")
        if len(memory) > config.batch_size:
            for _ in range(config.train_steps_per_iter):
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
                    log_softmax_main = F.log_softmax(main_logits, dim=1)

                    if config.use_mcts:
                        # MCTS standard : cross-entropy avec les visites MCTS.
                        loss_pi_main = (
                            -torch.sum(main_targets * log_softmax_main) / len(main_idx)
                        )
                    elif config.awr_beta > 0:
                        # Fork 2 — Option C : AWR (Advantage Weighted Regression).
                        # loss = -exp((z - z_mean) / beta) * log π(a).
                        # Utilise toutes les parties (perdantes incluses, poids négatif).
                        # Off-policy-safe + évite le crédit binaire de l'Option A.
                        z_main = values_tensor[main_idx]          # (n, 1)
                        z_mean = z_main.mean()
                        advantage = (z_main - z_mean) / config.awr_beta
                        weights = advantage.exp().clamp(max=config.awr_weight_clip)
                        per_sample = torch.sum(
                            main_targets * log_softmax_main, dim=1, keepdim=True
                        )
                        loss_pi_main = -torch.sum(weights * per_sample) / len(main_idx)
                    else:
                        # Fork 2 — Option A : self-imitation pondérée par max(z, 0).
                        z_main = values_tensor[main_idx]          # (n, 1)
                        z_weights = z_main.clamp(min=0.0)
                        per_sample = torch.sum(
                            main_targets * log_softmax_main, dim=1, keepdim=True
                        )
                        denom = float(z_weights.sum().item()) or 1.0
                        loss_pi_main = -torch.sum(z_weights * per_sample) / denom

                    # Bonus d'entropie (Fork 2 ET MCTS) pour maintenir la stochasticité.
                    if config.entropy_coef > 0:
                        probs_main = F.softmax(main_logits, dim=1)
                        entropy_main = -(probs_main * (probs_main + 1e-9).log()).sum(1).mean()
                        loss_pi_main = loss_pi_main - config.entropy_coef * entropy_main

                if target_idx:
                    target_logits = pi_target_pred[target_idx]
                    target_targets = torch.from_numpy(np.array(aug_target_policies)).to(DEVICE)
                    log_softmax_tgt = F.log_softmax(target_logits, dim=1)

                    if config.use_mcts:
                        loss_pi_target = (
                            -torch.sum(target_targets * log_softmax_tgt) / len(target_idx)
                        )
                    elif config.awr_beta > 0:
                        z_tgt = values_tensor[target_idx]
                        z_mean_tgt = z_tgt.mean()
                        adv_tgt = (z_tgt - z_mean_tgt) / config.awr_beta
                        w_tgt = adv_tgt.exp().clamp(max=config.awr_weight_clip)
                        per_tgt = torch.sum(target_targets * log_softmax_tgt, dim=1, keepdim=True)
                        loss_pi_target = -torch.sum(w_tgt * per_tgt) / len(target_idx)
                    else:
                        z_tgt = values_tensor[target_idx]
                        z_weights_tgt = z_tgt.clamp(min=0.0)
                        per_sample_tgt = torch.sum(
                            target_targets * log_softmax_tgt, dim=1, keepdim=True
                        )
                        denom_tgt = float(z_weights_tgt.sum().item()) or 1.0
                        loss_pi_target = -torch.sum(z_weights_tgt * per_sample_tgt) / denom_tgt

                loss_v = F.mse_loss(v_pred, values_tensor)
                loss_pi = loss_pi_main + loss_pi_target
                loss = loss_pi + loss_v

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                last_loss = loss.item()
                last_loss_pi = loss_pi.item()
                last_loss_v = loss_v.item()

                # Instrumentation : corrélation v_pred/v_target + entropie policy main.
                v_np = v_pred.detach().cpu().float().numpy().flatten()
                t_np = values_tensor.detach().cpu().numpy().flatten()
                if v_np.std() > 1e-6 and t_np.std() > 1e-6:
                    last_v_corr = float(np.corrcoef(v_np, t_np)[0, 1])
                else:
                    last_v_corr = float("nan")
                if main_idx:
                    probs = F.softmax(pi_main_pred[main_idx].detach(), dim=1)
                    last_pi_entropy = float(
                        -(probs * (probs + 1e-9).log()).sum(1).mean().item()
                    )

            scheduler.step()

            # Held-out v_corr (OOD) — mesure honnête de la généralisation value.
            last_heldout_corr = float("nan")
            if config.held_out_ratio > 0 and len(held_out) >= config.batch_size:
                ho_batch = random.sample(list(held_out), min(512, len(held_out)))
                ho_states = torch.from_numpy(
                    np.array([s for s, *_ in ho_batch])
                ).to(DEVICE)
                ho_vals = np.array([v for _, _, v, *_ in ho_batch], dtype=np.float32)
                net.eval()
                with torch.no_grad():
                    _, _, ho_pred = net(ho_states)
                ho_pred_np = ho_pred.cpu().float().numpy().flatten()
                if ho_pred_np.std() > 1e-6 and ho_vals.std() > 1e-6:
                    last_heldout_corr = float(np.corrcoef(ho_pred_np, ho_vals)[0, 1])

            if it % 10 == 0:
                logger.info(
                    "Iter %d | loss=%.4f (pi=%.4f v=%.4f) | v_corr=%.3f v_corr_ood=%.3f pi_ent=%.3f | lr=%.2e | top_score=%d",
                    it, last_loss, last_loss_pi, last_loss_v,
                    last_v_corr, last_heldout_corr, last_pi_entropy,
                    optimizer.param_groups[0]["lr"], max(scores.values()),
                )

        # Checkpoint intermédiaire
        if config.checkpoint_every and (it + 1) % config.checkpoint_every == 0:
            ckpt = os.path.join(
                config.model_dir, f"model_{config.num_players}_ckpt_{it + 1}.pth"
            )
            torch.save(net.state_dict(), ckpt)
            checkpoint_paths.append(ckpt)
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

        # Benchmark trois courbes vs greedy : policy-brute / MCTS-on / MCTS-off.
        if config.greedy_benchmark_every and (it + 1) % config.greedy_benchmark_every == 0:
            from app.greedy_bot import benchmark_threecurves  # import local
            tc = benchmark_threecurves(
                net,
                num_games=config.greedy_benchmark_games,
                num_sims=config.arena_num_sims,
                num_players=config.num_players,
                mcts_on_cls=MCTSHeuristicValue if config.heuristic_value else MCTS,
            )
            logger.info(
                "Greedy (iter %d) | policy_only=%.3f | mcts_on=%.3f | mcts_off=%.3f",
                it + 1,
                tc["policy_only"]["winrate"],
                tc["mcts_on"]["winrate"],
                tc["mcts_off"]["winrate"],
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

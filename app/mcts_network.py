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
    num_sims: int = 30
    c_puct: float = 1.5
    lr: float = 1e-3
    memory_size: int = 5000
    batch_size: int = 64
    # Exploration
    warmup_iters: int = 20
    epsilon_random: float = 0.10
    dirichlet_alpha: float = 0.3
    dirichlet_epsilon: float = 0.25
    # Checkpoint
    checkpoint_every: int = 25
    model_dir: str = "models"
    seed: int | None = None


# ======================================================================================
# 1. RESEAU DE NEURONES (ResNet)
# ======================================================================================
class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.fc1 = nn.Linear(hidden_dim, hidden_dim)
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = F.relu(self.bn1(self.fc1(x)))
        out = self.bn2(self.fc2(out))
        out += residual
        return F.relu(out)


class CourtisansNet(nn.Module):
    def __init__(self, input_dim: int, action_dim: int, num_blocks: int = 5) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.action_dim = action_dim

        self.start_fc = nn.Linear(input_dim, 512)
        self.bn_start = nn.BatchNorm1d(512)
        self.res_blocks = nn.ModuleList([ResidualBlock(512) for _ in range(num_blocks)])

        self.policy_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, action_dim),  # logits
        )
        self.value_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = F.relu(self.bn_start(self.start_fc(x)))
        for block in self.res_blocks:
            x = block(x)
        return self.policy_head(x), self.value_head(x)


# ======================================================================================
# 2. MCTS
# ======================================================================================
class MCTSNode:
    __slots__ = ("parent", "children", "visit_count", "value_sum", "prior", "player")

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

    def __init__(
        self,
        model: CourtisansNet,
        num_sims: int = 50,
        c_puct: float = 1.5,
        dirichlet_alpha: float = 0.3,
        dirichlet_epsilon: float = 0.25,
    ) -> None:
        self.model = model
        self.num_sims = num_sims
        self.c_puct = c_puct
        self.dirichlet_alpha = dirichlet_alpha
        self.dirichlet_epsilon = dirichlet_epsilon

    def search(self, env: GameEnv, add_root_noise: bool = False) -> np.ndarray:
        root_env = env.clone_determinized()
        root = MCTSNode(player=root_env.current_player)
        self._expand(root, root_env)

        if add_root_noise:
            self._apply_dirichlet(root)

        for _ in range(self.num_sims):
            node = root
            sim_env = root_env.clone_determinized()

            # 1. Sélection
            while node.children and not self._is_terminal(sim_env):
                best_score = -float("inf")
                best_child: MCTSNode | None = None
                best_action = -1
                total_visits = sum(c.visit_count for c in node.children.values())
                sqrt_total = np.sqrt(total_visits) if total_visits > 0 else 1.0

                for action, child in node.children.items():
                    # Q vu depuis le parent : pour 2 joueurs c'est -child.value()
                    # (somme nulle). Pour N joueurs on garde l'approximation
                    # zéro-sum entre node.player et le reste.
                    q_value = -child.value()
                    u = self.c_puct * child.prior * sqrt_total / (1 + child.visit_count)
                    score = q_value + u
                    if score > best_score:
                        best_score = score
                        best_action = action
                        best_child = child

                if best_child is None:
                    break
                node = best_child
                sim_env.step(best_action)

            # 2. Expansion / Évaluation
            if not self._is_terminal(sim_env):
                value = self._expand(node, sim_env)
            else:
                value = self._terminal_value(sim_env)

            # 3. Backprop
            cur = node
            cur_value = value
            while cur is not None:
                cur.value_sum += cur_value
                cur.visit_count += 1
                # On change de perspective à chaque remontée (approximation
                # zéro-sum valide pour 2 joueurs, raisonnable pour N joueurs).
                cur_value = -cur_value
                cur = cur.parent

        # Probas finales (visite-comptage normalisé)
        counts = np.zeros(env.mapper.get_action_space_size(), dtype=np.float32)
        for act, child in root.children.items():
            counts[act] = child.visit_count
        total = counts.sum()
        if total > 0:
            counts /= total
        return counts

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
        vec = env.get_state_vector()
        tensor = torch.from_numpy(vec).unsqueeze(0).to(DEVICE)

        self.model.eval()
        with torch.no_grad():
            logits, v = self.model(tensor)

        legal = env.get_legal_actions()
        if not legal:
            return float(v.item())

        # Masquage AVANT softmax : on met les logits illégaux à -inf.
        mask = torch.full_like(logits, float("-inf"))
        mask[0, legal] = logits[0, legal]
        probs = F.softmax(mask, dim=1).cpu().numpy()[0]

        # Sécurité numérique : si tout est nan (cas extrême), uniforme sur legal.
        if not np.isfinite(probs).all() or probs.sum() <= 0:
            probs = np.zeros_like(probs)
            probs[legal] = 1.0 / len(legal)

        child_player = env.current_player
        for idx in legal:
            if probs[idx] > 0:
                node.children[idx] = MCTSNode(node, prior=float(probs[idx]), player=child_player)

        return float(v.item())

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
    optimizer = optim.Adam(net.parameters(), lr=config.lr)
    mcts = MCTS(
        net,
        num_sims=config.num_sims,
        c_puct=config.c_puct,
        dirichlet_alpha=config.dirichlet_alpha,
        dirichlet_epsilon=config.dirichlet_epsilon,
    )

    memory: deque[tuple[np.ndarray, np.ndarray, float]] = deque(maxlen=config.memory_size)
    os.makedirs(config.model_dir, exist_ok=True)

    for it in range(config.iterations):
        if progress_callback:
            progress_callback(it / max(1, config.iterations), f"Iteration {it}/{config.iterations}")

        env = GameEnv(config.num_players)
        history: list[tuple[np.ndarray, np.ndarray, int]] = []
        done = False

        # Self-play
        while not done:
            s_vec = env.get_state_vector()
            probs = mcts.search(env, add_root_noise=True)

            if it < config.warmup_iters:
                action = int(np.random.choice(len(probs), p=probs))
            else:
                if random.random() < config.epsilon_random:
                    action = int(np.random.choice(len(probs), p=probs))
                else:
                    action = int(np.argmax(probs))

            history.append((s_vec, probs, env.current_player))
            _, _, done, info = env.step(action)
            # Si un assassin pending arrive durant le self-play (joueur 0 IA aussi),
            # on auto-résout en choisissant la première cible — placeholder simple.
            while info.get("assassin_pending"):
                ctx = env.pending_assassin_context
                victim = ctx["targets"][0] if ctx["targets"] else None
                _, _, done, info = env.resolve_assassin_manual(victim)

        # Reward final attribué à chaque état selon le joueur qui devait jouer.
        scores = env._calcul_scores()
        for s, p, player_id in history:
            my_score = scores[player_id]
            others = [v for k, v in scores.items() if k != player_id]
            avg_others = sum(others) / len(others)
            val = max(-1.0, min(1.0, (my_score - avg_others) / 20.0))
            memory.append((s, p, val))

        # Étape d'optimisation
        if len(memory) > config.batch_size:
            batch = random.sample(memory, config.batch_size)
            bs = torch.from_numpy(np.array([x[0] for x in batch])).to(DEVICE)
            bp = torch.from_numpy(np.array([x[1] for x in batch])).to(DEVICE)
            bv = torch.from_numpy(np.array([x[2] for x in batch], dtype=np.float32)).unsqueeze(1).to(DEVICE)

            net.train()
            pi_pred, v_pred = net(bs)
            loss_pi = -torch.sum(bp * F.log_softmax(pi_pred, dim=1)) / config.batch_size
            loss_v = F.mse_loss(v_pred, bv)
            loss = loss_pi + loss_v

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

    # Sauvegarde finale
    final_path = os.path.join(config.model_dir, f"model_{config.num_players}.pth")
    torch.save(net.state_dict(), final_path)
    logger.info("Final model saved: %s", final_path)
    return net


def load_model(model_path: str, env: GameEnv) -> CourtisansNet | None:
    """Charge un modèle si présent, sinon None. Utilise weights_only=True."""
    if not os.path.exists(model_path):
        logger.info("No model at %s", model_path)
        return None
    net = CourtisansNet(env.get_state_vector_size(), env.mapper.get_action_space_size()).to(DEVICE)
    try:
        net.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
    except (FileNotFoundError, RuntimeError) as exc:
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

        while info.get("assassin_pending"):
            ctx = env.pending_assassin_context
            victim = ctx["targets"][0] if ctx["targets"] else None
            _, _, _, info = env.resolve_assassin_manual(victim)

    print("Scores:", env._calcul_scores())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    train(config=TrainConfig(num_players=2, iterations=50))

"""Batterie de diagnostics rapides (< 15 min au total).

Usage :
    uv run python scripts/diagnostics.py

Diagnostics :
  1. Random vs Greedy          — baseline manquante
  2. Random vs Champion        — le champion bat-il seulement le hasard ?
  3. Policy-seule (0 sim) vs Greedy / Random  — le réseau a-t-il appris hors MCTS ?
  4. Candidat v7 vs Greedy à 30 / 100 / 200 / 500 sims  — value calibrée ou nuisible ?
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.greedy_bot import greedy_action_main, greedy_action_target
from app.jeu import GameEnv
from app.mcts_network import DEVICE, MCTS, CourtisansNet, load_model

NUM_GAMES = 200
NUM_PLAYERS = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_action(env: GameEnv) -> int:
    legal = env.get_legal_actions()
    return random.choice(legal) if legal else 0


def random_action_target(env: GameEnv) -> int | None:
    ctx = env.pending_assassin_context
    if not ctx:
        return None
    targets = list(ctx["targets"])
    return random.choice([None, *targets])


def play_game(policy_a, policy_a_target, policy_b, policy_b_target) -> int | None:
    """Joue une partie A (joueur 0) vs B (joueur 1). Retourne 0, 1 ou None."""
    env = GameEnv(NUM_PLAYERS)
    while not env.is_done():
        cp = env.current_player
        if env.pending_assassin_context is not None:
            fn = policy_a_target if cp == 0 else policy_b_target
            victim = fn(env)
            env.resolve_assassin_manual(victim)
        else:
            fn = policy_a if cp == 0 else policy_b
            action = fn(env)
            env.step(action)
    scores = env._calcul_scores()
    if scores[0] > scores[1]:
        return 0
    if scores[1] > scores[0]:
        return 1
    return None


def run_benchmark(name: str, policy_a, policy_a_target, policy_b, policy_b_target,
                  n: int = NUM_GAMES) -> dict:
    wins = losses = draws = 0
    for g in range(n):
        if g % 2 == 0:
            r = play_game(policy_a, policy_a_target, policy_b, policy_b_target)
            if r is None:
                draws += 1
            elif r == 0:
                wins += 1
            else:
                losses += 1
        else:
            r = play_game(policy_b, policy_b_target, policy_a, policy_a_target)
            if r is None:
                draws += 1
            elif r == 1:
                wins += 1
            else:
                losses += 1
    decisive = wins + losses
    wr = wins / decisive if decisive > 0 else 0.0
    print(f"{name:50s}  wins={wins:3d} losses={losses:3d} draws={draws:3d}  winrate={wr:.3f}")
    return {"wins": wins, "losses": losses, "draws": draws, "winrate": wr}


def net_policy(net: CourtisansNet, num_sims: int):
    """Renvoie (policy_main_fn, policy_target_fn) pour un réseau avec MCTS."""
    if num_sims == 0:
        # Policy seule : argmax des logits bruts, 0 simulation MCTS
        def main_fn(env: GameEnv) -> int:
            vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits_main, _, _ = net(vec)
            legal = env.get_legal_actions()
            logits = logits_main[0].cpu().numpy()
            mask = np.full(len(logits), -1e9)
            mask[legal] = logits[legal]
            return int(np.argmax(mask))

        def target_fn(env: GameEnv) -> int | None:
            ctx = env.pending_assassin_context
            if not ctx:
                return None
            targets = list(ctx["targets"])
            vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                _, logits_target, _ = net(vec)
            logits = logits_target[0].cpu().numpy()
            best_slot = int(np.argmax(logits[:len(targets) + 1]))
            if best_slot >= len(targets):
                return None
            return targets[best_slot]

        return main_fn, target_fn
    else:
        mcts = MCTS(net, num_sims=num_sims)

        def main_fn(env: GameEnv) -> int:
            probs = mcts.search(env)
            return int(np.argmax(probs))

        def target_fn(env: GameEnv) -> int | None:
            ctx = env.pending_assassin_context
            if not ctx:
                return None
            targets = list(ctx["targets"])
            probs = mcts.search(env)
            slot = int(np.argmax(probs))
            if slot >= len(targets):
                return None
            return targets[slot]

        return main_fn, target_fn


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("DIAGNOSTICS COURTISANS")
    print("=" * 70)

    env_tmp = GameEnv(NUM_PLAYERS)

    # Charger les modèles
    champion = load_model("models/model_2.pth", env_tmp)
    candidate = load_model("models/model_2_candidate.pth", env_tmp)

    if champion is None:
        print("WARN: models/model_2.pth introuvable")
    if candidate is None:
        print("WARN: models/model_2_candidate.pth introuvable")

    print()
    print("--- 1. BASELINES ---")
    run_benchmark(
        "Random vs Greedy",
        random_action, random_action_target,
        greedy_action_main, greedy_action_target,
    )
    if champion:
        champ_main, champ_target = net_policy(champion, num_sims=30)
        run_benchmark(
            "Random vs Champion (30 sims)",
            random_action, random_action_target,
            champ_main, champ_target,
        )

    print()
    print("--- 2. POLICY SEULE (0 sim) ---")
    if champion:
        champ0_main, champ0_target = net_policy(champion, num_sims=0)
        run_benchmark("Champion (0 sim) vs Random", champ0_main, champ0_target,
                      random_action, random_action_target)
        run_benchmark("Champion (0 sim) vs Greedy", champ0_main, champ0_target,
                      greedy_action_main, greedy_action_target)
    if candidate:
        cand0_main, cand0_target = net_policy(candidate, num_sims=0)
        run_benchmark("Candidat v7 (0 sim) vs Random", cand0_main, cand0_target,
                      random_action, random_action_target)
        run_benchmark("Candidat v7 (0 sim) vs Greedy", cand0_main, cand0_target,
                      greedy_action_main, greedy_action_target)

    print()
    print("--- 3. CANDIDAT v7 vs GREEDY — budget de sims ---")
    if candidate:
        for sims in [30, 100, 200, 500]:
            cand_main, cand_target = net_policy(candidate, num_sims=sims)
            run_benchmark(
                f"Candidat v7 ({sims:3d} sims) vs Greedy",
                cand_main, cand_target,
                greedy_action_main, greedy_action_target,
                n=100,  # 100 parties par sim-count pour limiter le temps
            )

    print()
    print("Diagnostics terminés.")

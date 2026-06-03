"""Benchmark rapide pour estimer le temps d'entraînement.

Lance N iterations de self-play + training step et extrapole vers 3h.

Usage :
    uv run python scripts/benchmark.py
    uv run python scripts/benchmark.py --iterations 10 --num-sims 100
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.mcts_network import MCTS, CourtisansNet, TrainConfig, _seed_everything
from app.jeu import GameEnv
from app.augmentation import augment_sample, augment_target_sample
import numpy as np
import random
import torch.optim as optim


def run_benchmark(cfg: TrainConfig, target_hours: float = 3.0) -> None:
    print("\n" + "=" * 60)
    print("BENCHMARK — Courtisans AlphaZero")
    print("=" * 60)

    import torch
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    device_str = f"CUDA ({device_name})" if torch.cuda.is_available() else "CPU"
    print(f"Device       : {device_str}")
    if torch.cuda.is_available():
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"VRAM         : {vram_gb:.1f} GB")
    print(f"num_players  : {cfg.num_players}")
    print(f"num_sims     : {cfg.num_sims}")
    print(f"num_worlds   : {cfg.num_worlds}")
    print(f"mcts_batch   : {cfg.mcts_batch_size}")
    print(f"batch_size   : {cfg.batch_size}")
    print(f"Iterations   : {cfg.iterations}")
    print("-" * 60)

    _seed_everything(cfg.seed)

    from app.mcts_network import DEVICE
    env_tmp = GameEnv(cfg.num_players, seed=cfg.seed)
    input_dim = env_tmp.get_state_vector_size()
    action_dim = env_tmp.mapper.get_action_space_size()

    net = CourtisansNet(input_dim, action_dim).to(DEVICE)
    optimizer = optim.AdamW(net.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    mcts = MCTS(
        net,
        num_sims=cfg.num_sims,
        num_worlds=cfg.num_worlds,
        batch_size=cfg.mcts_batch_size,
    )

    memory: deque = deque(maxlen=cfg.memory_size)

    selfplay_times: list[float] = []
    train_times: list[float] = []
    game_lengths: list[int] = []

    print(f"\n{'Iter':>4}  {'Self-play':>10}  {'Train':>8}  {'Total':>8}  {'Moves':>6}")
    print("-" * 50)

    for it in range(cfg.iterations):
        # ── Self-play ─────────────────────────────────────────
        t0 = time.perf_counter()
        env = GameEnv(cfg.num_players)
        history = []
        done = False
        move_in_game = 0

        while not done:
            s_vec = env.get_state_vector()
            hand_keys = tuple(sorted(env.cartes[i].sort_key for i in env.mains[env.current_player]))
            if len(hand_keys) != 3:
                break

            probs_main = mcts.search(env, add_root_noise=True)
            if move_in_game < cfg.temperature_threshold:
                action = int(np.random.choice(len(probs_main), p=probs_main))
            else:
                action = int(np.argmax(probs_main))

            history.append((s_vec, probs_main, env.current_player, hand_keys, "main"))
            _, _, done, info = env.step(action)
            move_in_game += 1

            while info.get("assassin_pending") and not done:
                target_state = env.get_state_vector()
                target_player = env.current_player
                ctx = env.pending_assassin_context
                ctx_targets = list(ctx["targets"]) if ctx else []

                probs_target = mcts.search(env, add_root_noise=False)
                if move_in_game < cfg.temperature_threshold:
                    slot = int(np.random.choice(len(probs_target), p=probs_target))
                else:
                    slot = int(np.argmax(probs_target))

                victim = ctx_targets[slot] if 0 <= slot < len(ctx_targets) else None
                history.append((target_state, probs_target, target_player, None, "target"))
                _, _, done, info = env.resolve_assassin_manual(victim)

        scores = env._calcul_scores()
        for s, p, player_id, hk, mode in history:
            my_score = scores[player_id]
            others = [v for k, v in scores.items() if k != player_id]
            val = max(-1.0, min(1.0, (my_score - sum(others) / len(others)) / 20.0))
            memory.append((s, p, val, hk, mode))

        t_selfplay = time.perf_counter() - t0
        selfplay_times.append(t_selfplay)
        game_lengths.append(move_in_game)

        # ── Training step ──────────────────────────────────────
        t1 = time.perf_counter()
        if len(memory) > cfg.batch_size:
            raw_batch = random.sample(memory, cfg.batch_size)
            aug_states, aug_values, aug_modes = [], [], []
            aug_main_policies, aug_target_policies = [], []

            for s, p, v, hk, mode in raw_batch:
                if mode == "main":
                    if cfg.family_augmentation and hk is not None:
                        new_s, new_p, _ = augment_sample(s, p, hk, env_tmp.mapper)
                    else:
                        new_s, new_p = s, p
                    aug_states.append(new_s)
                    aug_values.append(v)
                    aug_modes.append("main")
                    aug_main_policies.append(new_p)
                else:
                    if cfg.family_augmentation:
                        new_s, new_p = augment_target_sample(s, p, env_tmp.mapper)
                    else:
                        new_s, new_p = s, p
                    aug_states.append(new_s)
                    aug_values.append(v)
                    aug_modes.append("target")
                    aug_target_policies.append(new_p)

            states_t = torch.tensor(np.array(aug_states), dtype=torch.float32).to(DEVICE)
            values_t = torch.tensor(aug_values, dtype=torch.float32).to(DEVICE)

            main_idx = [i for i, m in enumerate(aug_modes) if m == "main"]
            tgt_idx  = [i for i, m in enumerate(aug_modes) if m == "target"]

            pi_main, pi_target, v_pred = net(states_t)
            v_pred = v_pred.squeeze(-1)
            loss_v = ((v_pred - values_t) ** 2).mean()

            loss_pi_main = torch.tensor(0.0, device=DEVICE)
            if main_idx and aug_main_policies:
                mp = torch.tensor(
                    np.array(aug_main_policies), dtype=torch.float32
                ).to(DEVICE)
                logp = torch.log_softmax(pi_main[main_idx], dim=-1)
                loss_pi_main = -(mp * logp).sum() / len(main_idx)

            loss_pi_target = torch.tensor(0.0, device=DEVICE)
            if tgt_idx and aug_target_policies:
                tp = torch.tensor(
                    np.array(aug_target_policies), dtype=torch.float32
                ).to(DEVICE)
                logp = torch.log_softmax(pi_target[tgt_idx], dim=-1)
                loss_pi_target = -(tp * logp).sum() / len(tgt_idx)

            loss = loss_pi_main + loss_pi_target + loss_v
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        t_train = time.perf_counter() - t1
        train_times.append(t_train)
        total = t_selfplay + t_train

        print(f"{it+1:>4}  {t_selfplay:>9.2f}s  {t_train:>7.3f}s  {total:>7.2f}s  {move_in_game:>6}")

    # ── Résultats ──────────────────────────────────────────────
    avg_sp   = sum(selfplay_times) / len(selfplay_times)
    avg_tr   = sum(train_times) / len(train_times)
    avg_tot  = avg_sp + avg_tr
    avg_moves = sum(game_lengths) / len(game_lengths)

    target_secs = target_hours * 3600
    estimated_iters = int(target_secs / avg_tot)

    print("\n" + "=" * 60)
    print("RÉSULTATS")
    print("=" * 60)
    print(f"Temps moyen / itération  : {avg_tot:.2f}s")
    print(f"  dont self-play         : {avg_sp:.2f}s  ({100*avg_sp/avg_tot:.0f}%)")
    print(f"  dont training step     : {avg_tr:.3f}s  ({100*avg_tr/avg_tot:.0f}%)")
    print(f"Durée moyenne d'une partie : {avg_moves:.1f} coups")
    print(f"Vitesse : {3600/avg_tot:.0f} itérations/heure")
    print("-" * 60)
    print(f"Estimation pour {target_hours:.0f}h : ~{estimated_iters} itérations")
    print(f"  (avec arena toutes les 50 iters — prévoyez +5-10% de marge)")
    print("=" * 60)

    # Recommandation d'hyperparamètres
    print("\nCOMMANDE SUGGÉRÉE pour l'entraînement :")
    print(f"  uv run python main.py train \\")
    print(f"    --iterations {estimated_iters} \\")
    print(f"    --num-sims {cfg.num_sims} \\")
    print(f"    --num-worlds {cfg.num_worlds}")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark entraînement Courtisans")
    p.add_argument("--iterations", type=int, default=8, help="Nombre d'itérations de benchmark (8 par défaut)")
    p.add_argument("--num-sims", type=int, default=50)
    p.add_argument("--num-players", type=int, default=2)
    p.add_argument("--num-worlds", type=int, default=1)
    p.add_argument("--mcts-batch-size", type=int, default=1)
    p.add_argument("--target-hours", type=float, default=3.0)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    cfg = TrainConfig(
        iterations=args.iterations,
        num_sims=args.num_sims,
        num_players=args.num_players,
        num_worlds=args.num_worlds,
        mcts_batch_size=args.mcts_batch_size,
        seed=args.seed,
    )
    run_benchmark(cfg, target_hours=args.target_hours)


if __name__ == "__main__":
    main()

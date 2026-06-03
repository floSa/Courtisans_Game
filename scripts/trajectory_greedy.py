"""Étape 2 — Trajectoire appariée d'un run vs le NOUVEAU greedy.

Mesure tous les checkpoints `model_2_ckpt_*.pth` d'un dossier, policy_only,
apparié (même donne par partie), et imprime la courbe iter -> winrate.

But : trancher "ça monte (volume débloque)" vs "ça plafonne (pivot credit
assignment / CFR)". Aucun chiffre non-apparié ne déclenche de décision.

Usage : uv run python scripts/trajectory_greedy.py [model_dir] [n_games]
"""
import sys, os, re, math, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
MODEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "models"
N_GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 200


def play_policy_only(net, net_starts, seed):
    env = GameEnv(NUM_PLAYERS, seed=seed)
    net_slot = 0 if net_starts else 1
    net.eval()
    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == net_slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    _, logits_t, _ = net(vec)
                targets = list(env.pending_assassin_context["targets"])
                logits = logits_t[0].cpu().numpy()
                slot = int(np.argmax(logits[: len(targets) + 1]))
                victim = targets[slot] if slot < len(targets) else None
                env.resolve_assassin_manual(victim)
            else:
                env.resolve_assassin_manual(greedy_action_target(env))
        else:
            if env.current_player == net_slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    logits_m, _, _ = net(vec)
                legal = env.get_legal_actions()
                logits = logits_m[0].cpu().numpy()
                mask = np.full(len(logits), -1e9)
                mask[legal] = logits[legal]
                action = int(np.argmax(mask))
            else:
                action = greedy_action_main(env)
            env.step(action)
    scores = env._calcul_scores()
    if scores[net_slot] > scores[1 - net_slot]:
        return 0
    if scores[1 - net_slot] > scores[net_slot]:
        return 1
    return None


def benchmark(net, n=N_GAMES):
    results = [play_policy_only(net, g % 2 == 0, g * 13337 + 42) for g in range(n)]
    w, l, d = results.count(0), results.count(1), results.count(None)
    dec = w + l
    wr = w / dec if dec > 0 else 0.0
    ci = 1.96 * math.sqrt(wr * (1 - wr) / dec) if dec > 0 else 0.0
    return wr, ci, w, l, d


def ckpt_iter(path):
    m = re.search(r"ckpt_(\d+)\.pth$", path)
    return int(m.group(1)) if m else -1


if __name__ == "__main__":
    env_tmp = GameEnv(NUM_PLAYERS)
    paths = sorted(
        glob.glob(os.path.join(MODEL_DIR, f"model_{NUM_PLAYERS}_ckpt_*.pth")),
        key=ckpt_iter,
    )
    print(f"=== Trajectoire vs NOUVEAU greedy | dir={MODEL_DIR} | N={N_GAMES} paired ===", flush=True)
    print(f"{'iter':>6}  {'wr':>6}  {'CI':>6}  W/L/D", flush=True)
    for p in paths:
        net = load_model(p, env_tmp)
        if net is None:
            continue
        wr, ci, w, l, d = benchmark(net)
        print(f"{ckpt_iter(p):>6}  {wr:.3f}  ±{ci:.3f}  [{w}/{l}/{d}]", flush=True)

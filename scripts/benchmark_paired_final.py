"""Benchmark apparié policy_only vs greedy — mesure propre du champion courant.

N=300 parties, même donne (GameEnv seed=g), CI ±5.7% worst-case.
Compare aussi avec un 2e modèle (original si disponible).
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
N_GAMES = 300

def play_policy_only(net, num_players, net_starts, seed):
    env = GameEnv(num_players, seed=seed)
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
                slot = int(np.argmax(logits[:len(targets)+1]))
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
    if scores[net_slot] > scores[1-net_slot]: return 0
    if scores[1-net_slot] > scores[net_slot]: return 1
    return None

def benchmark(net, label, n=N_GAMES):
    results = []
    for g in range(n):
        seed = g * 13337 + 42
        results.append(play_policy_only(net, NUM_PLAYERS, g % 2 == 0, seed))
    w = results.count(0); l = results.count(1); d = results.count(None)
    dec = w + l
    wr = w / dec if dec > 0 else 0.0
    ci = 1.96 * math.sqrt(wr * (1-wr) / dec) if dec > 0 else 0.0
    print(f"{label:40s}  wr={wr:.3f} ±{ci:.3f}  [{w}W/{l}L/{d}D]  n={n}")
    return wr

env_tmp = GameEnv(NUM_PLAYERS)

# Champion actuel : Fork 2b iter 75
net_champion = load_model("models/model_2.pth", env_tmp)
benchmark(net_champion, "Fork2b iter75 (champion actuel)", N_GAMES)

# Comparaison avec les checkpoints Fork 2d
for ckpt in sorted([f for f in os.listdir("models") if "ckpt" in f and f.endswith(".pth")])[-3:]:
    net_ckpt = load_model(f"models/{ckpt}", env_tmp)
    if net_ckpt:
        benchmark(net_ckpt, f"Ckpt {ckpt}", N_GAMES)

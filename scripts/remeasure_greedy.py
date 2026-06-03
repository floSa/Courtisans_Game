"""Étape 1 — Re-mesure du sol vs le NOUVEAU greedy (maximise l'écart, pas le score absolu).

Apparié : même donne (seed=g*13337+42) pour les deux camps, positions alternées.
N=300 → CI ±~5.7% worst-case. policy_only uniquement (0 sim), forward-pass pur.

But : obtenir le nouveau chiffre de référence du sol après correction du greedy.
Tous les chiffres greedy antérieurs (0.396, etc.) étaient vs l'ANCIEN greedy.
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

# Checkpoints clés à re-mesurer (label -> fichier)
MODELS = [
    ("v8_ckpt_250 (best prouve)", "models/model_2_ckpt_250.pth"),
    ("champion actuel (model_2)", "models/model_2.pth"),
    ("AWR candidate", "models/model_2_candidate.pth"),
]


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


def benchmark(net, label, n=N_GAMES):
    results = [play_policy_only(net, g % 2 == 0, g * 13337 + 42) for g in range(n)]
    w, l, d = results.count(0), results.count(1), results.count(None)
    dec = w + l
    wr = w / dec if dec > 0 else 0.0
    ci = 1.96 * math.sqrt(wr * (1 - wr) / dec) if dec > 0 else 0.0
    print(f"{label:32s}  wr={wr:.3f} ±{ci:.3f}  [{w}W/{l}L/{d}D]  n={n}", flush=True)
    return wr


if __name__ == "__main__":
    env_tmp = GameEnv(NUM_PLAYERS)
    print("=== Re-mesure vs NOUVEAU greedy (ecart), policy_only, paired N=300 ===", flush=True)
    for label, path in MODELS:
        if not os.path.exists(path):
            print(f"{label:32s}  (absent: {path})", flush=True)
            continue
        net = load_model(path, env_tmp)
        if net is not None:
            benchmark(net, label)

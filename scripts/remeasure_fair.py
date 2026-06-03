"""Re-mesure vs greedy ÉQUITABLE (PIMC, K déterminisations) — l'adversaire
n'utilise que l'info légalement disponible (ne voit plus les espions cachés).

Compare au greedy info-privilégié (K=0) pour quantifier l'effet du "triche".
Métrique : winrate apparié + écart de score moyen.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random as _random
import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
K = int(os.environ.get("FAIR_K", "8"))     # déterminisations du greedy équitable
N = int(os.environ.get("FAIR_N", "150"))


def net_move(net, env):
    vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
    if env.pending_assassin_context is not None:
        with torch.no_grad():
            _, lt, _ = net(vec)
        targets = list(env.pending_assassin_context["targets"])
        lt = lt[0].cpu().numpy()
        slot = int(np.argmax(lt[: len(targets) + 1]))
        return ("target", targets[slot] if slot < len(targets) else None)
    with torch.no_grad():
        lm, _, _ = net(vec)
    legal = env.get_legal_actions()
    lm = lm[0].cpu().numpy()
    mask = np.full(len(lm), -1e9, dtype=np.float32); mask[legal] = lm[legal]
    return ("main", int(np.argmax(mask)))


def play(net, net_starts, seed, k):
    env = GameEnv(NUM_PLAYERS, seed=seed)
    net_slot = 0 if net_starts else 1
    if net is not None:
        net.eval()
    while not env.is_done():
        is_net_turn = env.current_player == net_slot
        if env.pending_assassin_context is not None:
            if is_net_turn:
                if net is None:
                    ctx = list(env.pending_assassin_context["targets"])
                    victim = _random.choice([None, *ctx])
                else:
                    _, victim = net_move(net, env)
            else:
                victim = greedy_action_target(env, num_worlds=k)
            env.resolve_assassin_manual(victim)
        else:
            if is_net_turn:
                if net is None:
                    action = _random.choice(env.get_legal_actions())
                else:
                    _, action = net_move(net, env)
            else:
                action = greedy_action_main(env, num_worlds=k)
            env.step(action)
    sc = env._calcul_scores()
    return sc[net_slot] - sc[1 - net_slot]


def bench(net, label, k=K, n=N):
    w = l = d = 0; margin = 0.0
    for g in range(n):
        m = play(net, g % 2 == 0, g * 13337 + 42, k)
        margin += m
        if m > 0: w += 1
        elif m < 0: l += 1
        else: d += 1
    dec = w + l
    wr = w / dec if dec else 0.0
    ci = 1.96 * math.sqrt(wr * (1 - wr) / dec) if dec else 0.0
    print(f"{label:34s} K={k}  wr={wr:.3f} ±{ci:.3f}  ecart={margin/n:+.2f}  [{w}/{l}/{d}]  n={n}", flush=True)
    return wr


if __name__ == "__main__":
    env_tmp = GameEnv(NUM_PLAYERS)
    print(f"=== vs greedy EQUITABLE (PIMC K={K}), apparié N={N} ===", flush=True)
    # calibration : random vs fair greedy
    bench(None, "random (policy=None)")
    for label, path in [
        ("v8_ckpt_250", "models/model_2_ckpt_250.pth"),
        ("champion model_2", "models/model_2.pth"),
        ("AWR candidate", "models/model_2_candidate.pth"),
    ]:
        if os.path.exists(path):
            net = load_model(path, env_tmp)
            if net is not None:
                bench(net, label)

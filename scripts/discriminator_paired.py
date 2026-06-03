"""Test D6 — rollout greedy en feuille — ultime tiebreak MCTS.

Bras 1 : MCTSZeroValue     (value=0, PUCT pur, baseline)
Bras 2 : MCTSGreedyRollout (priors réseau + rollout greedy jusqu'au terminal)

Si bras2 > policy_only → MCTS avec bon signal de feuille aide. Pas de plafond r=0.4.
Si bras2 ≈ bras1 ou < policy_only → Fork 2 : la famille MCTS ne convient pas au jeu.

Common random numbers : GameEnv(seed=g) → même donne.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import MCTSZeroValue, MCTSGreedyRollout, DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

MODEL = "models/model_2.pth"
NUM_PLAYERS = 2
NUM_SIMS = 100   # réduit : rollout greedy ~5× plus lent par leaf expansion
N_GAMES = 100


def _play(net, num_sims, num_players, net_starts, seed, mcts_cls):
    env = GameEnv(num_players, seed=seed)
    mcts = mcts_cls(net, num_sims=num_sims)
    net_slot = 0 if net_starts else 1

    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                targets = list(env.pending_assassin_context["targets"])
                slot = int(np.argmax(probs))
                victim = targets[slot] if 0 <= slot < len(targets) else None
            else:
                victim = greedy_action_target(env)
            env.resolve_assassin_manual(victim)
        else:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                action = int(np.argmax(probs))
            else:
                action = greedy_action_main(env)
            env.step(action)

    scores = env._calcul_scores()
    if scores[net_slot] > scores[1 - net_slot]:
        return 0
    if scores[1 - net_slot] > scores[net_slot]:
        return 1
    return None


def _play_policy_only(net, num_players, net_starts, seed):
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


def winrate(results):
    w = results.count(0)
    l = results.count(1)
    d = results.count(None)
    dec = w + l
    return w / dec if dec > 0 else 0.0, w, l, d


def paired_stats(a, b):
    def enc(r):
        return 0 if r is None else (1 if r == 0 else -1)
    diffs = [enc(bv) - enc(av) for av, bv in zip(a, b)]
    n = len(diffs)
    mean_d = sum(diffs) / n
    std_d = math.sqrt(sum((x - mean_d) ** 2 for x in diffs) / (n - 1))
    t = mean_d / (std_d / math.sqrt(n)) if std_d > 0 else 0.0
    return mean_d, std_d, t


env_tmp = GameEnv(NUM_PLAYERS)
net = load_model(MODEL, env_tmp)
if net is None:
    raise RuntimeError(f"Impossible de charger {MODEL}")
net.eval()

print(f"Test D6 — rollout greedy en feuille")
print(f"Modèle : {MODEL}  |  sims={NUM_SIMS}  |  N={N_GAMES} paires appariées")
print(f"Bras 1 : MCTSZeroValue     (value=0, baseline)")
print(f"Bras 2 : MCTSGreedyRollout (priors réseau + rollout greedy terminal)")
print()

r_policy, r_arm1, r_arm2 = [], [], []

for g in range(N_GAMES):
    seed = g * 13337 + 42
    net_starts = (g % 2 == 0)
    r_policy.append(_play_policy_only(net, NUM_PLAYERS, net_starts, seed))
    r_arm1.append(_play(net, NUM_SIMS, NUM_PLAYERS, net_starts, seed, MCTSZeroValue))
    r_arm2.append(_play(net, NUM_SIMS, NUM_PLAYERS, net_starts, seed, MCTSGreedyRollout))
    if (g + 1) % 10 == 0:
        wrp, *_ = winrate(r_policy)
        wr1, *_ = winrate(r_arm1)
        wr2, *_ = winrate(r_arm2)
        print(f"  [{g+1:3d}/{N_GAMES}]  policy={wrp:.3f}  zero={wr1:.3f}  rollout={wr2:.3f}")

wr_p, wp, lp, dp = winrate(r_policy)
wr1, w1, l1, d1 = winrate(r_arm1)
wr2, w2, l2, d2 = winrate(r_arm2)

md_21, sd_21, t_21 = paired_stats(r_arm1, r_arm2)   # rollout − zero
md_2p, sd_2p, t_2p = paired_stats(r_policy, r_arm2)  # rollout − policy
md_1p, sd_1p, t_1p = paired_stats(r_policy, r_arm1)  # zero − policy

print()
print("=" * 60)
print(f"policy_only    wr={wr_p:.3f}  [{wp}W/{lp}L/{dp}D]")
print(f"mcts zero      wr={wr1:.3f}  [{w1}W/{l1}L/{d1}D]  (MCTSZeroValue)")
print(f"mcts rollout   wr={wr2:.3f}  [{w2}W/{l2}L/{d2}D]  (MCTSGreedyRollout)")
print()
print(f"rollout − zero   : {md_21:+.4f} ± {sd_21:.4f}  t={t_21:+.2f}")
print(f"rollout − policy : {md_2p:+.4f} ± {sd_2p:.4f}  t={t_2p:+.2f}")
print(f"zero    − policy : {md_1p:+.4f} ± {sd_1p:.4f}  t={t_1p:+.2f}")
print()

if wr2 >= wr_p and t_21 > 1.0:
    print("→ MCTS + rollout greedy > policy_only : la recherche marche avec un bon signal.")
    print("   Suite : run à volume avec MCTSGreedyRollout.")
elif t_21 > 1.0:
    print("→ rollout greedy > zero mais < policy_only.")
    print("   Le signal de feuille aide la recherche mais pas assez pour battre le prior.")
else:
    print("→ VERDICT FINAL : rollout greedy n'aide pas non plus.")
    print("   Fork 2 confirmé : améliorer la policy directement (self-play vs pool,")
    print("   sans MCTS-professeur). La policy brute à ~0.42 est la base.")

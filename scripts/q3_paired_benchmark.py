"""Q3 — Benchmark apparié complet sur le meilleur checkpoint Fork 2f.

Mesure les 3 nombres demandés par l'expert :
  1. policy_only vs greedy (aparié)
  2. mcts_on (30 sims) vs greedy (aparié)
  3. diff appariée mcts_on − policy_only

Modèle : model_2_ckpt_50.pth (Fork 2f iter 50, mcts_on=0.413 non-aparié).
N=300 parties seedées.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import MCTS, DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

MODEL = "models/model_2_ckpt_50.pth"
NUM_PLAYERS = 2
N = 300
MCTS_SIMS = 30

def play_policy(net, net_starts, seed):
    env = GameEnv(NUM_PLAYERS, seed=seed)
    slot = 0 if net_starts else 1
    net.eval()
    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    _, lt, _ = net(vec)
                tgts = list(env.pending_assassin_context["targets"])
                s = int(np.argmax(lt[0].cpu().numpy()[:len(tgts)+1]))
                env.resolve_assassin_manual(tgts[s] if s < len(tgts) else None)
            else:
                env.resolve_assassin_manual(greedy_action_target(env))
        else:
            if env.current_player == slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    lm, _, _ = net(vec)
                legal = env.get_legal_actions()
                lg = lm[0].cpu().numpy()
                mask = np.full(len(lg), -1e9)
                mask[legal] = lg[legal]
                action = int(np.argmax(mask))
            else:
                action = greedy_action_main(env)
            env.step(action)
    sc = env._calcul_scores()
    if sc[slot] > sc[1-slot]: return 0
    if sc[1-slot] > sc[slot]: return 1
    return None

def play_mcts(net, mcts, net_starts, seed):
    env = GameEnv(NUM_PLAYERS, seed=seed)
    slot = 0 if net_starts else 1
    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == slot:
                probs = mcts.search(env)
                tgts = list(env.pending_assassin_context["targets"])
                s = int(np.argmax(probs))
                env.resolve_assassin_manual(tgts[s] if 0<=s<len(tgts) else None)
            else:
                env.resolve_assassin_manual(greedy_action_target(env))
        else:
            if env.current_player == slot:
                probs = mcts.search(env)
                action = int(np.argmax(probs))
            else:
                action = greedy_action_main(env)
            env.step(action)
    sc = env._calcul_scores()
    if sc[slot] > sc[1-slot]: return 0
    if sc[1-slot] > sc[slot]: return 1
    return None

def stats(results):
    w=results.count(0); l=results.count(1); d=results.count(None)
    dec=w+l; wr=w/dec if dec>0 else 0.0
    ci=1.96*math.sqrt(wr*(1-wr)/dec) if dec>1 else 0.0
    return wr, ci, w, l, d

def enc(r): return 0 if r is None else (1 if r==0 else -1)

env_tmp = GameEnv(NUM_PLAYERS)
net = load_model(MODEL, env_tmp)
net.eval()
mcts = MCTS(net, num_sims=MCTS_SIMS)

print(f"Modèle : {MODEL}  |  N={N} paires seedées  |  MCTS sims={MCTS_SIMS}")
print()

rp, rm = [], []
for g in range(N):
    seed = g*13337+42
    ns = g%2==0
    rp.append(play_policy(net, ns, seed))
    rm.append(play_mcts(net, mcts, ns, seed))
    if (g+1)%50==0:
        wrp,_,*_ = stats(rp); wrm,_,*_ = stats(rm)
        print(f"  [{g+1}/{N}]  policy={wrp:.3f}  mcts_on={wrm:.3f}")

wrp, cip, wp, lp, dp = stats(rp)
wrm, cim, wm, lm, dm = stats(rm)

diffs = [enc(rm[i])-enc(rp[i]) for i in range(N)]
mean_d = sum(diffs)/N
std_d = math.sqrt(sum((x-mean_d)**2 for x in diffs)/(N-1))
t = mean_d/(std_d/math.sqrt(N)) if std_d>0 else 0.0

print()
print("="*60)
print(f"policy_only  wr={wrp:.3f} ±{cip:.3f}  [{wp}W/{lp}L/{dp}D]")
print(f"mcts_on      wr={wrm:.3f} ±{cim:.3f}  [{wm}W/{lm}L/{dm}D]")
print()
print(f"Diff appariée mcts_on−policy : {mean_d:+.4f} ±{std_d:.4f}  t={t:+.2f}")
print()
if wrm > wrp and t > 1.65:
    print("→ MCTS aide significativement (t>1.65, wr_mcts > wr_policy)")
elif wrm > wrp:
    print("→ MCTS positif mais non significatif")
elif wrp > 0.396 and cip < 0.06:
    print("→ Fork 2f améliore le baseline 0.396 (policy seule)")
else:
    print("→ Pas d'amélioration significative vs baseline 0.396")

"""Confirmation awr25 vs v8_250 — 300 parties appariées."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main

N = 300
def play_h2h(na, nb, a_starts, seed):
    env = GameEnv(2, seed=seed)
    nets = [na, nb] if a_starts else [nb, na]
    a_slot = 0 if a_starts else 1
    while not env.is_done():
        net = nets[env.current_player]
        if env.pending_assassin_context is not None:
            vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                _, lt, _ = net(vec)
            tgts = list(env.pending_assassin_context["targets"])
            s = int(np.argmax(lt[0].cpu().numpy()[:len(tgts)+1]))
            env.resolve_assassin_manual(tgts[s] if s<len(tgts) else None)
        else:
            vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                lm, _, _ = net(vec)
            legal = env.get_legal_actions()
            lg = lm[0].cpu().numpy(); mask=np.full(len(lg),-1e9); mask[legal]=lg[legal]
            env.step(int(np.argmax(mask)))
    sc = env._calcul_scores()
    if sc[a_slot] > sc[1-a_slot]: return 0
    if sc[1-a_slot] > sc[a_slot]: return 1
    return None

env_tmp = GameEnv(2)
awr25 = load_model("models/model_2_ckpt_25.pth", env_tmp)
v8_250 = load_model("models/model_2_ckpt_250.pth", env_tmp)

wa = wb = d = 0
for g in range(N):
    r = play_h2h(awr25, v8_250, g%2==0, g*13337+42)
    if r is None: d+=1
    elif r==0: wa+=1
    else: wb+=1
    if (g+1)%50==0: print(f"  [{g+1}/{N}]  awr25={wa} v8_250={wb} nuls={d}")

dec = wa+wb
wr = wa/dec if dec>0 else 0.5
ci = 1.96*math.sqrt(wr*(1-wr)/dec) if dec>1 else 0.0
t = (wr-0.5)/math.sqrt(wr*(1-wr)/dec) if dec>1 else 0.0
print(f"\nawr25 vs v8_250 ({N} parties): {wa}W/{wb}L/{d}D  wr={wr:.3f} ±{ci:.3f}  t={t:+.2f}")
if t > 1.65: print("→ awr25 > v8_250 CONFIRMÉ (nouveau champion)")
elif t > 0.5: print("→ tendance positive, n insuffisant")
else: print("→ pas de différence significative")

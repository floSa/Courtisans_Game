"""Table croisée checkpoints AWR + v8_250 — trouve le meilleur, vérifie transitif."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

N_PER_MATCH = 80

CKPTS = [
    ("awr25",  "models/model_2_ckpt_25.pth"),
    ("awr50",  "models/model_2_ckpt_50.pth"),
    ("awr75",  "models/model_2_ckpt_75.pth"),
    ("awr100", "models/model_2_ckpt_100.pth"),
    ("awr125", "models/model_2_ckpt_125.pth"),
    ("awr150", "models/model_2_ckpt_150.pth"),
    ("v8_250", "models/model_2_ckpt_250.pth"),
]

def play_h2h(na, nb, a_starts, seed):
    env = GameEnv(2, seed=seed)
    nets = [na, nb] if a_starts else [nb, na]
    a_slot = 0 if a_starts else 1
    while not env.is_done():
        cur = env.current_player
        net = nets[cur]
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
models = [(n, load_model(p, env_tmp)) for n,p in CKPTS if os.path.exists(p)]
models = [(n,m) for n,m in models if m]
K = len(models)
print(f"Matchups: {K*(K-1)//2} × {N_PER_MATCH} parties")

wins = [[0]*K for _ in range(K)]
gp = [[0]*K for _ in range(K)]
for i in range(K):
    for j in range(i+1, K):
        na, ma = models[i]; nb, mb = models[j]
        wa=wb=d=0
        for g in range(N_PER_MATCH):
            r = play_h2h(ma, mb, g%2==0, (i*100+j*10+g)*7919+42)
            if r is None: d+=1
            elif r==0: wa+=1
            else: wb+=1
        wins[i][j]=wa; wins[j][i]=wb; gp[i][j]=gp[j][i]=N_PER_MATCH-d
        dec=wa+wb
        print(f"  {na:7s} vs {nb:7s}: {wa}W/{wb}L/{d}D  wr={wa/dec:.2f}" if dec>0 else f"  {na} vs {nb}: nuls")

print("\n=== CLASSEMENT ===")
scores=[]
for i,(ni,_) in enumerate(models):
    s=sum(wins[i][j]/gp[i][j] for j in range(K) if i!=j and gp[i][j]>0)/(K-1)
    scores.append((s,ni))
scores.sort(reverse=True)
for r,(sc,name) in enumerate(scores,1):
    print(f"  {r}. {name:7s}  score={sc:.3f}")

# Focus sur les matchups vs v8_250
print("\n=== vs v8_250 ===")
v_idx = next(i for i,(n,_) in enumerate(models) if n=="v8_250")
for i,(ni,_) in enumerate(models):
    if i==v_idx: continue
    dec=gp[i][v_idx]; w=wins[i][v_idx]
    if dec>0:
        wr=w/dec; ci=1.96*math.sqrt(wr*(1-wr)/dec)
        t=(wr-0.5)/(math.sqrt(wr*(1-wr)/dec))
        sig="✓ SIG" if abs(t)>1.65 else ""
        print(f"  {ni:7s} vs v8_250: wr={wr:.3f} ±{ci:.3f} t={t:+.2f} {sig}")

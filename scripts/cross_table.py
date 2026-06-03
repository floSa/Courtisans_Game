"""Table croisée des checkpoints Fork 2f — diagnostic cycling vs progrès transitif.

Joue chaque checkpoint contre tous les autres en policy-only apparié.
Si la matrice est triangulaire (tardifs > précoces) → progrès transitif, pas de cycling.
Si cycles → non-transitivité confirmée.

Checkpoints : Fork 2f (25,50,75,100,125,150,175,200) + champion v8_ckpt_250.
N=60 parties appariées par matchup (plus rapide).
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, load_model
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
N_PER_MATCH = 60
CKPTS = [
    ("ckpt25",  "models/model_2_ckpt_25.pth"),
    ("ckpt50",  "models/model_2_ckpt_50.pth"),
    ("ckpt75",  "models/model_2_ckpt_75.pth"),
    ("ckpt100", "models/model_2_ckpt_100.pth"),
    ("ckpt125", "models/model_2_ckpt_125.pth"),
    ("ckpt150", "models/model_2_ckpt_150.pth"),
    ("ckpt175", "models/model_2_ckpt_175.pth"),
    ("ckpt200", "models/model_2_ckpt_200.pth"),
    ("v8_250",  "models/model_2_ckpt_250.pth"),
]

def play_head2head(net_a, net_b, a_starts, seed):
    env = GameEnv(NUM_PLAYERS, seed=seed)
    nets = [net_a, net_b] if a_starts else [net_b, net_a]
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
            env.resolve_assassin_manual(tgts[s] if s < len(tgts) else None)
        else:
            vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                lm, _, _ = net(vec)
            legal = env.get_legal_actions()
            lg = lm[0].cpu().numpy()
            mask = np.full(len(lg), -1e9)
            mask[legal] = lg[legal]
            env.step(int(np.argmax(mask)))
    sc = env._calcul_scores()
    return 0 if sc[a_slot] > sc[1-a_slot] else (1 if sc[1-a_slot] > sc[a_slot] else None)

env_tmp = GameEnv(NUM_PLAYERS)
models = [(name, load_model(path, env_tmp)) for name, path in CKPTS if os.path.exists(path)]
models = [(n, m) for n, m in models if m is not None]
K = len(models)
print(f"Checkpoints chargés : {[n for n,_ in models]}")
print(f"Matchups : {K*(K-1)//2} × {N_PER_MATCH} parties")
print()

# Matrice winrate[i][j] = winrate de i contre j
wins = [[0]*K for _ in range(K)]
games_played = [[0]*K for _ in range(K)]

for i in range(K):
    for j in range(i+1, K):
        na, ma = models[i]
        nb, mb = models[j]
        wa = wb = d = 0
        for g in range(N_PER_MATCH):
            seed = (i*100+j*10+g)*7919+42
            r = play_head2head(ma, mb, g%2==0, seed)
            if r is None: d+=1
            elif r==0: wa+=1
            else: wb+=1
        wins[i][j] = wa; wins[j][i] = wb
        games_played[i][j] = games_played[j][i] = N_PER_MATCH - d
        dec = wa + wb
        print(f"  {na:8s} vs {nb:8s} : {wa}W/{wb}L/{d}D  wr_A={wa/dec:.2f}" if dec>0 else f"  {na} vs {nb} : tous nuls")

print()
print("="*70)
print("MATRICE WINRATE (ligne=joueur, colonne=adversaire)")
names = [n for n,_ in models]
header = f"{'':8s}" + "".join(f"{n:9s}" for n in names)
print(header)
for i, (ni, _) in enumerate(models):
    row = f"{ni:8s}"
    for j in range(K):
        if i==j:
            row += f"{'—':>9s}"
        else:
            dec = games_played[i][j]
            wr = wins[i][j]/dec if dec>0 else 0.5
            row += f"  {wr:.2f}   "
    print(row)

# Score total de chaque checkpoint (somme des wr contre tous les autres)
print()
print("CLASSEMENT (score = somme des winrates vs tous)")
scores = []
for i, (ni, _) in enumerate(models):
    total = sum(wins[i][j]/games_played[i][j] for j in range(K) if i!=j and games_played[i][j]>0)
    scores.append((total/(K-1), ni))
scores.sort(reverse=True)
for rank, (sc, name) in enumerate(scores, 1):
    print(f"  {rank}. {name:8s}  score={sc:.3f}")

"""Discriminateur (A) vs (B) — PIMC strategy fusion ou bruit fini ?

Teste MCTSZeroValue (value=0, PUCT pur sur prior) à sims croissants sur le champion figé.
- Si l'écart à policy_only se referme → (A) bruit fini → rollout greedy utile.
- Si l'écart persiste ou s'élargit → (B) strategy fusion → re-déterminisation par simulation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
from app.jeu import GameEnv
from app.mcts_network import DEVICE, MCTSZeroValue, load_model
from app.greedy_bot import (
    _play_greedy_game_with_cls,
    _play_greedy_game_policy_only,
)

MODEL = "models/model_2.pth"
NUM_PLAYERS = 2

# (sims, num_games)
SCHEDULE = [
    (30,   80),
    (100,  60),
    (300,  40),
    (1000, 20),
]

env_tmp = GameEnv(NUM_PLAYERS)
net = load_model(MODEL, env_tmp)
if net is None:
    raise RuntimeError(f"Impossible de charger {MODEL}")
net.eval()

# Baseline policy_only
wins = losses = draws = 0
N_POLICY = 100
for g in range(N_POLICY):
    r = _play_greedy_game_policy_only(net, NUM_PLAYERS, g % 2 == 0)
    if r is None: draws += 1
    elif r == 0:  wins += 1
    else:         losses += 1
decisive = wins + losses
policy_wr = wins / decisive if decisive > 0 else 0.0
print(f"policy_only ({N_POLICY} games)  wr={policy_wr:.3f}  [{wins}W/{losses}L/{draws}D]")
print()

for sims, n_games in SCHEDULE:
    wins = losses = draws = 0
    for g in range(n_games):
        r = _play_greedy_game_with_cls(net, sims, NUM_PLAYERS, g % 2 == 0, MCTSZeroValue)
        if r is None: draws += 1
        elif r == 0:  wins += 1
        else:         losses += 1
    decisive = wins + losses
    wr = wins / decisive if decisive > 0 else 0.0
    gap = wr - policy_wr
    print(f"value=0  {sims:5d} sims  ({n_games:3d} games)  wr={wr:.3f}  gap={gap:+.3f}  [{wins}W/{losses}L/{draws}D]")

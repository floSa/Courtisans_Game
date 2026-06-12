"""Validation structurelle + mesure de courtisans_combo (brique 2.1e).

1. Playouts aléatoires : somme nulle, payoff indicateur, taille tenseur,
   ciblages < 12 actions.
2. Traversée complète : comptage exact états/terminaux, info-sets canon,
   lossless strings ↔ tensors.
3. Chronométrage d'une itération CFR+ → ETA de l'oracle.
"""
import os
import random
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "4")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cfr.courtisans_combo as cc
from open_spiel.python.algorithms import cfr as cfr_alg

game = cc.make_game()
sys.setrecursionlimit(20000)

# 1. Playouts.
rng = random.Random(0)
kills = 0
for _ in range(2000):
    s = game.new_initial_state()
    while not s.is_terminal():
        if s.is_chance_node():
            s.apply_action(rng.choice([o for o, _ in s.chance_outcomes()]))
            continue
        p = s.current_player()
        t = s.information_state_tensor(p)
        assert len(t) == cc.TENSOR_SIZE, f"tenseur {len(t)} != {cc.TENSOR_SIZE}"
        legal = s.legal_actions()
        assert legal and max(legal) < 12, legal
        if s._phase == "target":
            kills += 1
        s.apply_action(rng.choice(legal))
    r = s.returns()
    assert r[0] + r[1] == 0.0 and r[0] in (-1.0, 0.0, 1.0), r
print(f"2000 playouts : OK ({kills} résolutions d'assassin rencontrées)", flush=True)

# 2. Traversée complète (compte + info-sets + lossless), canon actif.
counts = {"nodes": 0, "terminals": 0}
infosets = {0: set(), 1: set()}
tensors = set()
pairs = set()


def walk(s):
    counts["nodes"] += 1
    if s.is_terminal():
        counts["terminals"] += 1
        return
    if s.is_chance_node():
        for a, _ in s.chance_outcomes():
            walk(s.child(a))
        return
    p = s.current_player()
    st = s.information_state_string(p)
    tn = tuple(s.information_state_tensor(p))
    infosets[p].add(st)
    tensors.add(tn)
    pairs.add((st, tn))
    for a in s.legal_actions():
        walk(s.child(a))


t0 = time.time()
walk(game.new_initial_state())
t_walk = time.time() - t0
n_str = len(infosets[0]) + len(infosets[1])
ok = n_str == len(tensors) == len(pairs)
print(f"États : {counts['nodes']} | terminaux : {counts['terminals']} | "
      f"info-sets canon P0={len(infosets[0])} P1={len(infosets[1])} "
      f"(traversée {t_walk:.0f}s)", flush=True)
print(f"lossless : strings={n_str} tensors={len(tensors)} paires={len(pairs)} "
      f"→ {'OK' if ok else 'COLLISION'}", flush=True)
assert ok

# 3. Une itération CFR+ chronométrée.
solver = cfr_alg.CFRPlusSolver(game)
t0 = time.time()
solver.evaluate_and_update_policy()
dt = time.time() - t0
print(f"1 itération CFR+ : {dt:.0f}s → 50 iters ≈ {dt * 50 / 3600:.1f}h, "
      f"100 iters ≈ {dt * 100 / 3600:.1f}h (hors évals d'exploitabilité)", flush=True)

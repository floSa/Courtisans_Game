"""Validation structurelle de courtisans_redeal avant de lancer l'oracle.

1. Playouts aléatoires : somme nulle, longueur, taille tenseur, manches.
2. Comptage de l'arbre sous une donne fixée (vs calcul analytique).
3. Chronométrage d'une itération CFR+ → estimation du coût de l'oracle.

(Pas de random_sim_test pyspiel : il exige make_py_observer, non implémenté
par nos jeux Python — même limitation que le best-response C++.)
"""
import os
import random
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "4")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cfr.courtisans_redeal as cr
from open_spiel.python.algorithms import cfr as cfr_alg

game = cr.make_game()

# 2. Playouts.
rng = random.Random(0)
lengths = set()
for _ in range(2000):
    s = game.new_initial_state()
    while not s.is_terminal():
        if s.is_chance_node():
            s.apply_action(rng.choice([o for o, _ in s.chance_outcomes()]))
        else:
            p = s.current_player()
            t = s.information_state_tensor(p)
            assert len(t) == cr.TENSOR_SIZE, f"tenseur {len(t)} != {cr.TENSOR_SIZE}"
            s.apply_action(rng.choice(s.legal_actions()))
    r = s.returns()
    assert r[0] + r[1] == 0.0 and r[0] in (-1.0, 0.0, 1.0), f"returns {r}"
    lengths.add(s.move_number())
assert len(cr._DEALS) == 1680, len(cr._DEALS)
print(f"2000 playouts : OK (longueurs={sorted(lengths)}, somme nulle, payoff indicateur)")

# 3. Arbre sous une donne : 1 + 12 + 144 + 1728 = 1885 nœuds.
def count(s):
    if s.is_terminal():
        return 1
    return 1 + sum(count(s.child(a)) for a in s.legal_actions())

s0 = game.new_initial_state()
s0.apply_action(0)
n = count(s0)
assert n == 1885, n
total = 1 + 1680 * n
print(f"Sous-arbre d'une donne : {n} nœuds → arbre total = {total} états (attendu 3 166 801)")

# 4. Une itération CFR+ chronométrée.
solver = cfr_alg.CFRPlusSolver(game)
t0 = time.time()
solver.evaluate_and_update_policy()
dt = time.time() - t0
print(f"1 itération CFR+ : {dt:.1f}s → 100 iters ≈ {dt * 100 / 3600:.1f}h "
      f"(hors évals d'exploitabilité, ≈2 traversées chacune)")

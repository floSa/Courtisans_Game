"""Validation de la canonicalisation du redeal (brique 2.1d, méthode §31).

1. Arbre identique canon on/off (le quotient ne touche que les info-sets).
2. Lossless canon : #strings == #tensors == #paires sur tout l'arbre.
3. Rapporte la réduction d'info-sets (attendu ≈ ÷3! = 6).
"""
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cfr.courtisans_redeal as cr

sys.setrecursionlimit(10000)


def count(s):
    if s.is_terminal():
        return 1
    return 1 + sum(count(s.child(a)) for a in s.legal_actions())


game = cr.make_game()

# 1. Structure invariante par le toggle (sous-arbre d'une donne).
sizes = {}
for flag in (False, True):
    cr.CANON = flag
    cr._CANON_CACHE.clear()
    s = game.new_initial_state()
    s.apply_action(0)
    sizes[flag] = count(s)
assert sizes[False] == sizes[True] == 1885, sizes
print(f"Arbre invariant canon on/off : {sizes[True]} nœuds/donne — OK", flush=True)

# 2+3. Lossless + quotient (canon ON, arbre complet).
cr.CANON = True
cr._CANON_CACHE.clear()
strings = {0: set(), 1: set()}
tensors = set()
pairs = set()


def walk(s):
    if s.is_terminal():
        return
    if s.is_chance_node():
        for a, _ in s.chance_outcomes():
            walk(s.child(a))
        return
    p = s.current_player()
    st = s.information_state_string(p)
    tn = tuple(s.information_state_tensor(p))
    strings[p].add(st)
    tensors.add(tn)
    pairs.add((st, tn))
    walk_children = [s.child(a) for a in s.legal_actions()]
    for c in walk_children:
        walk(c)


walk(game.new_initial_state())
n_str = len(strings[0]) + len(strings[1])
ok = n_str == len(tensors) == len(pairs)
print(f"canon : P0={len(strings[0])} (vs 213684 non-canon, ÷{213684 / len(strings[0]):.1f}) | "
      f"P1={len(strings[1])} (vs 12400, ÷{12400 / len(strings[1]):.1f})", flush=True)
print(f"strings={n_str} tensors={len(tensors)} paires={len(pairs)} "
      f"→ {'LOSSLESS OK' if ok else 'COLLISION DÉTECTÉE'}", flush=True)
sys.exit(0 if ok else 1)

"""Vérifie l'injectivité info_state_string ↔ info_state_tensor sur redeal.

Si #strings == #tensors == #paires, l'encodage tenseur est lossless (aucune
collision : deux info-sets distincts ont des tenseurs distincts).
"""
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cfr.courtisans_redeal as cr

strings = set()
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
    strings.add(st)
    tensors.add(tn)
    pairs.add((st, tn))
    for a in s.legal_actions():
        walk(s.child(a))


game = cr.make_game()
sys.setrecursionlimit(10000)
walk(game.new_initial_state())
ok = len(strings) == len(tensors) == len(pairs)
print(f"strings={len(strings)} tensors={len(tensors)} paires={len(pairs)} "
      f"→ {'LOSSLESS OK' if ok else 'COLLISION DÉTECTÉE'}", flush=True)
sys.exit(0 if ok else 1)

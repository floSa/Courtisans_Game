"""Compte les info-sets d'un jeu par traversée (sans matérialiser les états).

Usage : COURTISANS_GAME=cfr.courtisans_redeal uv run python cfr/count_infosets.py
Alternative légère à get_all_states pour les instances trop grosses (redeal).
"""
import importlib
import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

cm = importlib.import_module(os.environ.get("COURTISANS_GAME", "cfr.courtisans_redeal"))

infosets = {0: set(), 1: set()}
counts = {"nodes": 0, "terminals": 0, "chance": 0}


def walk(s):
    counts["nodes"] += 1
    if s.is_terminal():
        counts["terminals"] += 1
        return
    if s.is_chance_node():
        counts["chance"] += 1
        for a, _ in s.chance_outcomes():
            walk(s.child(a))
        return
    p = s.current_player()
    infosets[p].add(s.information_state_string(p))
    for a in s.legal_actions():
        walk(s.child(a))


game = cm.make_game()
sys.setrecursionlimit(10000)
walk(game.new_initial_state())
print(f"États : {counts['nodes']} | terminaux : {counts['terminals']} | "
      f"chance : {counts['chance']} | info-sets P0 : {len(infosets[0])} | "
      f"P1 : {len(infosets[1])}", flush=True)

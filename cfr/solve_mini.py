"""Résout Courtisans-mini (oracle) avec CFR+ et rapporte exploitabilité + structure.

Usage : uv run python cfr/solve_mini.py [iters]
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_spiel.python.algorithms import cfr, exploitability, get_all_states

# Jeu à résoudre (défaut : le mini). Ex : COURTISANS_GAME=cfr.courtisans_assassin
cm = importlib.import_module(os.environ.get("COURTISANS_GAME", "cfr.courtisans_mini"))

ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 600


def main():
    game = cm.make_game()

    # Structure du jeu : états et info-sets par joueur. Désactivable pour les
    # instances trop grosses pour matérialiser tous les états en RAM
    # (COURTISANS_SKIP_STATS=1, ex. redeal ≈ 3.2M états).
    if os.environ.get("COURTISANS_SKIP_STATS", "0") != "1":
        allst = get_all_states.get_all_states(game, include_terminals=True, include_chance_states=True)
        infosets = {0: set(), 1: set()}
        n_term = 0
        for s in allst.values():
            if s.is_terminal():
                n_term += 1
            elif not s.is_chance_node():
                p = s.current_player()
                infosets[p].add(s.information_state_string(p))
        print(f"États : {len(allst)} | terminaux : {n_term} | "
              f"info-sets P0 : {len(infosets[0])} | P1 : {len(infosets[1])}", flush=True)

    solver = cfr.CFRPlusSolver(game)
    for i in range(1, ITERS + 1):
        solver.evaluate_and_update_policy()
        if i in (1, 5, 10, 25, 50, 100, 300, ITERS):
            nc = exploitability.nash_conv(game, solver.average_policy(), use_cpp_br=False)
            print(f"CFR+ iter {i:4d} : NashConv={nc:.6f}  exploitabilité={nc/2:.6f}", flush=True)

    # Non-trivialité : la stratégie d'équilibre de P0 à la racine est-elle mixte ?
    avg = solver.average_policy()
    st = game.new_initial_state()
    st.apply_action(0)  # une donne fixée pour P0
    info = st.information_state_string(0)
    probs = dict(avg.action_probabilities(st))
    mixed = sum(1 for v in probs.values() if v > 1e-3)
    print(f"\nÉquilibre P0 sur une donne ({info.split('|board')[0]}):")
    print(f"  {mixed} actions jouées avec proba >0 (stratégie {'MIXTE' if mixed > 1 else 'pure'})")
    for a, p in sorted(probs.items(), key=lambda x: -x[1])[:4]:
        print(f"    action {a:2d} ({st.action_to_string(0, a)}) : {p:.3f}")


if __name__ == "__main__":
    main()

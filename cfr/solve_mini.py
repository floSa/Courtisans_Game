"""Résout Courtisans-mini (oracle) avec CFR+ et rapporte exploitabilité + structure.

Usage : uv run python cfr/solve_mini.py [iters]
"""
import importlib
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from open_spiel.python.algorithms import cfr, exploitability, get_all_states

# Jeu à résoudre (défaut : le mini). Ex : COURTISANS_GAME=cfr.courtisans_assassin
cm = importlib.import_module(os.environ.get("COURTISANS_GAME", "cfr.courtisans_mini"))

ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 600
# Checkpoint de reprise (COURTISANS_CKPT=chemin.pkl) : sauvegarde des regrets /
# politiques cumulés toutes les 3 itérations, reprise automatique après un kill.
# Indispensable sur les grosses instances (combo ≈ 7,4 min/iter) dans un
# environnement où les processus longs peuvent être tués.
CKPT = os.environ.get("COURTISANS_CKPT")
EVAL_ITERS = (1, 5, 10, 25, 50, 100, 300)


def _save_ckpt(solver, iteration):
    tmp = CKPT + ".tmp"
    nodes = {k: (dict(n.cumulative_regret), dict(n.cumulative_policy))
             for k, n in solver._info_state_nodes.items()}
    with open(tmp, "wb") as f:
        pickle.dump({"iteration": iteration, "nodes": nodes}, f, protocol=4)
    os.replace(tmp, CKPT)


def _load_ckpt(solver):
    with open(CKPT, "rb") as f:
        saved = pickle.load(f)
    nodes = solver._info_state_nodes
    for k, (cr, cp) in saved["nodes"].items():
        n = nodes[k]
        n.cumulative_regret.update(cr)
        n.cumulative_policy.update(cp)
    solver._iteration = saved["iteration"]
    return saved["iteration"]


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
    start = 0
    if CKPT and os.path.exists(CKPT):
        start = _load_ckpt(solver)
        print(f"Reprise du checkpoint à l'itération {start}", flush=True)
    for i in range(start + 1, ITERS + 1):
        solver.evaluate_and_update_policy()
        if CKPT and (i % 3 == 0 or i in EVAL_ITERS or i == ITERS):
            _save_ckpt(solver, i)
        if i in EVAL_ITERS or i == ITERS:
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

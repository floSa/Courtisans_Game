"""Deep CFR (PyTorch, OpenSpiel) sur Courtisans-mini — test de pipeline neuronal.

But (roadmap brique 1) : vérifier que Deep CFR converge vers l'exploitabilité
tabulaire (~0) de l'oracle CFR+ AVANT de scaler. On compare la courbe
d'exploitabilité Deep CFR à celle de CFR+ sur la même mini-instance.

Pièges environnement gérés ici (cf. doc de passation) :
  - os.environ pour le threading (NE PAS préfixer la commande par OMP_NUM_THREADS=).
  - exploitabilité via nash_conv(..., use_cpp_br=False) (jeu Python, pas de C++ BR).
  - policy Deep CFR renormalisée sur les actions légales (le réseau sort
    num_distinct_actions=20 logits, seules 12 sont légales aux nœuds de décision).

Usage : uv run python cfr/deep_cfr_mini.py [num_iterations]
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "4")

import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

import numpy as np
import torch

# Jeu (défaut : le mini). Ex : DCFR_GAME=cfr.courtisans_assassin
cm = importlib.import_module(os.environ.get("DCFR_GAME", "cfr.courtisans_mini"))
from open_spiel.python import policy as policy_lib
from open_spiel.python.algorithms import cfr, exploitability
from open_spiel.python.pytorch import deep_cfr

SEED = int(os.environ.get("DCFR_SEED", "42"))
NUM_ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("DCFR_ITERS", "160"))
TRAVERSALS = int(os.environ.get("DCFR_TRAVERSALS", "100"))
ADV_STEPS = int(os.environ.get("DCFR_ADV_STEPS", "300"))
POL_STEPS = int(os.environ.get("DCFR_POL_STEPS", "1000"))
LR = float(os.environ.get("DCFR_LR", "1e-3"))
MEASURE_NET = os.environ.get("DCFR_MEASURE_NET", "0") == "1"  # mesurer aussi la tête policy
ADV_NET = tuple(int(x) for x in os.environ.get("DCFR_ADV_NET", "64,64").split(","))
POL_NET = tuple(int(x) for x in os.environ.get("DCFR_POL_NET", "64,64").split(","))
MEM = int(float(os.environ.get("DCFR_MEM", "1e6")))  # capacité des reservoir buffers
CHECKPOINTS = [c for c in (2, 5, 10, 20, 40, 80, 160, 320, 640) if c <= NUM_ITERS]
if NUM_ITERS not in CHECKPOINTS:
    CHECKPOINTS.append(NUM_ITERS)


def normalized_policy_fn(solver):
    """Wrappe solver.action_probabilities en distribution valide sur actions légales."""

    def fn(state):
        d = solver.action_probabilities(state)
        legal = state.legal_actions()
        tot = sum(d.get(a, 0.0) for a in legal)
        if tot <= 1e-12:
            return {a: 1.0 / len(legal) for a in legal}
        return {a: d.get(a, 0.0) / tot for a in legal}

    return fn


def buffer_exact_fn(solver):
    """Policy moyenne MCCFR *exacte*, reconstruite depuis le strategy buffer.

    Moyenne pondérée-par-itération (linear CFR) des stratégies de regret-matching
    stockées, par info-set (encodage lossless → 1 tensor = 1 info-set). C'est la
    métrique de VALIDATION : elle isole la convergence du process MCCFR de l'erreur
    de régression de la tête policy, et doit converger vers l'oracle.
    """
    buf = solver._strategy_memories
    n = len(buf)
    info = buf.experience.info_state[:n]
    iters = buf.experience.iteration[:n].reshape(-1).astype(float)
    probs = buf.experience.strategy_action_probs[:n]
    num = defaultdict(lambda: np.zeros(probs.shape[1]))
    den = defaultdict(float)
    for i in range(n):
        key = tuple(np.round(info[i], 3))
        num[key] += iters[i] * probs[i]
        den[key] += iters[i]
    avg = {k: num[k] / den[k] for k in num}

    def fn(state):
        key = tuple(np.round(np.array(state.information_state_tensor(), dtype=np.float32), 3))
        legal = state.legal_actions()
        if key not in avg:
            return {a: 1.0 / len(legal) for a in legal}
        v = avg[key]
        tot = sum(v[a] for a in legal)
        if tot <= 1e-12:
            return {a: 1.0 / len(legal) for a in legal}
        return {a: v[a] / tot for a in legal}

    return fn, len(avg)


def buffer_exploitability(solver, game):
    """Exploitabilité de la policy MCCFR exacte (buffer) — métrique de validation."""
    fn, cov = buffer_exact_fn(solver)
    pol = policy_lib.tabular_policy_from_callable(game, fn)
    return exploitability.nash_conv(game, pol, use_cpp_br=False), cov


def net_exploitability(solver, game):
    """Exploitabilité de la tête policy (réseau) — métrique déployable, optionnelle."""
    solver._learn_strategy_network()
    pol = policy_lib.tabular_policy_from_callable(game, normalized_policy_fn(solver))
    nc = exploitability.nash_conv(game, pol, use_cpp_br=False)
    solver._reinitialize_policy_network()
    return nc


def run_cfr_plus(game, iters):
    """Courbe de référence CFR+ tabulaire (oracle)."""
    solver = cfr.CFRPlusSolver(game)
    curve = {}
    targets = set(CHECKPOINTS) | {iters}
    for i in range(1, iters + 1):
        solver.evaluate_and_update_policy()
        if i in targets:
            nc = exploitability.nash_conv(game, solver.average_policy(), use_cpp_br=False)
            curve[i] = nc
    return curve


def run_deep_cfr(game):
    """Pilote la boucle Deep CFR (réplique solve()) et mesure aux checkpoints."""
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    solver = deep_cfr.DeepCFRSolver(
        game,
        policy_network_layers=POL_NET,
        advantage_network_layers=ADV_NET,
        num_iterations=NUM_ITERS,        # informatif ; on pilote la boucle nous-mêmes
        num_traversals=TRAVERSALS,
        learning_rate=LR,
        batch_size_advantage=512,
        batch_size_strategy=512,
        policy_network_train_steps=POL_STEPS,
        advantage_network_train_steps=ADV_STEPS,
        memory_capacity=MEM,
        reinitialize_advantage_networks=True,
        device="cpu",
        seed=SEED,
    )
    curve = {}
    ckpt = set(CHECKPOINTS)
    for it in range(1, NUM_ITERS + 1):
        for p in range(solver._num_players):
            for _ in range(solver._num_traversals):
                solver._traverse_game_tree(solver._root_node, p)
            if solver._reinitialize_advantage_networks:
                solver._reinitialize_advantage_network(p)
            solver._learn_advantage_network(p)
        solver._iteration += 1
        if it in ckpt:
            nc, cov = buffer_exploitability(solver, game)
            curve[it] = nc
            extra = ""
            if MEASURE_NET:
                extra = f"  | net={net_exploitability(solver, game) / 2:.6f}"
            stream = int(solver._strategy_memories.add_calls)
            kept = len(solver._strategy_memories)
            print(f"  Deep CFR iter {it:4d} : NashConv={nc:.6f}  exploitabilité={nc / 2:.6f}"
                  f"  (buffer cov {cov} info-sets, {kept}/{stream} échantillons gardés)"
                  f"{extra}", flush=True)
    return curve


def main():
    game = cm.make_game()
    cfr_curve = {}
    if os.environ.get("DCFR_SKIP_CFR", "0") != "1":
        print(f"=== Oracle CFR+ (référence) — {NUM_ITERS} iters ===", flush=True)
        cfr_curve = run_cfr_plus(game, NUM_ITERS)
        for i in sorted(cfr_curve):
            print(f"  CFR+     iter {i:4d} : NashConv={cfr_curve[i]:.6f}  "
                  f"exploitabilité={cfr_curve[i] / 2:.6f}", flush=True)

    print(f"\n=== Deep CFR (PyTorch) — {NUM_ITERS} iters | traversals={TRAVERSALS} "
          f"adv_net={ADV_NET} pol_net={POL_NET} adv_steps={ADV_STEPS} pol_steps={POL_STEPS} "
          f"lr={LR} seed={SEED} ===", flush=True)
    dcfr_curve = run_deep_cfr(game)

    print("\n=== Comparatif exploitabilité (NashConv/2) — Deep CFR = policy MCCFR exacte ===",
          flush=True)
    print(f"{'iter':>6} | {'CFR+':>12} | {'Deep CFR':>12}")
    for i in sorted(set(cfr_curve) | set(dcfr_curve)):
        c = f"{cfr_curve[i] / 2:.6f}" if i in cfr_curve else "-"
        d = f"{dcfr_curve[i] / 2:.6f}" if i in dcfr_curve else "-"
        print(f"{i:>6} | {c:>12} | {d:>12}")

    final = dcfr_curve[max(dcfr_curve)] / 2
    if cfr_curve:
        print(f"\nOracle (CFR+ final)   exploitabilité = {cfr_curve[max(cfr_curve)] / 2:.6f}")
    print(f"Deep CFR final        exploitabilité = {final:.6f}  (policy MCCFR exacte)")
    verdict = "CONVERGE (→ oracle)" if final < 0.02 else "NE CONVERGE PAS encore — voir hyperparams"
    print(f"Verdict : {verdict}")


if __name__ == "__main__":
    main()

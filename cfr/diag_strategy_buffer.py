"""Diagnostic : exploitabilité de la policy moyenne MCCFR *exacte* (buffer brut).

Pourquoi : les runs Deep CFR plafonnent ~0.08 dès l'iter 20, insensible aux
traversals → ce n'est pas la variance. On isole ici la cause :
  - On extrait le strategy buffer (échantillons (info_state, iter, probs)).
  - On reconstruit la moyenne pondérée-par-itération PAR info-set (encodage
    lossless → 1 tensor = 1 info-set), SANS le réseau de policy.
  - Son exploitabilité = qualité du process MCCFR+advantage-net seul.
Si elle est ~0 → le plancher venait du réseau de policy (régression).
Si elle reste ~0.08 → le plancher est dans les regrets (advantage net) /
l'échantillonnage, pas dans la tête policy.

Usage : uv run python cfr/diag_strategy_buffer.py [iters] [traversals]
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "4")
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch

import cfr.courtisans_mini as cm
from open_spiel.python import policy as policy_lib
from open_spiel.python.algorithms import exploitability
from open_spiel.python.pytorch import deep_cfr

SEED = 42
ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 80
TRAV = int(sys.argv[2]) if len(sys.argv) > 2 else 500


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    game = cm.CourtisansMiniGame()
    solver = deep_cfr.DeepCFRSolver(
        game,
        policy_network_layers=(64, 64),
        advantage_network_layers=(64, 64),
        num_iterations=ITERS,
        num_traversals=TRAV,
        learning_rate=1e-3,
        batch_size_advantage=512,
        advantage_network_train_steps=500,
        memory_capacity=int(2e6),
        reinitialize_advantage_networks=True,
        device="cpu",
        seed=SEED,
    )
    for _ in range(ITERS):
        for p in range(solver._num_players):
            for _ in range(solver._num_traversals):
                solver._traverse_game_tree(solver._root_node, p)
            if solver._reinitialize_advantage_networks:
                solver._reinitialize_advantage_network(p)
            solver._learn_advantage_network(p)
        solver._iteration += 1

    # --- moyenne pondérée-par-itération exacte, par info-set (tensor lossless) ---
    buf = solver._strategy_memories
    n = len(buf)
    info = buf.experience.info_state[:n]
    iters = buf.experience.iteration[:n].reshape(-1).astype(float)
    probs = buf.experience.strategy_action_probs[:n]
    print(f"strategy buffer : {n} échantillons")

    num = defaultdict(lambda: np.zeros(probs.shape[1]))
    den = defaultdict(float)
    for i in range(n):
        key = tuple(np.round(info[i], 3))
        w = iters[i]                       # poids = itération (linear CFR)
        num[key] += w * probs[i]
        den[key] += w
    avg = {k: num[k] / den[k] for k in num}
    print(f"info-sets couverts par le buffer : {len(avg)} (attendu 236)")

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

    pol = policy_lib.tabular_policy_from_callable(game, fn)
    nc = exploitability.nash_conv(game, pol, use_cpp_br=False)
    print(f"\nPolicy moyenne MCCFR EXACTE (buffer, sans réseau policy) :")
    print(f"  NashConv={nc:.6f}  exploitabilité={nc / 2:.6f}")
    print("→ si ~0 : le plancher venait du RÉSEAU DE POLICY (régression).")
    print("→ si ~0.08 : le plancher est dans les REGRETS (advantage net) / échantillonnage.")


if __name__ == "__main__":
    main()

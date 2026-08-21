"""La MSE du critique de `final.pt`, mesuree par moi, nœud par nœud et par profondeur,
confrontee au PLANCHER `E[Var(R | etat complet)]` mesure par `critique.py`.
"""
from __future__ import annotations
import random, statistics, sys
import torch
from agents.politique_reseau import charger
from audit.phase3.critique import DEPART, collecter
from courtisans.infoset import tenseur

if __name__ == "__main__":
    modele = charger("models/phase3/final.pt", 205, 24)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    noeuds = collecter(modele, range(DEPART, DEPART + n))
    obs = torch.tensor([tenseur(e, j) for _, j, e, _ in noeuds], dtype=torch.float32)
    with torch.no_grad():
        _, valeurs = modele(obs)
    valeurs = valeurs.tolist()
    retours = [r for _, _, _, r in noeuds]
    profs = [p for p, _, _, _ in noeuds]

    mse = statistics.fmean((v - r) ** 2 for v, r in zip(valeurs, retours))
    var = statistics.pvariance(retours)
    print(f"depart de donne          : {DEPART}")
    print(f"nœuds                    : {len(noeuds)}  ({n} parties de self-play a 3 copies)")
    print(f"variance des retours     : {var:.4f}")
    print(f"MSE du critique final.pt : {mse:.4f}")
    print(f"R2 = 1 - MSE/Var         : {1 - mse/var:+.4f}")
    print(f"predictions du critique  : moyenne {statistics.fmean(valeurs):+.4f}, "
          f"ecart-type {statistics.pstdev(valeurs):.4f}, "
          f"min {min(valeurs):+.3f}, max {max(valeurs):+.3f}")
    print("\npar profondeur : MSE du critique, variance des retours, et ecart-type des predictions")
    groupes: dict[int, list[tuple[float, float]]] = {}
    for p, v, r in zip(profs, valeurs, retours):
        groupes.setdefault(p, []).append((v, r))
    for p in sorted(groupes):
        g = groupes[p]
        m = statistics.fmean((v - r) ** 2 for v, r in g)
        vr = statistics.pvariance([r for _, r in g])
        sd = statistics.pstdev([v for v, _ in g])
        print(f"  prof {p:2d} : MSE {m:.4f}   Var(R) {vr:.4f}   sd(V) {sd:.4f}   n={len(g)}")

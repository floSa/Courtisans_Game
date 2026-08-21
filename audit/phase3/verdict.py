"""Le verdict, recalcule par ma boucle. Usage : python -m audit.phase3.verdict <n_donnes> <depart>"""
from __future__ import annotations
import statistics, sys, time
from audit.phase3.ma_boucle import (aleatoire, bootstrap_par_donne, campagne, greedy,
                                    reseau, rho_intra_donne)

def resume(nom, res, tirages=10000, graine=12345):
    gains, parts, pd = res["gains"], res["parts"], res["par_donne"]
    moy = statistics.fmean(gains)
    bas, haut = bootstrap_par_donne(pd, tirages, graine, 0.99)
    rho = rho_intra_donne(pd)
    print(f"{nom}")
    print(f"  parties          : {len(gains)}  ({len(pd)} donnes x 3)")
    print(f"  gain moyen       : {moy:+.4f}")
    print(f"  IC 99 % / donne  : [{bas:+.4f} ; {haut:+.4f}]   demi-largeur {(haut-bas)/2:.4f}")
    print(f"  part fractionnee : {100*statistics.fmean(parts):.2f} %")
    print(f"  sigma(gain)      : {statistics.stdev(gains):.4f}")
    print(f"  rho intra-donne  : {rho:+.4f}   effet de plan 1+2rho = {1+2*rho:.4f}")
    print(f"  gain par siege   : " + "  ".join(
        f"s{s}={statistics.fmean(t[s] for t in pd):+.4f}" for s in range(3)))
    return moy, bas, haut

if __name__ == "__main__":
    n = int(sys.argv[1]); depart = int(sys.argv[2]); quoi = sys.argv[3] if len(sys.argv) > 3 else "tout"
    donnes = range(depart, depart + n)
    if quoi in ("tout", "agent"):
        t = time.time(); r = campagne(reseau(), greedy, donnes)
        resume("AGENT (echantillonne) contre 2 GREEDYS, sieges permutes", r); print(f"  [{time.time()-t:.0f} s]")
    if quoi in ("tout", "nul"):
        t = time.time(); r = campagne(greedy, greedy, donnes)
        resume("HYPOTHESE NULLE : GREEDY a la place de l'agent, contre 2 GREEDYS", r); print(f"  [{time.time()-t:.0f} s]")
    if quoi == "alea":
        t = time.time(); r = campagne(reseau(), aleatoire, donnes)
        resume("AGENT contre 2 ALEATOIRES", r); print(f"  [{time.time()-t:.0f} s]")
    if quoi == "greedyalea":
        t = time.time(); r = campagne(greedy, aleatoire, donnes)
        resume("GREEDY contre 2 ALEATOIRES", r); print(f"  [{time.time()-t:.0f} s]")

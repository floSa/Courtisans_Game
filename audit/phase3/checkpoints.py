"""Les huit checkpoints contre deux aleatoires, sur LES MEMES donnes, et les ecarts
APPARIES entre checkpoints consecutifs -- ce que le rapport ne publie pas.

Le rapport publie huit IC de Bonferroni sur les huit NIVEAUX. Il n'en publie aucun sur les
sept ECARTS. Or c'est un ecart -- le dernier -- que l'entree de journal cite pour conclure
« il progressait encore au dernier ».
"""
from __future__ import annotations
import math, random, statistics, sys
from audit.phase3.ma_boucle import aleatoire, campagne, part_fractionnee, reseau

DONNES = range(40_000, 40_000 + int(sys.argv[1] if len(sys.argv) > 1 else 600))

def mesurer(chemin: str):
    r = campagne(reseau(chemin), aleatoire, DONNES)
    # parts groupees par donne : 3 par donne, dans l'ordre des sieges
    parts = r["parts"]
    par_donne = [parts[i * 3:(i + 1) * 3] for i in range(len(parts) // 3)]
    return {
        "part": statistics.fmean(parts),
        "gain": statistics.fmean(r["gains"]),
        "par_donne": [statistics.fmean(t) for t in par_donne],
    }

def ic_apparie(a: list[float], b: list[float], graine: int, niveau=0.99, tirages=10000):
    """Bootstrap par donne de la difference APPARIEE b - a."""
    diff = [y - x for x, y in zip(a, b, strict=True)]
    alea = random.Random(graine)
    n = len(diff)
    moys = sorted(statistics.fmean(diff[alea.randrange(n)] for _ in range(n)) for _ in range(tirages))
    q = (1 - niveau) / 2
    return statistics.fmean(diff), moys[int(q * tirages)], moys[int((1 - q) * tirages) - 1]

if __name__ == "__main__":
    res = []
    for i in range(1, 9):
        m = mesurer(f"models/phase3/checkpoint_{i:02d}.pt")
        res.append(m)
        print(f"ckpt {i} : part fractionnee {100*m['part']:.2f} %   gain {m['gain']:+.4f}", flush=True)
    print("\nECARTS APPARIES entre checkpoints consecutifs (memes donnes, IC 99 % par donne) :")
    for i in range(7):
        d, bas, haut = ic_apparie(res[i]["par_donne"], res[i + 1]["par_donne"], 4242 + i)
        signe = "ETABLI" if bas > 0 else ("etabli negatif" if haut < 0 else "dans le bruit")
        print(f"  ckpt {i+1} -> {i+2} : {100*d:+.2f} pt   IC [{100*bas:+.2f} ; {100*haut:+.2f}]   {signe}")
    d, bas, haut = ic_apparie(res[0]["par_donne"], res[7]["par_donne"], 999)
    print(f"  ckpt 1 -> 8 : {100*d:+.2f} pt   IC [{100*bas:+.2f} ; {100*haut:+.2f}]   "
          + ("ETABLI" if bas > 0 else "dans le bruit"))

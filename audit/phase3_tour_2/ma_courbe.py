"""Ma reconstruction independante des ecarts apparies. Aucune fonction de mesure/ importee."""
import json, random, math
from statistics import fmean

jalons = [json.loads(x) for x in open('models/phase3/journal.jsonl') if x.strip()]
series = {j['numero']: j['parts_par_donne'] for j in jalons}
niveaux = {j['numero']: j['part_fractionnee'] for j in jalons}

# controle 0 : la serie moyenne redonne-t-elle le niveau publie ?
print("== la serie par donne redonne-t-elle le niveau publie ? ==")
for n in sorted(series):
    m = fmean(series[n])
    print(f"  ckpt {n}: serie {m:.10f}  journal {niveaux[n]:.10f}  ecart {abs(m-niveaux[n]):.2e}")

def ic_apparie(a, b, rep=20000, graine=1234, risque=0.01):
    diff = [y - x for x, y in zip(a, b)]
    n = len(diff)
    alea = random.Random(graine)
    moys = []
    for _ in range(rep):
        moys.append(math.fsum(diff[alea.randrange(n)] for _ in range(n)) / n)
    moys.sort()
    lo = moys[int(risque/2*rep)]
    hi = moys[min(rep-1, int((1-risque/2)*rep))]
    return fmean(diff), lo, hi

RISQUE = 0.01 / 8   # Bonferroni, 8 regards
for portee in (1, 2, 3):
    print(f"\n== ecarts apparies de portee {portee}, IC 99% Bonferroni/8 (mon bootstrap) ==")
    demi = []
    for k in sorted(series):
        if k - portee not in series: continue
        m, lo, hi = ic_apparie(series[k-portee], series[k], graine=7000+10*portee+k, risque=RISQUE)
        etabli = lo > 0 or hi < 0
        demi.append((hi-lo)/2)
        print(f"  {k-portee} -> {k}: {m*100:+.2f} pt  IC [{lo*100:+.2f} ; {hi*100:+.2f}]  "
              f"demi-largeur {(hi-lo)/2*100:.2f} pt  {'ETABLI' if etabli else 'dans le bruit'}")
    print(f"  demi-largeur : min {min(demi)*100:.2f}  max {max(demi)*100:.2f}  moyenne {fmean(demi)*100:.2f} pt")

m, lo, hi = ic_apparie(series[1], series[8], graine=99, risque=RISQUE)
print(f"\n== 1 -> 8 : {m*100:+.2f} pt  IC [{lo*100:+.2f} ; {hi*100:+.2f}] ==")
print(f"progres par checkpoint = ({niveaux[8]*100:.2f} - {niveaux[1]*100:.2f})/7 = {(niveaux[8]-niveaux[1])*100/7:.4f} pt")

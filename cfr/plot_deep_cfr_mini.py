"""Trace la courbe d'exploitabilité CFR+ (oracle) vs Deep CFR depuis le log.

Usage : uv run python cfr/plot_deep_cfr_mini.py [log] [out.png]
Lit cfr/deep_cfr_mini.log par défaut, écrit cfr/deep_cfr_mini.png.
"""
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOG = sys.argv[1] if len(sys.argv) > 1 else "cfr/deep_cfr_mini.log"
OUT = sys.argv[2] if len(sys.argv) > 2 else "cfr/deep_cfr_mini.png"

LINE = re.compile(r"(CFR\+|Deep CFR)\s+iter\s+(\d+)\s*:.*exploitabilité=([0-9.eE+-]+)")


def parse(path):
    cfr, dcfr = {}, {}
    with open(path) as f:
        for ln in f:
            m = LINE.search(ln)
            if not m:
                continue
            algo, it, expl = m.group(1), int(m.group(2)), float(m.group(3))
            (cfr if algo == "CFR+" else dcfr)[it] = expl
    return cfr, dcfr


def main():
    cfr, dcfr = parse(LOG)
    if not cfr and not dcfr:
        print(f"Aucune donnée trouvée dans {LOG}")
        return
    plt.figure(figsize=(7, 5))
    if cfr:
        xs = sorted(cfr)
        plt.plot(xs, [cfr[x] for x in xs], "o-", label="CFR+ (oracle tabulaire)")
    if dcfr:
        xs = sorted(dcfr)
        plt.plot(xs, [dcfr[x] for x in xs], "s-", label="Deep CFR (PyTorch)")
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("itérations")
    plt.ylabel("exploitabilité (NashConv/2)")
    plt.title("Courtisans-mini : Deep CFR vs oracle CFR+")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT, dpi=120)
    print(f"Écrit {OUT}  ({os.path.getsize(OUT)} octets)")


if __name__ == "__main__":
    main()

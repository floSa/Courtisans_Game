"""Trace plusieurs courbes Deep CFR (et CFR+ éventuel) depuis plusieurs logs.

Usage : uv run python cfr/plot_compare.py out.png label1=log1 [label2=log2 ...]
Chaque log est parsé comme dans plot_deep_cfr_mini ; la courbe CFR+ (si présente
dans un log) est tracée une seule fois en référence.
"""
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
    if len(sys.argv) < 3:
        print(__doc__)
        return
    out = sys.argv[1]
    plt.figure(figsize=(8, 5))
    cfr_done = False
    for spec in sys.argv[2:]:
        label, path = spec.split("=", 1)
        cfr, dcfr = parse(path)
        if cfr and not cfr_done:
            xs = sorted(cfr)
            plt.plot(xs, [cfr[x] for x in xs], "k--", label="CFR+ (oracle)")
            cfr_done = True
        if dcfr:
            xs = sorted(dcfr)
            plt.plot(xs, [dcfr[x] for x in xs], "o-", label=label)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("itérations")
    plt.ylabel("exploitabilité (NashConv/2)")
    plt.title("Deep CFR — comparaison de configurations")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    print(f"Écrit {out}  ({os.path.getsize(out)} octets)")


if __name__ == "__main__":
    main()

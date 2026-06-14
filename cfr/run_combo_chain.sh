#!/bin/bash
# Chaîne brique 2.1e : oracle CFR+ 50 iters puis Deep CFR canon 100 iters.
# Idempotent (saute ce qui est déjà terminé) + verrou anti-double-lancement
# + checkpoint/reprise du solveur + trace horodatée des naissances/morts.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/florian/mes_projets/Courtisant-Game || exit 1
trace() { echo "[$(date +%H:%M:%S)] $1" >> cfr/chain_trace.log; }
exec 9>/tmp/combo_chain.lock
flock -n 9 || { trace "instance dupliquée, je sors (verrou pris)"; exit 0; }
trace "chaîne démarrée (pid $$)"
trap 'trace "chaîne terminée ou tuée (code $?)"' EXIT

if ! grep -q "Équilibre" cfr/solve_combo.log 2>/dev/null; then
    trace "lancement oracle (reprise du ckpt si présent)"
    COURTISANS_GAME=cfr.courtisans_combo COURTISANS_SKIP_STATS=1 COURTISANS_CANON=1 \
        COURTISANS_CKPT=cfr/solve_combo.ckpt \
        uv run --no-sync python cfr/solve_mini.py 50 >> cfr/solve_combo.log 2>&1 || exit 1
    trace "oracle terminé"
fi

if ! grep -q "Verdict" cfr/deep_cfr_combo.log 2>/dev/null; then
    trace "lancement Deep CFR"
    DCFR_GAME=cfr.courtisans_combo COURTISANS_CANON=1 DCFR_SKIP_CFR=1 \
        DCFR_TRAVERSALS=2000 DCFR_ADV_NET=256,256 DCFR_ADV_STEPS=1500 \
        uv run --no-sync python cfr/deep_cfr_mini.py 100 > cfr/deep_cfr_combo.log 2>&1
    trace "Deep CFR terminé"
fi

#!/bin/bash
# Chaîne brique 2.1e : oracle CFR+ 50 iters puis Deep CFR canon 100 iters.
# Idempotent (saute ce qui est déjà terminé) + verrou anti-double-lancement.
# Lancé par une tâche planifiée Windows pour survivre aux cycles de la VM WSL.
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd /home/florian/mes_projets/Courtisant-Game || exit 1
exec 9>/tmp/combo_chain.lock
flock -n 9 || exit 0

if ! grep -q "Équilibre" cfr/solve_combo.log 2>/dev/null; then
    COURTISANS_GAME=cfr.courtisans_combo COURTISANS_SKIP_STATS=1 COURTISANS_CANON=1 \
        COURTISANS_CKPT=cfr/solve_combo.ckpt \
        uv run --no-sync python cfr/solve_mini.py 50 >> cfr/solve_combo.log 2>&1 || exit 1
fi

if ! grep -q "Verdict" cfr/deep_cfr_combo.log 2>/dev/null; then
    DCFR_GAME=cfr.courtisans_combo COURTISANS_CANON=1 DCFR_SKIP_CFR=1 \
        DCFR_TRAVERSALS=2000 DCFR_ADV_NET=256,256 DCFR_ADV_STEPS=1500 \
        uv run --no-sync python cfr/deep_cfr_mini.py 100 > cfr/deep_cfr_combo.log 2>&1
fi

"""Diagnostic — Behavioural Cloning du greedy (capacité de représentation).

Question : le réseau PEUT-IL représenter un jeu fort ? On génère des parties
greedy-vs-greedy, on entraîne une policy FRAÎCHE (init aléatoire) à imiter les
coups du greedy (supervisé pur, pas de RL), et on mesure si `policy_only` se
rapproche du niveau greedy.

- policy_only ≈ 0.50 en miroir vs greedy → la représentation suffit, le sol 0.00
  est un problème de SIGNAL RL → entraîner contre le greedy débloque.
- policy_only reste basse → problème de REPRÉSENTATION (state vector insuffisant)
  → corriger l'entrée avant tout ré-entraînement.

On mesure aussi l'écart de score moyen (métrique continue, lisible même près de 0).
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from app.jeu import GameEnv
from app.mcts_network import DEVICE, CourtisansNet
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
N_GEN_GAMES = 600          # parties greedy-vs-greedy pour le dataset
EPOCHS = 12
BATCH = 256
EVAL_GAMES = 100


def gen_dataset(n_games, seed0=1000):
    mainX, mainY, tgtX, tgtY = [], [], [], []
    for g in range(n_games):
        env = GameEnv(NUM_PLAYERS, seed=seed0 + g)
        while not env.is_done():
            if env.pending_assassin_context is not None:
                targets = list(env.pending_assassin_context["targets"])
                s = env.get_state_vector()
                victim = greedy_action_target(env)
                slot = targets.index(victim) if (victim in targets) else len(targets)
                tgtX.append(s); tgtY.append(slot)
                env.resolve_assassin_manual(victim)
            else:
                s = env.get_state_vector()
                a = greedy_action_main(env)
                mainX.append(s); mainY.append(a)
                env.step(a)
    return (
        np.array(mainX, dtype=np.float32), np.array(mainY, dtype=np.int64),
        np.array(tgtX, dtype=np.float32), np.array(tgtY, dtype=np.int64),
    )


def eval_vs_greedy(net, n=EVAL_GAMES, seed0=42):
    net.eval()
    w = l = d = 0
    margin_sum = 0.0
    for g in range(n):
        env = GameEnv(NUM_PLAYERS, seed=g * 13337 + seed0)
        net_slot = 0 if g % 2 == 0 else 1
        while not env.is_done():
            if env.pending_assassin_context is not None:
                if env.current_player == net_slot:
                    vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                    with torch.no_grad():
                        _, lt, _ = net(vec)
                    targets = list(env.pending_assassin_context["targets"])
                    lt = lt[0].cpu().numpy()
                    slot = int(np.argmax(lt[: len(targets) + 1]))
                    victim = targets[slot] if slot < len(targets) else None
                    env.resolve_assassin_manual(victim)
                else:
                    env.resolve_assassin_manual(greedy_action_target(env))
            else:
                if env.current_player == net_slot:
                    vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                    with torch.no_grad():
                        lm, _, _ = net(vec)
                    legal = env.get_legal_actions()
                    lm = lm[0].cpu().numpy()
                    mask = np.full(len(lm), -1e9); mask[legal] = lm[legal]
                    action = int(np.argmax(mask))
                else:
                    action = greedy_action_main(env)
                env.step(action)
        sc = env._calcul_scores()
        margin_sum += sc[net_slot] - sc[1 - net_slot]
        if sc[net_slot] > sc[1 - net_slot]: w += 1
        elif sc[1 - net_slot] > sc[net_slot]: l += 1
        else: d += 1
    dec = w + l
    wr = w / dec if dec else 0.0
    return wr, margin_sum / n, w, l, d


def main():
    from app.mcts_network import MAX_TARGETS
    env_tmp = GameEnv(NUM_PLAYERS)
    in_dim = env_tmp.get_state_vector_size()
    act_dim = env_tmp.mapper.get_action_space_size()
    n_tgt_cls = MAX_TARGETS + 1

    cache = "bc_greedy_dataset.npz"
    if os.path.exists(cache):
        d = np.load(cache)
        mX, mY, tX, tY = d["mX"], d["mY"], d["tX"], d["tY"]
        print(f"Dataset chargé du cache ({cache}) : main={len(mX)} target={len(tX)}", flush=True)
    else:
        print(f"Generation dataset ({N_GEN_GAMES} parties greedy-vs-greedy)...", flush=True)
        t0 = time.time()
        mX, mY, tX, tY = gen_dataset(N_GEN_GAMES)
        np.savez(cache, mX=mX, mY=mY, tX=tX, tY=tY)
        print(f"  main samples={len(mX)}  target samples={len(tX)}  ({time.time()-t0:.0f}s)", flush=True)

    # Filtrage des labels hors plage (états à >16 cibles → slot 'passer' déborde la tête).
    mok = (mY >= 0) & (mY < act_dim)
    tok = (tY >= 0) & (tY < n_tgt_cls)
    print(f"  labels valides : main {mok.sum()}/{len(mY)}  target {tok.sum()}/{len(tY)}", flush=True)
    mX, mY = mX[mok], mY[mok]
    tX, tY = tX[tok], tY[tok]

    net = CourtisansNet(in_dim, act_dim).to(DEVICE)  # FRAIS, init aleatoire
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)

    mX_t = torch.from_numpy(mX).to(DEVICE); mY_t = torch.from_numpy(mY).to(DEVICE)
    tX_t = torch.from_numpy(tX).to(DEVICE); tY_t = torch.from_numpy(tY).to(DEVICE)

    print("epoch  train_acc_main  policy_only_wr  avg_margin  [W/L/D]", flush=True)
    wr0, m0, *_ = eval_vs_greedy(net)
    print(f"  0(init)      -          {wr0:.3f}        {m0:+.2f}", flush=True)

    for ep in range(1, EPOCHS + 1):
        net.train()
        perm = torch.randperm(len(mX_t), device=DEVICE)
        correct = 0
        for i in range(0, len(perm), BATCH):
            idx = perm[i:i + BATCH]
            pm, _, _ = net(mX_t[idx])
            loss = F.cross_entropy(pm, mY_t[idx])
            # têtes target : un batch aléatoire à chaque step
            if len(tX_t) > BATCH:
                tidx = torch.randint(0, len(tX_t), (BATCH,), device=DEVICE)
                _, pt, _ = net(tX_t[tidx])
                loss = loss + F.cross_entropy(pt, tY_t[tidx])
            opt.zero_grad(); loss.backward(); opt.step()
            correct += (pm.argmax(1) == mY_t[idx]).sum().item()
        acc = correct / len(mX_t)
        wr, mg, w, l, d = eval_vs_greedy(net)
        print(f"  {ep:<3}    {acc:.3f}          {wr:.3f}        {mg:+.2f}    [{w}/{l}/{d}]", flush=True)


if __name__ == "__main__":
    main()

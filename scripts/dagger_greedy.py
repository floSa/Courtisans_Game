"""DAgger (Ross et al. 2011) — apprendre du greedy-oracle en corrigeant le
distribution shift que le behavioural cloning pur a révélé (cf. rapport §25).

Boucle :
  1. entraîner le réseau sur le dataset agrégé (états -> action greedy)
  2. évaluer (winrate + écart de score moyen vs greedy)
  3. le RÉSEAU joue contre le greedy (visite SES propres états) ; on étiquette
     chaque état visité par le réseau avec l'action que le GREEDY y jouerait
  4. agréger ces nouveaux états au dataset, recommencer

Le réseau apprend ainsi à récupérer de ses propres erreurs — exactement ce qui
manque au clonage pur.

Métrique de pilotage : écart de score moyen (continu, lisible même à wr=0).
"""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import torch
import torch.nn.functional as F
from app.jeu import GameEnv
from app.mcts_network import DEVICE, CourtisansNet, MAX_TARGETS
from app.greedy_bot import greedy_action_main, greedy_action_target

NUM_PLAYERS = 2
ROUNDS = 8
COLLECT_GAMES = 250        # parties net-vs-greedy par round (collecte d'états)
TRAIN_EPOCHS = 6           # epochs par round sur le dataset agrégé
BATCH = 256
EVAL_GAMES = 80
N_TGT_CLS = MAX_TARGETS + 1


def net_main_action(net, env, explore):
    vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        lm, _, _ = net(vec)
    legal = env.get_legal_actions()
    lm = lm[0].cpu().numpy()
    mask = np.full(len(lm), -1e9, dtype=np.float32); mask[legal] = lm[legal]
    if explore:
        s = mask - mask.max(); p = np.exp(s); p /= p.sum()
        return int(np.random.choice(len(p), p=p))
    return int(np.argmax(mask))


def net_target_slot(net, env, n_slots, explore):
    vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        _, lt, _ = net(vec)
    lt = lt[0].cpu().numpy()[:n_slots]
    if explore:
        s = lt - lt.max(); p = np.exp(s); p /= p.sum()
        return int(np.random.choice(len(p), p=p))
    return int(np.argmax(lt))


def collect_dagger(net, n_games, seed0):
    """Le réseau joue contre le greedy ; on étiquette ses états par l'action greedy."""
    mX, mY, tX, tY = [], [], [], []
    for g in range(n_games):
        env = GameEnv(NUM_PLAYERS, seed=seed0 + g)
        net_seat = g % 2
        while not env.is_done():
            cur = env.current_player
            net_turn = (cur % 2 == net_seat)
            if env.pending_assassin_context is not None:
                targets = list(env.pending_assassin_context["targets"])
                if net_turn:
                    # étiquette greedy sur l'état visité par le réseau
                    victim_g = greedy_action_target(env)
                    slot_g = targets.index(victim_g) if (victim_g in targets) else len(targets)
                    if 0 <= slot_g < N_TGT_CLS:
                        tX.append(env.get_state_vector()); tY.append(slot_g)
                    slot = net_target_slot(net, env, len(targets) + 1, explore=True)
                    victim = targets[slot] if slot < len(targets) else None
                else:
                    victim = greedy_action_target(env)
                env.resolve_assassin_manual(victim)
            else:
                if net_turn:
                    a_g = greedy_action_main(env)              # label expert
                    mX.append(env.get_state_vector()); mY.append(a_g)
                    a = net_main_action(net, env, explore=True)  # action réellement jouée
                else:
                    a = greedy_action_main(env)
                env.step(a)
    return (np.array(mX, np.float32), np.array(mY, np.int64),
            np.array(tX, np.float32), np.array(tY, np.int64))


def eval_vs_greedy(net, n=EVAL_GAMES, seed0=42):
    net.eval()
    w = l = d = 0; margin = 0.0
    for g in range(n):
        env = GameEnv(NUM_PLAYERS, seed=g * 13337 + seed0)
        net_seat = 0 if g % 2 == 0 else 1
        while not env.is_done():
            cur = env.current_player
            if env.pending_assassin_context is not None:
                targets = list(env.pending_assassin_context["targets"])
                if cur % 2 == net_seat:
                    slot = net_target_slot(net, env, len(targets) + 1, explore=False)
                    victim = targets[slot] if slot < len(targets) else None
                else:
                    victim = greedy_action_target(env)
                env.resolve_assassin_manual(victim)
            else:
                if cur % 2 == net_seat:
                    a = net_main_action(net, env, explore=False)
                else:
                    a = greedy_action_main(env)
                env.step(a)
        sc = env._calcul_scores()
        margin += sc[net_seat] - sc[1 - net_seat]
        if sc[net_seat] > sc[1 - net_seat]: w += 1
        elif sc[1 - net_seat] > sc[net_seat]: l += 1
        else: d += 1
    dec = w + l
    return (w / dec if dec else 0.0), margin / n, w, l, d


def train_on(net, opt, mX, mY, tX, tY, epochs):
    mXt = torch.from_numpy(mX).to(DEVICE); mYt = torch.from_numpy(mY).to(DEVICE)
    haveT = len(tX) > BATCH
    if haveT:
        tXt = torch.from_numpy(tX).to(DEVICE); tYt = torch.from_numpy(tY).to(DEVICE)
    acc = 0.0
    for _ in range(epochs):
        net.train()
        perm = torch.randperm(len(mXt), device=DEVICE); correct = 0
        for i in range(0, len(perm), BATCH):
            idx = perm[i:i + BATCH]
            pm, _, _ = net(mXt[idx])
            loss = F.cross_entropy(pm, mYt[idx])
            if haveT:
                ti = torch.randint(0, len(tXt), (BATCH,), device=DEVICE)
                _, pt, _ = net(tXt[ti]); loss = loss + F.cross_entropy(pt, tYt[ti])
            opt.zero_grad(); loss.backward(); opt.step()
            correct += (pm.argmax(1) == mYt[idx]).sum().item()
        acc = correct / len(mXt)
    return acc


def main():
    env_tmp = GameEnv(NUM_PLAYERS)
    in_dim = env_tmp.get_state_vector_size()
    act_dim = env_tmp.mapper.get_action_space_size()

    # Dataset initial = greedy-vs-greedy (réutilise le cache de la BC s'il existe).
    cache = "bc_greedy_dataset.npz"
    if os.path.exists(cache):
        d = np.load(cache)
        mX, mY = d["mX"], d["mY"]
        tok = (d["tY"] >= 0) & (d["tY"] < N_TGT_CLS)
        tX, tY = d["tX"][tok], d["tY"][tok]
        mok = (mY >= 0) & (mY < act_dim); mX, mY = mX[mok], mY[mok]
        print(f"Dataset initial (greedy-vs-greedy) : main={len(mX)} target={len(tX)}", flush=True)
    else:
        print("Pas de cache BC — lance d'abord scripts/bc_greedy.py", flush=True)
        return

    net = CourtisansNet(in_dim, act_dim).to(DEVICE)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)

    print("round  dataset_main  train_acc  policy_only_wr  avg_margin  [W/L/D]", flush=True)
    for r in range(ROUNDS):
        acc = train_on(net, opt, mX, mY, tX, tY, TRAIN_EPOCHS)
        wr, mg, w, l, dd = eval_vs_greedy(net)
        print(f"  {r:<3}   {len(mX):>7}      {acc:.3f}      {wr:.3f}        {mg:+.2f}   [{w}/{l}/{dd}]", flush=True)
        # collecte DAgger
        t0 = time.time()
        nmX, nmY, ntX, ntY = collect_dagger(net, COLLECT_GAMES, seed0=5000 + r * 1000)
        mX = np.concatenate([mX, nmX]) if len(nmX) else mX
        mY = np.concatenate([mY, nmY]) if len(nmY) else mY
        if len(ntX):
            tX = np.concatenate([tX, ntX]); tY = np.concatenate([tY, ntY])
        print(f"        (+{len(nmX)} états réseau étiquetés greedy, {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()

"""Greedy bot heuristique — baseline externe reproductible pour Courtisans.

À chaque tour, le bot simule chaque action légale et joue celle qui maximise
l'**écart** de score immédiat (son score moins le meilleur score adverse), sans
anticipation multi-tour. Il prend donc en compte l'effet de son coup sur l'adversaire
(jeu sur le domaine adverse, bascules de famille défavorables à l'autre). Ignore les
combos multi-tour et les bluffs.
"""

from __future__ import annotations

import numpy as np
import torch

from app.jeu import GameEnv
from app.mcts_network import DEVICE, MCTS, MCTSHeuristicValue, MCTSZeroValue, CourtisansNet


def _score_margin(scores: dict[int, int], cp: int) -> float:
    """Écart immédiat = score du joueur courant moins le meilleur score adverse.

    C'est le proxy myope cohérent avec la condition de victoire (le plus haut
    score gagne), contrairement au score absolu qui ignore l'effet d'un coup sur
    l'adversaire (jeu défensif/offensif sur le domaine adverse, bascules de famille).
    """
    others = [s for p, s in scores.items() if p != cp]
    return scores.get(cp, 0) - (max(others) if others else 0)


def greedy_action_main(env: GameEnv, num_worlds: int = 0) -> int:
    """Action principale qui maximise l'écart de score immédiat (cf. _score_margin).

    num_worlds=0 : évalue l'état RÉEL (`randomize=False`) — voit à travers les espions
        cachés adverses. C'est un oracle info-privilégié (greedy "qui triche").
    num_worlds>=1 : greedy ÉQUITABLE (PIMC) — moyenne l'écart sur `num_worlds`
        déterminisations échantillonnées (`randomize=True`), n'utilise donc que
        l'information légalement disponible au joueur courant.
    """
    legal = env.get_legal_actions()
    if not legal:
        return 0
    cp = env.current_player
    best_action = legal[0]
    best_margin = -float("inf")
    for action in legal:
        if num_worlds <= 0:
            sim = env.clone_determinized(randomize=False)
            sim.step(action)
            margin = _score_margin(sim._calcul_scores(), cp)
        else:
            tot = 0.0
            for _ in range(num_worlds):
                sim = env.clone_determinized(randomize=True)
                sim.step(action)
                tot += _score_margin(sim._calcul_scores(), cp)
            margin = tot / num_worlds
        if margin > best_margin:
            best_margin = margin
            best_action = action
    return best_action


def greedy_action_target(env: GameEnv, num_worlds: int = 0) -> int | None:
    """Cible d'assassinat qui maximise le score immédiat (None = passer)."""
    ctx = env.pending_assassin_context
    if not ctx:
        return None
    targets = list(ctx["targets"])
    cp = env.current_player
    best_victim: int | None = None
    best_margin = -float("inf")
    for victim in (None, *targets):
        if num_worlds <= 0:
            sim = env.clone_determinized(randomize=False)
            sim.resolve_assassin_manual(victim)
            margin = _score_margin(sim._calcul_scores(), cp)
        else:
            tot = 0.0
            for _ in range(num_worlds):
                sim = env.clone_determinized(randomize=True)
                sim.resolve_assassin_manual(victim)
                tot += _score_margin(sim._calcul_scores(), cp)
            margin = tot / num_worlds
        if margin > best_margin:
            best_margin = margin
            best_victim = victim
    return best_victim


def play_greedy_game(
    net: CourtisansNet,
    num_sims: int,
    num_players: int,
    net_starts: bool,
) -> int | None:
    """Joue une partie net vs greedy bot.

    Retourne 0 si net gagne, 1 si greedy gagne, None si égalité.
    net_starts=True → net joue joueur 0, greedy joue joueur 1.
    """
    env = GameEnv(num_players)
    mcts = MCTS(net, num_sims=num_sims)
    net_slot = 0 if net_starts else 1

    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                ctx_targets = list(env.pending_assassin_context["targets"])
                slot = int(np.argmax(probs))
                victim = ctx_targets[slot] if 0 <= slot < len(ctx_targets) else None
            else:
                victim = greedy_action_target(env)
            env.resolve_assassin_manual(victim)
        else:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                action = int(np.argmax(probs))
            else:
                action = greedy_action_main(env)
            env.step(action)

    scores = env._calcul_scores()
    net_score = scores[net_slot]
    greedy_score = scores[1 - net_slot]
    if net_score > greedy_score:
        return 0
    if greedy_score > net_score:
        return 1
    return None


def benchmark_vs_greedy(
    net: CourtisansNet,
    num_games: int = 100,
    num_sims: int = 30,
    num_players: int = 2,
) -> dict[str, int | float]:
    """Benchmark net contre le greedy bot sur num_games parties alternées.

    Retourne {"wins", "losses", "draws", "winrate"}.
    """
    net.eval()
    wins = losses = draws = 0
    for g in range(num_games):
        result = play_greedy_game(net, num_sims, num_players, net_starts=(g % 2 == 0))
        if result is None:
            draws += 1
        elif result == 0:
            wins += 1
        else:
            losses += 1
    decisive = wins + losses
    winrate = wins / decisive if decisive > 0 else 0.0
    return {"wins": wins, "losses": losses, "draws": draws, "winrate": winrate}


def _play_greedy_game_with_cls(
    net: CourtisansNet,
    num_sims: int,
    num_players: int,
    net_starts: bool,
    mcts_cls: type,
) -> int | None:
    """Variante de play_greedy_game acceptant une classe MCTS custom."""
    env = GameEnv(num_players)
    mcts = mcts_cls(net, num_sims=num_sims)
    net_slot = 0 if net_starts else 1

    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                ctx_targets = list(env.pending_assassin_context["targets"])
                slot = int(np.argmax(probs))
                victim = ctx_targets[slot] if 0 <= slot < len(ctx_targets) else None
            else:
                victim = greedy_action_target(env)
            env.resolve_assassin_manual(victim)
        else:
            if env.current_player == net_slot:
                probs = mcts.search(env)
                action = int(np.argmax(probs))
            else:
                action = greedy_action_main(env)
            env.step(action)

    scores = env._calcul_scores()
    if scores[net_slot] > scores[1 - net_slot]:
        return 0
    if scores[1 - net_slot] > scores[net_slot]:
        return 1
    return None


def _play_greedy_game_policy_only(
    net: CourtisansNet, num_players: int, net_starts: bool
) -> int | None:
    """Partie net (policy brute, 0 sim — argmax des logits) vs greedy."""
    env = GameEnv(num_players)
    net_slot = 0 if net_starts else 1
    net.eval()

    while not env.is_done():
        if env.pending_assassin_context is not None:
            if env.current_player == net_slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    _, logits_target, _ = net(vec)
                targets = list(env.pending_assassin_context["targets"])
                logits = logits_target[0].cpu().numpy()
                slot = int(np.argmax(logits[: len(targets) + 1]))
                victim = targets[slot] if slot < len(targets) else None
                env.resolve_assassin_manual(victim)
            else:
                env.resolve_assassin_manual(greedy_action_target(env))
        else:
            if env.current_player == net_slot:
                vec = torch.from_numpy(env.get_state_vector()).unsqueeze(0).to(DEVICE)
                with torch.no_grad():
                    logits_main, _, _ = net(vec)
                legal = env.get_legal_actions()
                logits = logits_main[0].cpu().numpy()
                mask = np.full(len(logits), -1e9)
                mask[legal] = logits[legal]
                action = int(np.argmax(mask))
            else:
                action = greedy_action_main(env)
            env.step(action)

    scores = env._calcul_scores()
    if scores[net_slot] > scores[1 - net_slot]:
        return 0
    if scores[1 - net_slot] > scores[net_slot]:
        return 1
    return None


def benchmark_threecurves(
    net: CourtisansNet,
    num_games: int = 100,
    num_sims: int = 30,
    num_players: int = 2,
    mcts_on_cls: type = MCTS,
) -> dict[str, dict[str, int | float]]:
    """Mesure les trois courbes diagnostiques vs greedy :

    - policy_only : argmax des logits, 0 simulation MCTS.
    - mcts_on     : MCTS avec mcts_on_cls (défaut=MCTS normal, v9=MCTSHeuristicValue).
    - mcts_off    : MCTS avec value=0 partout (PUCT pur sur prior, num_sims sims).

    Si mcts_on > mcts_off, la value (ou l'heuristique) aide. Sinon, elle nuit.
    Retourne un dict {"policy_only": {...}, "mcts_on": {...}, "mcts_off": {...}}.
    """
    net.eval()
    results: dict[str, dict[str, int | float]] = {}

    for mode in ("policy_only", "mcts_on", "mcts_off"):
        wins = losses = draws = 0
        for g in range(num_games):
            net_starts = g % 2 == 0
            if mode == "policy_only":
                r = _play_greedy_game_policy_only(net, num_players, net_starts)
            elif mode == "mcts_on":
                r = _play_greedy_game_with_cls(net, num_sims, num_players, net_starts, mcts_on_cls)
            else:  # mcts_off
                r = _play_greedy_game_with_cls(net, num_sims, num_players, net_starts, MCTSZeroValue)
            if r is None:
                draws += 1
            elif r == 0:
                wins += 1
            else:
                losses += 1
        decisive = wins + losses
        results[mode] = {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "winrate": wins / decisive if decisive > 0 else 0.0,
        }
    return results

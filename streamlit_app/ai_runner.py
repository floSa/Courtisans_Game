"""Encapsulation de l'inférence IA et de la chaîne de résolution des assassins."""

from __future__ import annotations

import random

import numpy as np

from app.jeu import GameEnv
from app.mcts_network import MCTS, CourtisansNet


def pick_ai_action(env: GameEnv, net: CourtisansNet | None, num_sims: int = 30) -> int:
    """Retourne l'index d'action que l'IA souhaite jouer."""
    if net is None:
        return random.choice(env.get_legal_actions())
    mcts = MCTS(net, num_sims=num_sims)
    probs = mcts.search(env)
    return int(np.argmax(probs))


def auto_resolve_assassins(env: GameEnv, info: dict) -> tuple[bool, dict]:
    """Tant qu'un assassin (IA) est en attente, on résout en prenant la première cible.

    Retourne (done, last_info).
    """
    done = False
    while info.get("assassin_pending"):
        ctx = env.pending_assassin_context
        victim = ctx["targets"][0] if ctx and ctx["targets"] else None
        _, _, done, info = env.resolve_assassin_manual(victim)
    return done, info

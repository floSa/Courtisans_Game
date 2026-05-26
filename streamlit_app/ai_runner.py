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
    """Résolution heuristique B1 des assassins en attente (côté IA).

    Pour le joueur humain, la résolution se fait via l'UI Streamlit
    (modal dédié) ; cette fonction n'est appelée qu'après les coups de l'IA.

    Retourne (done, last_info).
    """
    if not info.get("assassin_pending"):
        return False, info
    _, _, done, last_info = env.resolve_pending_with_heuristic()
    return done, last_info

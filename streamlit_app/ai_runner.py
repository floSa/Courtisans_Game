"""Encapsulation de l'inférence IA et de la chaîne de résolution des assassins."""

from __future__ import annotations

import random

import numpy as np

from app.greedy_bot import greedy_action_main, greedy_action_target
from app.jeu import GameEnv
from app.mcts_network import MCTS, CourtisansNet

# Types d'adversaires sélectionnables dans l'UI.
GREEDY = "greedy"
NETWORK = "network"
RANDOM = "random"


def pick_ai_action(
    env: GameEnv,
    opponent: str = GREEDY,
    net: CourtisansNet | None = None,
    num_sims: int = 30,
    num_worlds: int = 10,
) -> int:
    """Retourne l'index d'action que l'IA souhaite jouer.

    - GREEDY : greedy PIMC équitable (`num_worlds` déterminisations), le plus
      fort agent mesuré à ce jour.
    - NETWORK : MCTS guidé par le réseau AlphaZero (historique).
    - RANDOM (ou réseau absent) : action légale aléatoire.
    """
    if opponent == GREEDY:
        return greedy_action_main(env, num_worlds=num_worlds)
    if opponent == NETWORK and net is not None:
        mcts = MCTS(net, num_sims=num_sims)
        probs = mcts.search(env)
        return int(np.argmax(probs))
    return random.choice(env.get_legal_actions())


def resolve_ai_assassins(
    env: GameEnv,
    info: dict,
    opponent: str = GREEDY,
    num_worlds: int = 10,
) -> tuple[bool, dict]:
    """Résout la chaîne d'assassins en attente après un coup de l'IA.

    GREEDY cible via `greedy_action_target` (PIMC équitable) ; les autres
    adversaires retombent sur l'heuristique B1 du moteur.

    Retourne (done, last_info).
    """
    if not info.get("assassin_pending") and not env.pending_assassin_context:
        return env.is_done(), info
    if opponent == GREEDY:
        done, last_info = env.is_done(), info
        while env.pending_assassin_context:
            victim = greedy_action_target(env, num_worlds=num_worlds)
            _, _, done, last_info = env.resolve_assassin_manual(victim)
        return done, last_info
    _, _, done, last_info = env.resolve_pending_with_heuristic()
    return done, last_info

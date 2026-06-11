"""Smoke test headless du nouveau ai_runner Streamlit.

Simule des parties complètes IA-vs-IA pour chaque type d'adversaire exposé
dans l'interface (greedy PIMC, réseau absent → random, aléatoire), en passant
par pick_ai_action / resolve_ai_assassins exactement comme le fait l'app.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "4")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.jeu import GameEnv  # noqa: E402
from streamlit_app import ai_runner  # noqa: E402


def play_full_game(opponent: str, num_worlds: int, seed_games: int = 1) -> dict[int, int]:
    scores: dict[int, int] = {}
    for _ in range(seed_games):
        env = GameEnv(num_players=2)
        turns = 0
        while not env.is_done():
            if env.pending_assassin_context is not None:
                ai_runner.resolve_ai_assassins(
                    env, {"assassin_pending": True}, opponent=opponent, num_worlds=num_worlds
                )
                continue
            action = ai_runner.pick_ai_action(
                env, opponent=opponent, net=None, num_worlds=num_worlds
            )
            _, _, done, info = env.step(action)
            ai_runner.resolve_ai_assassins(env, info, opponent=opponent, num_worlds=num_worlds)
            turns += 1
            assert turns < 200, "partie anormalement longue"
        scores = env._calcul_scores()
    return scores


if __name__ == "__main__":
    for opponent, worlds in [
        (ai_runner.RANDOM, 0),
        (ai_runner.NETWORK, 0),  # net=None → fallback random, comme l'app sans modèle
        (ai_runner.GREEDY, 3),
    ]:
        scores = play_full_game(opponent, worlds)
        print(f"OK {opponent:8s} (worlds={worlds}) → scores finaux {scores}")
    print("Smoke test ai_runner : OK")

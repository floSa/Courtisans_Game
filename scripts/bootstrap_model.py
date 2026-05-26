"""Initialise un `models/model_2.pth` minimal pour permettre à Streamlit de
démarrer avec une IA fonctionnelle (mais non entraînée).

Usage :
    python scripts/bootstrap_model.py            # initial weights only
    python scripts/bootstrap_model.py --train 50 # quick 50-iter training

Le modèle initial joue au hasard (avant tout entraînement), mais il a la bonne
architecture pour être chargé par `load_model()`. Pour une vraie IA, lancer un
vrai entraînement via `python main.py train --iterations 500`.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

import torch

# Permet d'exécuter ce script depuis la racine du projet sans installer le paquet.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.jeu import GameEnv  # noqa: E402
from app.mcts_network import DEVICE, CourtisansNet, TrainConfig, train  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Bootstrap d'un modèle Courtisans.")
    p.add_argument(
        "--train",
        type=int,
        default=0,
        help="Nombre d'itérations d'entraînement (0 = juste initialiser les poids).",
    )
    p.add_argument("--num-players", type=int, default=2)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    if args.train > 0:
        train(
            config=TrainConfig(
                num_players=args.num_players,
                iterations=args.train,
                num_sims=15,
                seed=args.seed,
            )
        )
    else:
        env = GameEnv(args.num_players)
        torch.manual_seed(args.seed)
        net = CourtisansNet(
            env.get_state_vector_size(), env.mapper.get_action_space_size()
        ).to(DEVICE)
        os.makedirs("models", exist_ok=True)
        path = f"models/model_{args.num_players}.pth"
        torch.save(net.state_dict(), path)
        print(f"Poids initiaux écrits dans {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

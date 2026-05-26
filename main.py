"""Point d'entrée CLI du projet Courtisans.

Usage :
    python main.py train --iterations 200 --num-sims 30
    python main.py play --model models/model_2.pth
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.mcts_network import TrainConfig, play_vs_ai, train


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Courtisans — entraînement et jeu console.")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("train", help="Lance un self-play d'entraînement.")
    pt.add_argument("--num-players", type=int, default=2)
    pt.add_argument("--iterations", type=int, default=100)
    pt.add_argument("--num-sims", type=int, default=50)
    pt.add_argument("--lr", type=float, default=1e-3)
    pt.add_argument("--weight-decay", type=float, default=1e-4)
    pt.add_argument("--memory-size", type=int, default=50_000)
    pt.add_argument("--temperature-threshold", type=int, default=10)
    pt.add_argument(
        "--num-worlds",
        type=int,
        default=1,
        help="L2#2.1 — nb de déterminisations PIMC agrégées par appel MCTS (3-5 recommandé).",
    )
    pt.add_argument(
        "--no-family-augmentation",
        action="store_true",
        help="L2#2.2 — désactive l'augmentation par symétrie des familles.",
    )
    pt.add_argument(
        "--mcts-batch-size",
        type=int,
        default=1,
        help="L3#3.1 — taille du batch de l'évaluateur MCTS (>1 active le batché avec virtual loss).",
    )
    pt.add_argument("--seed", type=int, default=None)
    pt.add_argument("--model-dir", type=str, default="models")

    pp = sub.add_parser("play", help="Joue une partie console contre l'IA.")
    pp.add_argument("--model", type=str, default="models/model_2.pth")
    pp.add_argument("--num-sims", type=int, default=50)

    return p


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = build_parser().parse_args(argv)

    if args.command == "train":
        train(
            config=TrainConfig(
                num_players=args.num_players,
                iterations=args.iterations,
                num_sims=args.num_sims,
                lr=args.lr,
                weight_decay=args.weight_decay,
                memory_size=args.memory_size,
                temperature_threshold=args.temperature_threshold,
                num_worlds=args.num_worlds,
                family_augmentation=not args.no_family_augmentation,
                mcts_batch_size=args.mcts_batch_size,
                seed=args.seed,
                model_dir=args.model_dir,
            )
        )
        return 0
    if args.command == "play":
        play_vs_ai(model_path=args.model, num_sims=args.num_sims)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

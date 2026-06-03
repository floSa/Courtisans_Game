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
    pt.add_argument(
        "--parallel-games",
        type=int,
        default=1,
        help="Nb de parties self-play en parallèle (threads). Recommandé : 4-8 sur 9600X + 4060Ti.",
    )
    pt.add_argument(
        "--arena-games",
        type=int,
        default=200,
        help="Nb de parties d'arena. 200 → ±7%% CI (~10 min/arena). 1000 → ±3%% CI (~50 min/arena).",
    )
    pt.add_argument(
        "--arena-every",
        type=int,
        default=50,
        help="Fréquence d'évaluation arena (en itérations). 0 = désactivé.",
    )
    pt.add_argument(
        "--past-checkpoint-ratio",
        type=float,
        default=0.25,
        help="Fraction de parties self-play contre un checkpoint passé aléatoire (0.0 = désactivé).",
    )
    pt.add_argument(
        "--anchor-checkpoints",
        type=str,
        default="",
        help="Pool ancré (fictitious play) — chemins de checkpoints TOUJOURS présents "
             "comme adversaires, séparés par des virgules (ex. models/model_2_ckpt_250.pth). "
             "Ancrer le meilleur modèle connu empêche la dérive du self-play.",
    )
    pt.add_argument(
        "--anchor-ratio",
        type=float,
        default=0.5,
        help="Dans la branche adversaire-passé, fraction du temps où l'on tire une ancre "
             "plutôt qu'un checkpoint récent (défaut 0.5).",
    )
    pt.add_argument(
        "--no-progressive-sims",
        action="store_true",
        help="Désactive le schedule progressif de simulations (100→200→num_sims).",
    )
    pt.add_argument(
        "--greedy-benchmark-every",
        type=int,
        default=50,
        help="Benchmark greedy bot tous les N iters (0 = désactivé).",
    )
    pt.add_argument(
        "--greedy-benchmark-games",
        type=int,
        default=100,
        help="Nb de parties pour le benchmark greedy.",
    )
    pt.add_argument(
        "--train-steps",
        type=int,
        default=1,
        help="Nb de passes d'optimisation par itération (K>1 = plus de signal par partie).",
    )
    pt.add_argument(
        "--lr-min",
        type=float,
        default=1e-5,
        help="LR minimal pour le cosine annealing (lr décroît de --lr à --lr-min).",
    )
    pt.add_argument(
        "--held-out-ratio",
        type=float,
        default=0.0,
        help="Fraction des parties vers un buffer held-out (jamais entraîné). "
             "v_corr OOD = seul thermomètre honnête de la value. Recommandé : 0.05-0.10.",
    )
    pt.add_argument(
        "--heuristic-value",
        action="store_true",
        help="v9 — remplace la value réseau aux feuilles MCTS par tanh(margin/15).",
    )
    pt.add_argument(
        "--no-mcts",
        action="store_true",
        help="Fork 2 — self-play direct sans MCTS. Échantillonnage température depuis "
             "les logits policy. Loss = AWR si --awr-beta>0, sinon Option A max(z,0).",
    )
    pt.add_argument(
        "--awr-beta",
        type=float,
        default=0.0,
        help="Fork 2 AWR — température de pondération. 0=désactivé (Option A). "
             "Recommandé : 1.0. loss=-exp((z-z_mean)/beta)*log(pi(a)).",
    )
    pt.add_argument(
        "--awr-weight-clip",
        type=float,
        default=20.0,
        help="AWR — plafond du poids exp((z-z_mean)/beta). Évite la dominance d'un seul sample.",
    )
    pt.add_argument(
        "--entropy-coef",
        type=float,
        default=0.0,
        help="Fork 2 — coefficient du bonus d'entropie dans la loss policy. "
             "Maintient la stochasticité (évite l'exploitabilité). Recommandé : 0.01.",
    )
    pt.add_argument(
        "--policy-temperature",
        type=float,
        default=1.0,
        help="Fork 2 — température d'exploration pour l'échantillonnage policy "
             "en début de partie (avant temperature_threshold).",
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
                num_parallel_games=args.parallel_games,
                arena_games=args.arena_games,
                arena_every=args.arena_every,
                past_checkpoint_ratio=args.past_checkpoint_ratio,
                anchor_checkpoints=[
                    p.strip() for p in args.anchor_checkpoints.split(",") if p.strip()
                ],
                anchor_ratio=args.anchor_ratio,
                progressive_sims=not args.no_progressive_sims,
                greedy_benchmark_every=args.greedy_benchmark_every,
                greedy_benchmark_games=args.greedy_benchmark_games,
                train_steps_per_iter=args.train_steps,
                lr_min=args.lr_min,
                held_out_ratio=args.held_out_ratio,
                heuristic_value=args.heuristic_value,
                use_mcts=not args.no_mcts,
                entropy_coef=args.entropy_coef,
                policy_temperature=args.policy_temperature,
                awr_beta=args.awr_beta,
                awr_weight_clip=args.awr_weight_clip,
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

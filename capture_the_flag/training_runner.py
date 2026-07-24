"""Self-play training runner: run the generations loop and write checkpoints.

Runnable as a module: `python -m capture_the_flag.training_runner [options]`.
Each generation collects self-play games with the current network, trains on
them, and saves a checkpoint, carrying the improved network forward. A run lands
in its own timestamped directory under `./training-runs/` (gitignored), holding
the checkpoint series and a `run-config.json` reproducibility record.

The hyperparameter defaults are the modest starting points from `TrainingConfig`;
raise `--games` / `--iterations` / `--generations` as self-play throughput allows.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from game_engine_learning.training_loop import EpochLoss

from .engines.neural_network.ctf_checkpoint import DEFAULT_RUNS_DIR
from .engines.neural_network.ctf_training_run import TrainingConfig, train_generations

_DEFAULTS = TrainingConfig()


def _print_progress(generation: int, history: list[EpochLoss]) -> None:
    """One line per generation: the within-generation loss trend and the final
    split, so the across-generation trend can be eyeballed as the run proceeds."""
    first, last = history[0], history[-1]
    print(
        f"generation {generation:>3}: total loss {first.total:.4f} -> {last.total:.4f}"
        f"  (value {last.value:.4f}, policy {last.policy:.4f})"
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the Capture the Flag play engine by self-play.",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=_DEFAULTS.generations,
        help=f"number of self-play/train generations (default: {_DEFAULTS.generations})",
    )
    parser.add_argument(
        "-n",
        "--games",
        type=int,
        default=_DEFAULTS.games_per_generation,
        help=f"self-play games per generation (default: {_DEFAULTS.games_per_generation})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=_DEFAULTS.self_play_iterations,
        help=f"MCTS iterations per ply during self-play (default: {_DEFAULTS.self_play_iterations})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=_DEFAULTS.self_play_temperature,
        help=f"self-play ply-selection temperature (default: {_DEFAULTS.self_play_temperature})",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=_DEFAULTS.epochs_per_generation,
        help=f"training epochs over each generation's data (default: {_DEFAULTS.epochs_per_generation})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=_DEFAULTS.batch_size,
        help=f"training minibatch size (default: {_DEFAULTS.batch_size})",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=_DEFAULTS.learning_rate,
        help=f"Adam learning rate (default: {_DEFAULTS.learning_rate})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed network init and the process-global RNG for reproducibility",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=f"base directory for run directories (default: ./{DEFAULT_RUNS_DIR})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    config = TrainingConfig(
        generations=args.generations,
        games_per_generation=args.games,
        self_play_iterations=args.iterations,
        self_play_temperature=args.temperature,
        epochs_per_generation=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed,
    )
    run_dir = train_generations(config, base_dir=args.output_dir, progress=_print_progress)
    print(f"\nDone — {config.generations} generations. Checkpoints in {run_dir}")


if __name__ == "__main__":
    main()

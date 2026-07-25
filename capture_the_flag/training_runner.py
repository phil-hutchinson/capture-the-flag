"""Self-play training runner: run the generations loop and write checkpoints.

Runnable as a module: `python -m capture_the_flag.training_runner [options]`.
Each generation collects self-play games with the current network, trains on
them, and saves a checkpoint, carrying the improved network forward. A run lands
in its own timestamped directory under `./training-runs/` (gitignored), holding
the checkpoint series and a `run-config.json` reproducibility record.

The hyperparameter defaults are the modest starting points from `TrainingConfig`;
raise `--games` / `--iterations` / `--generations` as self-play throughput allows.
`--features` / `--residual-blocks` size the network itself, so — like every other
non-resumable hyperparameter — they are fixed when the run starts and a resume
rebuilds from what the run recorded.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from game_engine_learning.training_loop import EpochLoss

from .engines.neural_network.ctf_checkpoint import DEFAULT_RUNS_DIR
from .engines.neural_network.ctf_crn import (
    MAX_FEATURE_COUNT,
    MAX_RESIDUAL_BLOCK_COUNT,
)
from .engines.neural_network.ctf_training_run import (
    TrainingConfig,
    resume_generations,
    train_generations,
)
from .timing_record import TIMING_ON_BY_DEFAULT, TIMING_RECORD_FILENAME

_DEFAULTS = TrainingConfig()

# The training-shape flags — everything except --generations and --output-dir,
# which are meaningful in resume mode too. Each maps its CLI flag (for the resume
# warning) to the argparse dest and the TrainingConfig field it fills. Their
# argparse defaults are None ("unset") so an explicitly-passed value is
# distinguishable from an absent one — a fresh run falls back to the config
# defaults, and a resume warns that these are ignored.
_TRAINING_FLAGS = {
    "--games": ("games", "games_per_generation"),
    "--iterations": ("iterations", "self_play_iterations"),
    "--temperature": ("temperature", "self_play_temperature"),
    "--epochs": ("epochs", "epochs_per_generation"),
    "--batch-size": ("batch_size", "batch_size"),
    "--learning-rate": ("learning_rate", "learning_rate"),
    "--features": ("features", "feature_count"),
    "--residual-blocks": ("residual_blocks", "residual_block_count"),
    "--seed": ("seed", "seed"),
}


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
        default=None,
        help=f"self-play games per generation (default: {_DEFAULTS.games_per_generation})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help=f"MCTS iterations per ply during self-play (default: {_DEFAULTS.self_play_iterations})",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=f"self-play ply-selection temperature (default: {_DEFAULTS.self_play_temperature})",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help=f"training epochs over each generation's data (default: {_DEFAULTS.epochs_per_generation})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"training minibatch size (default: {_DEFAULTS.batch_size})",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=None,
        help=f"Adam learning rate (default: {_DEFAULTS.learning_rate})",
    )
    parser.add_argument(
        "--features",
        type=int,
        default=None,
        help=f"network trunk width, 1-{MAX_FEATURE_COUNT} (default: "
        f"{_DEFAULTS.feature_count}); fixed for the life of a run, so a resume "
        "rebuilds from the run's recorded value",
    )
    parser.add_argument(
        "--residual-blocks",
        type=int,
        default=None,
        help=f"network trunk depth, 1-{MAX_RESIDUAL_BLOCK_COUNT} (default: "
        f"{_DEFAULTS.residual_block_count}); fixed for the life of a run, like "
        "--features",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed network init, self-play placements, and the process-global RNG "
        "so a fresh run reproduces in the same environment (resumes are not reseeded)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=f"base directory for run directories (default: ./{DEFAULT_RUNS_DIR})",
    )
    parser.add_argument(
        "--timing",
        action=argparse.BooleanOptionalAction,
        default=TIMING_ON_BY_DEFAULT,
        help="measure where the run spends its time: print the breakdown and "
        f"write it, with the run's hyperparameters, to {TIMING_RECORD_FILENAME} "
        f"in the run directory (default: {'on' if TIMING_ON_BY_DEFAULT else 'off'}); "
        "a resume writes its own record and leaves the original intact",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume the most recent run under the output directory: reload its "
        "latest checkpoint and train --generations more generations into the same "
        "run, reusing that run's recorded hyperparameters (the other training "
        "options are ignored in this mode)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.resume:
        ignored = [
            flag
            for flag, (dest, _) in _TRAINING_FLAGS.items()
            if getattr(args, dest) is not None
        ]
        if ignored:
            print(
                "warning: --resume reuses the resumed run's recorded "
                f"hyperparameters; ignoring {', '.join(ignored)}",
                file=sys.stderr,
            )
        run_dir = resume_generations(
            args.generations,
            base_dir=args.output_dir,
            progress=_print_progress,
            timing=args.timing,
        )
        print(
            f"\nDone — resumed and added {args.generations} generations. "
            f"Checkpoints in {run_dir}"
        )
        return

    # Only fields explicitly passed override the config defaults; an unset flag
    # (None) leaves that field at its TrainingConfig default.
    overrides = {
        field: getattr(args, dest)
        for dest, field in _TRAINING_FLAGS.values()
        if getattr(args, dest) is not None
    }
    config = replace(_DEFAULTS, generations=args.generations, **overrides)
    run_dir = train_generations(
        config, base_dir=args.output_dir, progress=_print_progress, timing=args.timing
    )
    print(f"\nDone — {config.generations} generations. Checkpoints in {run_dir}")


if __name__ == "__main__":
    main()

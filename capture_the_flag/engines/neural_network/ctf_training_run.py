"""Multi-generation training orchestrator (story 00000009, Step 6).

Wraps the single-generation glue (`train_one_generation`, Step 4) in the
generations loop: each generation collects self-play with the *current* network,
trains on it, and saves a checkpoint (Step 5), carrying the improved network into
the next generation. One timestamped run directory holds the whole run — its
checkpoint series plus a `run-config.json` reproducibility record.

`TrainingConfig` carries the starting hyperparameters. The defaults are the
deliberately-modest starting points chosen in the story discussion (5 games and
200 search iterations per ply, self-play temperature 1.0, Adam at 1e-3, a few
epochs) — cheap enough to run on one workstation, to be raised as throughput
allows, not values tuned to demonstrated strength (that is deferred).

A fresh optimizer is built per generation, so no optimizer state crosses a
generation boundary — which is why checkpoints are weights-only (Step 5) and a
resume (Step 7) can pick up from any checkpoint without it.
"""

from __future__ import annotations

import json
import random
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from importlib import metadata
from pathlib import Path

import torch
from game_engine_learning.checkpoints import checkpoint_path, new_run_directory
from game_engine_learning.training_loop import EpochLoss
from torch.optim import Adam

from .ctf_checkpoint import DEFAULT_RUNS_DIR, save_checkpoint
from .ctf_crn import CtfCrn
from .ctf_training import train_one_generation

RUN_CONFIG_FILENAME = "run-config.json"

# Progress callback: (generation number, that generation's per-epoch loss history).
ProgressCallback = Callable[[int, list[EpochLoss]], None]


@dataclass(frozen=True)
class TrainingConfig:
    """The starting hyperparameters for a training run.

    Grouped by what they govern: the first block is self-play data production
    (the expensive half — wall-clock is dominated by
    `games_per_generation x self_play_iterations`), the second is learning over
    that data (the cheap half), and `generations` / `seed` frame the run itself.
    """

    generations: int = 10
    games_per_generation: int = 5
    self_play_iterations: int = 200
    self_play_temperature: float = 1.0
    epochs_per_generation: int = 3
    batch_size: int = 32
    learning_rate: float = 1e-3
    seed: int | None = None


def train_generations(
    config: TrainingConfig,
    base_dir: Path = DEFAULT_RUNS_DIR,
    progress: ProgressCallback | None = None,
) -> Path:
    """Run `config.generations` generations and return the run directory.

    Each generation trains `network` in place (via `train_one_generation`) and
    saves it as `checkpoint-<generation>.pt`, so the checkpoint iteration is the
    number of generations trained so far — the anchor a resume (Step 7) continues
    from. `progress`, if given, is called after each generation with that
    generation's loss history, so a caller can report the trend live.
    """
    if config.generations < 1:
        raise ValueError(f"generations must be at least 1, got {config.generations}")

    if config.seed is not None:
        # Seed torch (network init) and the process-global `random` (which
        # placement and the search draw from). Note self-play placement still
        # uses its own unseeded RNG, so a run is reproducible in configuration
        # and network init but not bit-for-bit in the games played.
        torch.manual_seed(config.seed)
        random.seed(config.seed)

    network = CtfCrn()
    run_dir = new_run_directory(base_dir)
    _write_run_config(run_dir, config)

    for generation in range(1, config.generations + 1):
        optimizer = Adam(network.parameters(), lr=config.learning_rate)
        history = train_one_generation(
            network,
            optimizer,
            n_games=config.games_per_generation,
            epochs=config.epochs_per_generation,
            batch_size=config.batch_size,
            self_play_iterations=config.self_play_iterations,
            self_play_temperature=config.self_play_temperature,
        )
        save_checkpoint(network, checkpoint_path(run_dir, generation))
        if progress is not None:
            progress(generation, history)

    return run_dir


def _write_run_config(run_dir: Path, config: TrainingConfig) -> None:
    """Write the reproducibility record: the config, the environment it ran
    against (dependency versions and this repo's commit), and the start time."""
    record = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "config": asdict(config),
        "versions": {
            "game_engine_core": _distribution_version("game-engine-core"),
            "capture_the_flag": _distribution_version("capture-the-flag"),
            "torch": torch.__version__,
        },
        "git_commit": _git_commit(),
    }
    path = run_dir / RUN_CONFIG_FILENAME
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _distribution_version(name: str) -> str | None:
    """The installed version of a distribution, or None if it is not installed
    (e.g. running from a source tree that was never `pip install`-ed)."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _git_commit() -> str | None:
    """This repo's short commit hash, or None if git is unavailable or the run is
    not inside a working tree — the record is best-effort, never fatal."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None

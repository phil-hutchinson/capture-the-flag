"""Multi-generation training orchestrator.

Wraps the single-generation glue (`train_one_generation`) in the generations
loop: each generation collects self-play with the *current* network, trains on
it, and saves a checkpoint, carrying the improved network into the next
generation. One timestamped run directory holds the whole run — its checkpoint
series plus a `run-config.json` reproducibility record.

`TrainingConfig` carries the starting hyperparameters. The defaults are
deliberately modest (5 games and 200 search iterations per ply, self-play
temperature 1.0, Adam at 1e-3, a few epochs) — cheap enough to run on one
workstation, to be raised as throughput allows, not values tuned to demonstrated
strength (that is deferred).

A fresh optimizer is built per generation, so no optimizer state crosses a
generation boundary — which is why checkpoints are weights-only and a resume can
pick up from any checkpoint without it.
"""

from __future__ import annotations

import json
import random
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from importlib import metadata
from pathlib import Path

import torch
from game_engine_learning.checkpoints import (
    checkpoint_path,
    discover_checkpoints,
    latest_run_directory,
    new_run_directory,
)
from game_engine_learning.training_loop import EpochLoss
from torch.optim import Adam

from .ctf_checkpoint import DEFAULT_RUNS_DIR, load_network, save_checkpoint
from .ctf_crn import DEFAULT_FEATURE_COUNT, DEFAULT_RESIDUAL_BLOCK_COUNT, CtfCrn
from .ctf_position_factory import CtfPositionFactory
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
    that data (the cheap half), the third is the network the run trains, and
    `generations` / `seed` frame the run itself.

    The architecture fields are what the run's network is *built* from, so like
    the rest of these they are fixed for the life of a run: a resume rebuilds
    from the recorded values rather than from whatever the current defaults are.
    """

    generations: int = 10
    games_per_generation: int = 5
    self_play_iterations: int = 200
    self_play_temperature: float = 1.0
    epochs_per_generation: int = 3
    batch_size: int = 32
    learning_rate: float = 1e-3
    feature_count: int = DEFAULT_FEATURE_COUNT
    residual_block_count: int = DEFAULT_RESIDUAL_BLOCK_COUNT
    seed: int | None = None


def train_generations(
    config: TrainingConfig,
    base_dir: Path = DEFAULT_RUNS_DIR,
    progress: ProgressCallback | None = None,
) -> Path:
    """Run `config.generations` generations and return the run directory.

    Each generation trains `network` in place (via `train_one_generation`) and
    saves it as `checkpoint-<generation>.pt`, so the checkpoint iteration is the
    number of generations trained so far — the anchor a resume continues from.
    `progress`, if given, is called after each generation with that generation's
    loss history, so a caller can report the trend live.
    """
    if config.generations < 1:
        raise ValueError(f"generations must be at least 1, got {config.generations}")

    position_factory: CtfPositionFactory | None = None
    if config.seed is not None:
        # Seed every stochastic source so the run is reproducible given the same
        # environment: torch (network init), the process-global `random` (the
        # search draws from it), and the placement factory (its own rng, seeded
        # here so the self-play games are reproducible too rather than drawn from
        # OS entropy).
        torch.manual_seed(config.seed)
        random.seed(config.seed)
        position_factory = CtfPositionFactory(random.Random(config.seed))

    network = CtfCrn(
        feature_count=config.feature_count,
        residual_block_count=config.residual_block_count,
    )
    run_dir = new_run_directory(base_dir)
    _write_run_config(run_dir, config)
    _run_generations(
        network,
        run_dir,
        config,
        start_generation=1,
        position_factory=position_factory,
        progress=progress,
    )
    return run_dir


def resume_generations(
    added_generations: int,
    base_dir: Path = DEFAULT_RUNS_DIR,
    progress: ProgressCallback | None = None,
) -> Path:
    """Resume the most recent run and train `added_generations` more generations
    into the *same* run directory, then return it.

    The network is rehydrated from the run's latest checkpoint (`load_network`),
    so training continues from the saved weights rather than a fresh init, and the
    appended checkpoints are numbered from the next generation —
    `latest_checkpoint + 1` onward. The self-play and training hyperparameters
    come from the run's own `run-config.json`, not from fresh defaults, so the
    added generations are produced the same way as the original ones; only *how
    many* more to run is chosen at resume time. That includes the architecture,
    which the run therefore records twice — in the run config and in the
    checkpoint's own stamp. The checkpoint stamp is what the network is actually
    rebuilt from (it is the one attached to the weights); the run config is
    checked against it, and a disagreement means the run directory is
    inconsistent and is refused rather than silently resolved.

    No reseeding happens here: the seed governed the original network init and
    initial run, which are already in the past by the time a resume loads the
    saved weights, so re-applying it would only reduce the diversity of the
    additional self-play games.
    """
    if added_generations < 1:
        raise ValueError(f"added_generations must be at least 1, got {added_generations}")

    run_dir = latest_run_directory(base_dir)
    if run_dir is None:
        raise FileNotFoundError(f"No training run to resume under {base_dir}")

    checkpoints = discover_checkpoints(run_dir)
    if not checkpoints:
        raise FileNotFoundError(f"No checkpoint to resume from in {run_dir}")

    latest = checkpoints[-1]
    network = load_network(latest.path)
    config = replace(_read_run_config(run_dir), generations=added_generations)
    _check_architecture_agrees(network, config, latest.path)

    _append_resume_record(
        run_dir, resumed_from=latest.iteration, added_generations=added_generations
    )
    _run_generations(
        network,
        run_dir,
        config,
        start_generation=latest.iteration + 1,
        progress=progress,
    )
    return run_dir


def _run_generations(
    network: CtfCrn,
    run_dir: Path,
    config: TrainingConfig,
    *,
    start_generation: int,
    position_factory: CtfPositionFactory | None = None,
    progress: ProgressCallback | None,
) -> None:
    """Train `config.generations` generations into `run_dir`, labelling the first
    of them `start_generation` (1 for a fresh run, `latest_checkpoint + 1` for a
    resume).

    Each generation builds a fresh optimizer, trains `network` in place, and saves
    it under the checkpoint convention — so the checkpoint iteration is the total
    number of generations trained so far, and a resume can continue from it.
    """
    for offset in range(config.generations):
        generation = start_generation + offset
        optimizer = Adam(network.parameters(), lr=config.learning_rate)
        history = train_one_generation(
            network,
            optimizer,
            n_games=config.games_per_generation,
            epochs=config.epochs_per_generation,
            batch_size=config.batch_size,
            self_play_iterations=config.self_play_iterations,
            self_play_temperature=config.self_play_temperature,
            position_factory=position_factory,
        )
        save_checkpoint(network, checkpoint_path(run_dir, generation))
        if progress is not None:
            progress(generation, history)


def _check_architecture_agrees(
    network: CtfCrn, config: TrainingConfig, checkpoint: Path
) -> None:
    """Cross-check a resumed run's two independent architecture records.

    `network` was rebuilt from the checkpoint's own stamp and `config` from the
    run's `run-config.json`; the two are written by the same run and cannot
    legitimately differ. If they do, the run directory has been edited or files
    from different runs have been mixed, and continuing would train under a
    config that does not describe the network being trained.
    """
    recorded = (config.feature_count, config.residual_block_count)
    stamped = (network.feature_count, network.residual_block_count)
    if recorded != stamped:
        raise ValueError(
            f"{RUN_CONFIG_FILENAME} records a network of {recorded[0]} features "
            f"x {recorded[1]} residual blocks, but {checkpoint} holds one of "
            f"{stamped[0]} x {stamped[1]}. The run directory is inconsistent; "
            "resume from a run whose config and checkpoints match."
        )


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


def _read_run_config(run_dir: Path) -> TrainingConfig:
    """Reconstruct the run's `TrainingConfig` from its `run-config.json`, so a
    resume reproduces the original run's self-play and training settings instead
    of falling back to fresh defaults."""
    record = json.loads((run_dir / RUN_CONFIG_FILENAME).read_text(encoding="utf-8"))
    return TrainingConfig(**record["config"])


def _append_resume_record(
    run_dir: Path, *, resumed_from: int, added_generations: int
) -> None:
    """Note this resume in the run's record. The original config is left intact
    and each resume appends an entry — when it happened, which checkpoint it
    continued from, how many generations it added, and the commit it ran against —
    so the record still reproduces the run as a whole across any number of
    resumes."""
    path = run_dir / RUN_CONFIG_FILENAME
    record = json.loads(path.read_text(encoding="utf-8"))
    record.setdefault("resumes", []).append(
        {
            "resumed": datetime.now().isoformat(timespec="seconds"),
            "resumed_from_checkpoint": resumed_from,
            "added_generations": added_generations,
            "git_commit": _git_commit(),
        }
    )
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

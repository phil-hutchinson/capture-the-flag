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
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
from game_engine_learning.checkpoints import (
    checkpoint_path,
    discover_checkpoints,
    latest_run_directory,
    new_run_directory,
)
from game_engine_learning.training_loop import EpochLoss
from torch.optim import Adam

from ...device import ResolvedDevice, pipeline_device
from ...instrumentation.timing import TimingSession, region
from ...record import (
    RulesetConfiguration,
    active_configuration,
    configuration_differences,
)
from ...run_environment import distribution_version, git_commit
from ...timing_record import (
    TIMING_ON_BY_DEFAULT,
    TIMING_RECORD_STEM,
    report_timings,
    timing_run,
)
from ...timing_regions import (
    BUILD_OPTIMIZER,
    GENERATION,
    ROOT_TRAINING,
    SAVE_CHECKPOINT,
)
from .ctf_checkpoint import (
    DEFAULT_RUNS_DIR,
    checkpoint_configuration,
    load_network,
    save_checkpoint,
)
from .ctf_crn import DEFAULT_FEATURE_COUNT, DEFAULT_RESIDUAL_BLOCK_COUNT, CtfCrn
from .ctf_position_factory import CtfPositionFactory
from .ctf_training import train_one_generation

RUN_CONFIG_FILENAME = "run-config.json"

TIMING_RESUME_STEM_TEMPLATE = "timings-resume-{index}"
"""Where a resumed run's timings land — the stem its `.json`/`.txt` pair shares.

A resume trains different generations under the same config, so its costs are a
separate measurement rather than an amendment to the first one — and the
original record must survive, since it is the baseline a later comparison uses.
The index matches the run config's own resume list, so a record and the resume
that produced it are identifiable from either side.
"""

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
    timing: bool = TIMING_ON_BY_DEFAULT,
) -> Path:
    """Run `config.generations` generations and return the run directory.

    Each generation trains `network` in place (via `train_one_generation`) and
    saves it as `checkpoint-<generation>.pt`, so the checkpoint iteration is the
    number of generations trained so far — the anchor a resume continues from.
    `progress`, if given, is called after each generation with that generation's
    loss history, so a caller can report the trend live.

    With `timing`, the run measures itself and leaves a `timings.json` beside its
    checkpoints — the breakdown together with the hyperparameters that produced
    it, so the file stands on its own when compared against a later run. It is
    rewritten with every checkpoint, so a run that never reaches its end still
    leaves the generations it finished.
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

    resolved_device = pipeline_device()

    with timing_run(ROOT_TRAINING, enabled=timing) as session:
        network = CtfCrn(
            feature_count=config.feature_count,
            residual_block_count=config.residual_block_count,
        )
        run_dir = new_run_directory(base_dir)
        _write_run_config(run_dir, config)
        settings = asdict(config)
        reported = _run_generations(
            network,
            run_dir,
            config,
            # A fresh run is by definition played under what this code currently
            # implements, and stamps its checkpoints with it; only a resume has
            # some other configuration to carry.
            configuration=active_configuration(),
            start_generation=1,
            position_factory=position_factory,
            progress=progress,
            record_timings=_timing_recorder(
                session, run_dir, settings=settings, resolved_device=resolved_device
            ),
        )

    _report_timings(
        session, run_dir, settings=settings, resolved_device=resolved_device, preamble=reported
    )
    return run_dir


def resume_generations(
    added_generations: int,
    base_dir: Path = DEFAULT_RUNS_DIR,
    progress: ProgressCallback | None = None,
    timing: bool = TIMING_ON_BY_DEFAULT,
) -> Path:
    """Resume the most recent run and train `added_generations` more generations
    into the *same* run directory, then return it.

    The network is rehydrated from the run's latest checkpoint (`load_network`),
    so training continues from the saved weights rather than a fresh init, and the
    appended checkpoints are numbered from the next generation —
    `latest_checkpoint + 1` onward. The self-play and training hyperparameters
    come from the run's own `run-config.json`, not from fresh defaults, so the
    added generations are produced the same way as the original ones; only *how
    many* more to run is chosen at resume time. That includes the architecture and
    the ruleset configuration, which the run therefore records twice — in the run
    config and in the checkpoint's own stamp. The checkpoint stamp is what the
    network is actually rebuilt from and continued under (it is the one attached
    to the weights); the run config is checked against it, and a disagreement
    means the run directory is inconsistent and is refused rather than silently
    resolved.

    The ruleset comes from the stamp rather than from current defaults for the
    same reason the architecture does: a run trained with a flag on continues with
    that flag on even if the current default is off. The adopted configuration is
    also what the appended checkpoints are stamped with, so a resume cannot
    quietly re-tag a run's later generations with an edition it was not trained
    under. What is refused is the case where the running code cannot implement the
    stamped configuration at all, which `load_network` has already rejected by the
    time the cross-check runs.

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

    resolved_device = pipeline_device()

    with timing_run(ROOT_TRAINING, enabled=timing) as session:
        latest = checkpoints[-1]
        network = load_network(latest.path)
        run_record = _read_run_record(run_dir)
        config = replace(_run_config(run_record), generations=added_generations)
        _check_architecture_agrees(network, config, latest.path)
        # Bound, not merely checked: this is the configuration the appended
        # generations are trained under and stamped with.
        configuration = checkpoint_configuration(latest.path)
        _check_ruleset_agrees(
            configuration, _run_ruleset(run_record, run_dir), latest.path
        )

        resume_index = _append_resume_record(
            run_dir, resumed_from=latest.iteration, added_generations=added_generations
        )
        settings = {**asdict(config), "resumed_from_checkpoint": latest.iteration}
        stem = TIMING_RESUME_STEM_TEMPLATE.format(index=resume_index)
        reported = _run_generations(
            network,
            run_dir,
            config,
            configuration=configuration,
            start_generation=latest.iteration + 1,
            progress=progress,
            record_timings=_timing_recorder(
                session, run_dir, settings=settings, stem=stem, resolved_device=resolved_device
            ),
        )

    _report_timings(
        session,
        run_dir,
        settings=settings,
        stem=stem,
        resolved_device=resolved_device,
        preamble=reported,
    )
    return run_dir


def format_generation_progress(generation: int, history: list[EpochLoss]) -> str:
    """One generation's loss summary: the within-generation trend and the final
    split.

    Shared so the line a run prints live and the line its timing record keeps are
    the same line — a report that disagreed with the terminal would be worse than
    one that omitted it.
    """
    first, last = history[0], history[-1]
    return (
        f"generation {generation:>3}: total loss {first.total:.4f} -> {last.total:.4f}"
        f"  (value {last.value:.4f}, policy {last.policy:.4f})"
    )


def _run_generations(
    network: CtfCrn,
    run_dir: Path,
    config: TrainingConfig,
    *,
    configuration: RulesetConfiguration,
    start_generation: int,
    position_factory: CtfPositionFactory | None = None,
    progress: ProgressCallback | None,
    record_timings: Callable[[list[str]], None] | None = None,
) -> list[str]:
    """Train `config.generations` generations into `run_dir`, labelling the first
    of them `start_generation` (1 for a fresh run, `latest_checkpoint + 1` for a
    resume), and return what the run had to report per generation.

    Each generation builds a fresh optimizer, trains `network` in place, and saves
    it under the checkpoint convention — so the checkpoint iteration is the total
    number of generations trained so far, and a resume can continue from it.

    `configuration` is the ruleset every checkpoint written here is stamped with:
    the active one for a fresh run, and for a resume the one adopted from the
    checkpoint it continued from. Passing it rather than letting `save_checkpoint`
    reach for the active configuration is what keeps a resume's own checkpoints
    tagged with the rules its weights were actually trained under.

    The returned lines are the same loss summaries a caller's `progress` callback
    prints (both come from `format_generation_progress`), collected so the run's
    timing record can carry them and read as the whole story of the run.

    `record_timings`, if given, is called with those lines after every
    checkpoint — see `_timing_recorder`.
    """
    reported: list[str] = []
    for offset in range(config.generations):
        generation = start_generation + offset
        # Every generation records into the same `generation` node: the report is
        # cumulative, so its call count is how many generations ran and its mean
        # is what one costs.
        with region(GENERATION):
            with region(BUILD_OPTIMIZER):
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
            with region(SAVE_CHECKPOINT):
                save_checkpoint(
                    network,
                    checkpoint_path(run_dir, generation),
                    configuration=configuration,
                )
        reported.append(format_generation_progress(generation, history))
        # Paired with the checkpoint: a generation's weights and the cost of
        # producing them land on disk together, so whatever ends the run —
        # an exception, a Ctrl-C, the machine rebooting under it — leaves the
        # generations that did finish accounted for.
        if record_timings is not None:
            record_timings(reported)
        if progress is not None:
            progress(generation, history)
    return reported


def _timing_recorder(
    session: TimingSession | None,
    run_dir: Path,
    *,
    settings: dict[str, object],
    resolved_device: ResolvedDevice,
    stem: str = TIMING_RECORD_STEM,
) -> Callable[[list[str]], None] | None:
    """A callable that rewrites the run's record from the timings so far, or
    None when the run is not being measured.

    Overwriting the same pair each time rather than numbering them keeps a run
    directory to one record per measurement: the last write, at the end of the
    run, is the complete one, and the interim writes exist only so that there is
    something to read if that write never happens. They are cheap next to the
    checkpoint they accompany — kilobytes against ~15MB — and silent, since a
    whole tree on the console every generation would drown the loss lines.
    """
    if session is None:
        return None

    def record(reported: list[str]) -> None:
        _report_timings(
            session,
            run_dir,
            settings=settings,
            stem=stem,
            resolved_device=resolved_device,
            preamble=reported,
            echo=False,
        )

    return record


def _report_timings(
    session: TimingSession | None,
    run_dir: Path,
    *,
    settings: dict[str, object],
    resolved_device: ResolvedDevice,
    stem: str = TIMING_RECORD_STEM,
    preamble: list[str],
    echo: bool = True,
) -> None:
    """Write (and by default print) the run's breakdown, if it was measured at all.

    The hyperparameters go into the timing record as well as `run-config.json`:
    the record is what gets carried elsewhere and compared against a later run,
    and a breakdown separated from the settings that produced it is not worth
    much.
    """
    if session is None:
        return
    report_timings(
        session,
        directory=run_dir,
        kind=ROOT_TRAINING,
        settings=settings,
        resolved_device=resolved_device,
        stem=stem,
        preamble=preamble,
        echo=echo,
    )


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


def _check_ruleset_agrees(
    stamped: RulesetConfiguration, recorded: RulesetConfiguration, checkpoint: Path
) -> None:
    """Cross-check a resumed run's two independent ruleset records.

    `stamped` comes from the checkpoint's own stamp and `recorded` from the run's
    `run-config.json`; the same run wrote both and they cannot legitimately
    differ. If they do, the run directory has been edited or files from different
    runs have been mixed, and continuing would add generations under rules that
    do not describe the network being trained.

    The division is the one `_check_architecture_agrees` already draws: the stamp
    attached to the weights is what the run continues under, and the run config is
    checked against it rather than the other way round.
    """
    differences = configuration_differences(
        recorded, stamped, left_label=RUN_CONFIG_FILENAME, right_label=str(checkpoint)
    )
    if differences:
        raise ValueError(
            "The run directory is inconsistent: "
            f"{'; '.join(differences)}. Resume from a run whose config and "
            "checkpoints agree on the rules they were produced under."
        )


def _write_run_config(run_dir: Path, config: TrainingConfig) -> None:
    """Write the reproducibility record: the config, the rules the run was played
    under, the environment it ran against (dependency versions and this repo's
    commit), and the start time.

    The ruleset belongs here for the same reason the hyperparameters and seed do:
    a record that reproduces everything about a run *except* which rules its
    games were played under does not reproduce the run. It is recorded twice — in
    this file and in each checkpoint's own stamp — exactly as the architecture is,
    and `_check_ruleset_agrees` is what keeps the two honest.
    """
    record = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "config": asdict(config),
        "ruleset": active_configuration().as_stamp(),
        "versions": {
            "game_engine_core": distribution_version("game-engine-core"),
            "capture_the_flag": distribution_version("capture-the-flag"),
            "torch": torch.__version__,
        },
        "git_commit": git_commit(),
    }
    path = run_dir / RUN_CONFIG_FILENAME
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _read_run_record(run_dir: Path) -> dict[str, Any]:
    """The run's `run-config.json`, parsed.

    Read once and handed to both `_run_config` and `_run_ruleset`: a resume needs
    two different things out of the same small file, and re-reading it per field
    would leave them able to disagree about what the file said.
    """
    return json.loads((run_dir / RUN_CONFIG_FILENAME).read_text(encoding="utf-8"))


def _run_config(record: dict[str, Any]) -> TrainingConfig:
    """Reconstruct the run's `TrainingConfig` from its `run-config.json` record,
    so a resume reproduces the original run's self-play and training settings
    instead of falling back to fresh defaults."""
    return TrainingConfig(**record["config"])


def _run_ruleset(record: dict[str, Any], run_dir: Path) -> RulesetConfiguration:
    """The ruleset configuration the run's `run-config.json` record carries.

    A run directory written before ruleset stamping has no such key. That is the
    same refusal `checkpoint_configuration` makes, and for the same reason: the
    rules the run was played under are unknown, and assuming the current ones
    would be asserting something unknown. `run_dir` is carried only to name the
    file in that message.
    """
    path = run_dir / RUN_CONFIG_FILENAME
    if "ruleset" not in record:
        raise ValueError(
            f"{path} records no ruleset, so it predates ruleset stamping and the "
            "rules its games were played under are unknown."
        )
    try:
        return RulesetConfiguration.from_stamp(record["ruleset"])
    except ValueError as error:
        raise ValueError(f"{path}'s ruleset record is malformed: {error}") from error


def _append_resume_record(
    run_dir: Path, *, resumed_from: int, added_generations: int
) -> int:
    """Note this resume in the run's record and return its 1-based index.

    The original config is left intact and each resume appends an entry — when it
    happened, which checkpoint it continued from, how many generations it added,
    and the commit it ran against — so the record still reproduces the run as a
    whole across any number of resumes. The index is what a resume's timing
    record is named after, tying the two together.
    """
    path = run_dir / RUN_CONFIG_FILENAME
    record = json.loads(path.read_text(encoding="utf-8"))
    resumes = record.setdefault("resumes", [])
    resumes.append(
        {
            "resumed": datetime.now().isoformat(timespec="seconds"),
            "resumed_from_checkpoint": resumed_from,
            "added_generations": added_generations,
            "git_commit": git_commit(),
        }
    )
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return len(resumes)

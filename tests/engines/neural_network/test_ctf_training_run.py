"""End-to-end smoke test for the training orchestrator.

Marked `slow`: it runs real self-play (MCTS) and gradient descent, so it is
excluded from the default suite and opted into with `pytest -m slow`. At tiny
scale it exercises the whole generations loop and asserts the run's artifacts —
a checkpoint per generation and a parseable run-config record — rather than any
strength claim, which is deferred.
"""

import json

import pytest
from game_engine_learning.checkpoints import discover_checkpoints, new_run_directory

from capture_the_flag.engines.neural_network.ctf_training_run import (
    RUN_CONFIG_FILENAME,
    TrainingConfig,
    resume_generations,
    train_generations,
)


@pytest.mark.slow
def test_train_generations_writes_a_checkpoint_series_and_config(tmp_path):
    config = TrainingConfig(
        generations=2,
        games_per_generation=1,
        self_play_iterations=10,
        epochs_per_generation=2,
        batch_size=8,
        seed=0,
    )
    recorded: list[tuple[int, list]] = []

    run_dir = train_generations(
        config,
        base_dir=tmp_path,
        progress=lambda generation, history: recorded.append((generation, history)),
    )

    # One checkpoint per generation, numbered by generations trained so far.
    checkpoints = discover_checkpoints(run_dir)
    assert [checkpoint.iteration for checkpoint in checkpoints] == [1, 2]

    # A reproducibility record that round-trips through JSON and carries the config.
    record = json.loads((run_dir / RUN_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert record["config"]["generations"] == 2
    assert record["config"]["self_play_iterations"] == 10
    assert record["versions"]["game_engine_core"] is not None

    # The progress callback fired once per generation, each with its epoch history.
    assert [generation for generation, _ in recorded] == [1, 2]
    assert all(len(history) == config.epochs_per_generation for _, history in recorded)


def test_resume_with_no_previous_run_raises(tmp_path):
    """Resume needs a run to continue: an empty base directory is a clear error,
    not a silent fresh start."""
    with pytest.raises(FileNotFoundError):
        resume_generations(1, base_dir=tmp_path)


def test_resume_with_no_checkpoint_raises(tmp_path):
    """A run directory with no checkpoint (e.g. the process died before the first
    generation saved) has nothing to reload from."""
    new_run_directory(tmp_path)  # a run dir, but no checkpoint file inside it
    with pytest.raises(FileNotFoundError):
        resume_generations(1, base_dir=tmp_path)


def test_resume_rejects_non_positive_added_generations(tmp_path):
    with pytest.raises(ValueError):
        resume_generations(0, base_dir=tmp_path)


@pytest.mark.slow
def test_resume_appends_to_the_same_run_and_continues_numbering(tmp_path):
    config = TrainingConfig(
        generations=1,
        games_per_generation=1,
        self_play_iterations=10,
        epochs_per_generation=2,
        batch_size=8,
        seed=0,
    )
    original_run = train_generations(config, base_dir=tmp_path)
    assert [c.iteration for c in discover_checkpoints(original_run)] == [1]

    recorded: list[tuple[int, list]] = []
    resumed_run = resume_generations(
        1,
        base_dir=tmp_path,
        progress=lambda generation, history: recorded.append((generation, history)),
    )

    # Same run directory — checkpoints are appended, not written to a fresh run.
    assert resumed_run == original_run
    assert [c.iteration for c in discover_checkpoints(resumed_run)] == [1, 2]

    # Numbering picks up where it left off: the next generation is 2, not 1.
    assert [generation for generation, _ in recorded] == [2]

    # The record preserves the original config and notes the resume.
    record = json.loads((resumed_run / RUN_CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert record["config"]["generations"] == 1
    assert len(record["resumes"]) == 1
    assert record["resumes"][0]["resumed_from_checkpoint"] == 1
    assert record["resumes"][0]["added_generations"] == 1

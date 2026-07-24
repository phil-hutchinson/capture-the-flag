"""End-to-end smoke test for the training orchestrator (story 00000009, Step 6).

Marked `slow`: it runs real self-play (MCTS) and gradient descent, so it is
excluded from the default suite and opted into with `pytest -m slow`. At tiny
scale it exercises the whole generations loop and asserts the run's artifacts —
a checkpoint per generation and a parseable run-config record — rather than any
strength claim, which is deferred.
"""

import json

import pytest
from game_engine_learning.checkpoints import discover_checkpoints

from capture_the_flag.engines.neural_network.ctf_training_run import (
    RUN_CONFIG_FILENAME,
    TrainingConfig,
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

"""End-to-end smoke test for the training orchestrator.

Marked `slow`: it runs real self-play (MCTS) and gradient descent, so it is
excluded from the default suite and opted into with `pytest -m slow`. At tiny
scale it exercises the whole generations loop and asserts the run's artifacts —
a checkpoint per generation and a parseable run-config record — rather than any
strength claim, which is deferred. The runs are trained at the small test
architecture: the loop's behaviour does not depend on the trunk's size, and the
default one would make an already-slow test slower still.
"""

import json

import pytest
import torch
from game_engine_learning.checkpoints import (
    checkpoint_path,
    discover_checkpoints,
    new_run_directory,
)
from game_engine_learning.training_loop import EpochLoss

from capture_the_flag.engines.neural_network.ctf_checkpoint import save_checkpoint
from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_training_run import (
    RUN_CONFIG_FILENAME,
    TrainingConfig,
    _write_run_config,
    resume_generations,
    train_generations,
)
from capture_the_flag.record import (
    DEFAULT_EDITION,
    RuleFlag,
    RulesetConfiguration,
    active_configuration,
)
from tests.engines.neural_network.small_networks import (
    BATTLE_TENSOR_LAYOUT,
    SMALL_FEATURE_COUNT,
    SMALL_RESIDUAL_BLOCK_COUNT,
)


@pytest.mark.slow
def test_train_generations_writes_a_checkpoint_series_and_config(tmp_path):
    config = TrainingConfig(
        generations=2,
        games_per_generation=1,
        self_play_iterations=10,
        epochs_per_generation=2,
        batch_size=8,
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
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
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
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

    # The architecture the run was started at is what it resumed at, from the
    # run's own record rather than from the (different) current defaults.
    assert record["config"]["feature_count"] == SMALL_FEATURE_COUNT
    assert record["config"]["residual_block_count"] == SMALL_RESIDUAL_BLOCK_COUNT
    assert SMALL_FEATURE_COUNT != TrainingConfig().feature_count


def test_resume_rejects_a_run_whose_config_and_checkpoint_disagree(tmp_path):
    """The two independent architecture records — the run config and the
    checkpoint's own stamp — must agree. They cannot legitimately differ, so a
    hand-edited or mixed-up run directory is refused rather than resumed under a
    config that does not describe the network being trained. Assembled directly
    (no training) because the failure is about the recorded metadata, not about
    anything the loop computes."""
    run_dir = new_run_directory(tmp_path)
    config = TrainingConfig(feature_count=SMALL_FEATURE_COUNT, residual_block_count=3)
    _write_run_config(run_dir, config, active_configuration())
    # A checkpoint at a *different* depth than the config claims.
    save_checkpoint(
        CtfCrn(
            BATTLE_TENSOR_LAYOUT,
            feature_count=SMALL_FEATURE_COUNT,
            residual_block_count=2,
        ),
        checkpoint_path(run_dir, 1),
    )

    with pytest.raises(ValueError, match="inconsistent"):
        resume_generations(1, base_dir=tmp_path)


def _assembled_run(tmp_path, configuration=None):
    """A run directory with a config and one checkpoint, built without training.

    The ruleset failures below are all about recorded metadata, not about
    anything the generations loop computes, so assembling the directory directly
    keeps them out of the `slow` suite.

    `configuration`, if given, is what both records carry — standing in for a run
    conducted under something other than the current active configuration, which
    is the only way to tell adoption from re-stamping while one edition and no
    flags are published.
    """
    run_dir = new_run_directory(tmp_path)
    config = TrainingConfig(
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
    )
    _write_run_config(run_dir, config, active_configuration())
    if configuration is not None:
        _rewrite_run_config(run_dir, ruleset=configuration.as_stamp())
    save_checkpoint(
        CtfCrn(
            BATTLE_TENSOR_LAYOUT,
            feature_count=SMALL_FEATURE_COUNT,
            residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
        ),
        checkpoint_path(run_dir, 1),
        configuration=configuration,
    )
    return run_dir


def _rewrite_run_config(run_dir, **changes):
    path = run_dir / RUN_CONFIG_FILENAME
    record = json.loads(path.read_text(encoding="utf-8"))
    record.update(changes)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def test_run_config_records_the_ruleset_the_run_was_played_under(tmp_path):
    # A record that reproduces the hyperparameters, the architecture, and the seed
    # but not the rules does not reproduce the run.
    run_dir = _assembled_run(tmp_path)

    record = json.loads((run_dir / RUN_CONFIG_FILENAME).read_text(encoding="utf-8"))

    assert record["ruleset"] == active_configuration().as_stamp()


def test_resume_rejects_a_run_whose_config_and_checkpoint_disagree_on_the_ruleset(
    tmp_path,
):
    # The same refusal the architecture cross-check makes, for the same reason:
    # one run wrote both records, so a difference means the directory has been
    # edited or files from two runs have been mixed.
    run_dir = _assembled_run(tmp_path)
    _rewrite_run_config(run_dir, ruleset={"edition": "1-3:PRE-RELEASE", "flags": {}})

    with pytest.raises(ValueError, match="inconsistent") as rejection:
        resume_generations(1, base_dir=tmp_path)
    message = str(rejection.value)
    # Both values, each attributed to its source — a bare "they differ" would not
    # tell the developer which file to look at.
    assert "1-3:PRE-RELEASE" in message
    assert DEFAULT_EDITION in message
    assert RUN_CONFIG_FILENAME in message


def test_resume_rejects_a_run_config_from_before_ruleset_stamping(tmp_path):
    # No ruleset key at all: the rules the run's games were played under are
    # unknown, and assuming the current ones would assert something unknown.
    run_dir = _assembled_run(tmp_path)
    path = run_dir / RUN_CONFIG_FILENAME
    record = json.loads(path.read_text(encoding="utf-8"))
    del record["ruleset"]
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no ruleset"):
        resume_generations(1, base_dir=tmp_path)


def test_resume_stamps_its_own_checkpoints_with_the_configuration_it_adopted(
    tmp_path, monkeypatch
):
    # The stamp is adopted, not merely verified: a resume continues under the
    # configuration its weights were trained under, so the generations it appends
    # must carry that configuration and not the current active one. With a single
    # published edition and an empty flag registry the two coincide, which is why
    # this test has to supply a flag — the failure it guards against only becomes
    # reachable once a second variant exists, and by then it is silent.
    monkeypatch.setattr(
        "capture_the_flag.record.RULE_FLAGS",
        {"MOVABLE_TOWERS": RuleFlag(flag_id="MOVABLE_TOWERS", values=("off", "on"), default="off")},
    )
    trained_under = RulesetConfiguration(DEFAULT_EDITION, {"MOVABLE_TOWERS": "on"})
    run_dir = _assembled_run(tmp_path, configuration=trained_under)
    # Self-play and gradient descent are not what is under test, and running them
    # would put this in the `slow` suite; the stub keeps the resume path itself
    # real, checkpoint stamping included.
    monkeypatch.setattr(
        "capture_the_flag.engines.neural_network.ctf_training_run.train_one_generation",
        lambda *args, **kwargs: [EpochLoss(value=0.5, policy=0.5)],
    )

    resume_generations(1, base_dir=tmp_path, timing=False)

    appended = torch.load(checkpoint_path(run_dir, 2), map_location="cpu", weights_only=True)
    assert appended["ruleset"] == trained_under.as_stamp()
    assert appended["ruleset"] != active_configuration().as_stamp()


def test_resume_rejects_a_malformed_ruleset_record(tmp_path):
    # Present but unreadable earns the same named failure as absent, rather than
    # a KeyError from somewhere deeper.
    run_dir = _assembled_run(tmp_path)
    _rewrite_run_config(run_dir, ruleset="1-2:PRE-RELEASE")

    with pytest.raises(ValueError, match="malformed"):
        resume_generations(1, base_dir=tmp_path)

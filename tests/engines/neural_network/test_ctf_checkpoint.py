"""Checkpoint save/load round-trip tests.

A checkpoint is weights-only, so the correctness claim is that a network reloaded
from disk evaluates a fixed position *identically* to the in-memory original —
same value, same policy — and that the shared discovery convention lists saved
files in iteration order. These are the two things the training loop and the
(later) resume path rely on.

The stamps a checkpoint carries are tested here too, and they are tested as the
asymmetric pair they are: an engine-spec mismatch is rejected, while a differing
architecture is *reconstructed* — the network comes back at the width and depth
the file records rather than at whatever the current defaults are.
"""

from pathlib import Path

import pytest
import torch
from game_engine_learning.checkpoints import checkpoint_path, discover_checkpoints

from capture_the_flag.engines.neural_network.ctf_checkpoint import (
    load_network,
    load_neural_player,
    save_checkpoint,
)
from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.engines.neural_network.neural_ctf_player import NeuralCtfPlayer
from capture_the_flag.engines.neural_network.tensor_layout import ENGINE_SPEC_NAME
from tests.engines.neural_network.small_networks import small_network


def test_saved_network_round_trips_to_identical_evaluation(tmp_path: Path):
    # Seed the init so a failure is reproducible; a single fixed position is
    # evaluated by both networks, so any difference is the checkpoint's doing,
    # not the input's.
    torch.manual_seed(0)
    original = small_network()
    position = CtfPositionFactory()()

    original_eval = CtfNNEvaluator(original).evaluate_position(position)

    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path)

    restored_eval = CtfNNEvaluator(load_network(path)).evaluate_position(position)

    # Weights and BatchNorm buffers all live in the state dict, and evaluation is
    # a deterministic no-grad forward pass, so the reload must reproduce the
    # original exactly — not merely approximately.
    assert restored_eval.value == original_eval.value
    assert restored_eval.policy == original_eval.policy


def test_discover_checkpoints_returns_saved_files_in_iteration_order(tmp_path: Path):
    network = small_network()
    # Save out of order to prove discovery sorts by iteration, not by write time.
    for iteration in (0, 5, 2):
        save_checkpoint(network, checkpoint_path(tmp_path, iteration))

    discovered = discover_checkpoints(tmp_path)

    assert [checkpoint.iteration for checkpoint in discovered] == [0, 2, 5]
    assert all(checkpoint.path.exists() for checkpoint in discovered)


def test_checkpoint_loads_into_a_playable_seat(tmp_path: Path):
    # The AC's "any checkpoint can be loaded and used as a playing engine": the
    # loader composes the full evaluator + engine + player seat from the file.
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path)

    player = load_neural_player(path, name="loaded")

    assert isinstance(player, NeuralCtfPlayer)


def test_saved_checkpoint_is_stamped_with_the_current_engine_spec(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path)

    raw = torch.load(path, map_location="cpu", weights_only=True)

    assert raw["spec"] == ENGINE_SPEC_NAME


def test_load_network_rejects_a_checkpoint_stamped_for_a_different_spec(tmp_path: Path):
    # Simulates a checkpoint saved under a later, incompatible spec revision.
    path = checkpoint_path(tmp_path, 0)
    torch.save({"spec": "ENG_NN_99", "state_dict": small_network().state_dict()}, path)

    with pytest.raises(ValueError, match="ENG_NN_99"):
        load_network(path)


def test_load_network_rejects_a_checkpoint_from_before_spec_stamping(tmp_path: Path):
    # The pre-story checkpoint format: a bare state_dict, no wrapping/stamp at
    # all (what every ENG_NN_1 checkpoint on disk looks like).
    path = checkpoint_path(tmp_path, 0)
    torch.save(small_network().state_dict(), path)

    with pytest.raises(ValueError, match="engine-spec stamp"):
        load_network(path)


def test_saved_checkpoint_is_stamped_with_the_networks_architecture(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(CtfCrn(feature_count=12, residual_block_count=3), path)

    raw = torch.load(path, map_location="cpu", weights_only=True)

    assert raw["architecture"] == {"feature_count": 12, "residual_block_count": 3}


def test_load_network_rebuilds_at_the_stamped_architecture(tmp_path: Path):
    # The asymmetry's payoff: a checkpoint trained at a non-default size loads
    # under code whose defaults are something else entirely, because the file —
    # not the current default — decides the shape the weights go back into.
    torch.manual_seed(0)
    original = CtfCrn(feature_count=12, residual_block_count=3)
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path)

    restored = load_network(path)

    assert restored.feature_count == 12
    assert restored.residual_block_count == 3
    assert restored.feature_count != CtfCrn().feature_count  # genuinely non-default
    original_state = original.state_dict()
    restored_state = restored.state_dict()
    assert restored_state.keys() == original_state.keys()
    assert all(
        torch.equal(restored_state[key], original_state[key]) for key in original_state
    )


def test_default_built_checkpoint_round_trips_at_the_default_architecture(
    tmp_path: Path,
):
    # The default architecture is the one training actually uses, so it gets its
    # own round-trip rather than riding on the small networks the other tests
    # build. Constructing it is the cost here, not a forward pass.
    original = CtfCrn()
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path)

    restored = load_network(path)

    assert restored.feature_count == original.feature_count
    assert restored.residual_block_count == original.residual_block_count


def test_load_network_rejects_a_checkpoint_with_no_architecture_stamp(tmp_path: Path):
    # Correctly spec-stamped but predating architecture stamping: the weights'
    # shape is unknowable, and guessing is exactly what stamping exists to avoid.
    path = checkpoint_path(tmp_path, 0)
    network = small_network()
    torch.save(
        {"spec": ENGINE_SPEC_NAME, "state_dict": network.state_dict()}, path
    )

    with pytest.raises(ValueError, match="architecture stamp"):
        load_network(path)

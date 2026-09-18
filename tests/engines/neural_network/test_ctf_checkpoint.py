"""Checkpoint save/load round-trip tests.

A checkpoint is weights-only, so the correctness claim is that a network reloaded
from disk evaluates a fixed position *identically* to the in-memory original —
same value, same policy — and that the shared discovery convention lists saved
files in iteration order. These are the two things the training loop and the
(later) resume path rely on.

The stamps a checkpoint carries are tested here too, and they are tested as the
asymmetric set they are: an engine-spec mismatch is rejected, a differing
architecture is *reconstructed* — the network comes back at the width and depth
the file records rather than at whatever the current defaults are — and the
ruleset configuration is adopted when this code can implement it and rejected
when it cannot, including when it is absent entirely.
"""

from pathlib import Path

import pytest
import torch
from game_engine_learning.checkpoints import checkpoint_path, discover_checkpoints

from capture_the_flag.engines.neural_network.ctf_checkpoint import (
    checkpoint_configuration,
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
from capture_the_flag.record import (
    ACTIVE_EDITIONS,
    DEFAULT_EDITION,
    RuleFlag,
    RulesetConfiguration,
    active_configuration,
)
from tests.engines.neural_network.small_networks import (
    OTHER_TENSOR_LAYOUT,
    PRE_RELEASE_SETUP,
    PRE_RELEASE_TENSOR_LAYOUT,
    small_network,
)

_SPEC = PRE_RELEASE_TENSOR_LAYOUT.spec
_CONFIGURATION = PRE_RELEASE_SETUP.stamp


def test_saved_network_round_trips_to_identical_evaluation(tmp_path: Path):
    # Seed the init so a failure is reproducible; a single fixed position is
    # evaluated by both networks, so any difference is the checkpoint's doing,
    # not the input's.
    torch.manual_seed(0)
    original = small_network()
    position = CtfPositionFactory(setup=PRE_RELEASE_SETUP)()

    original_eval = CtfNNEvaluator(original, PRE_RELEASE_TENSOR_LAYOUT).evaluate_positions([position])[0]

    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path, configuration=_CONFIGURATION)

    restored_eval = CtfNNEvaluator(load_network(path, PRE_RELEASE_SETUP), PRE_RELEASE_TENSOR_LAYOUT).evaluate_positions([position])[0]

    # Weights and BatchNorm buffers all live in the state dict, and evaluation is
    # a deterministic no-grad forward pass, so the reload must reproduce the
    # original exactly — not merely approximately.
    assert restored_eval.value == original_eval.value
    assert restored_eval.policy == original_eval.policy


def test_discover_checkpoints_returns_saved_files_in_iteration_order(tmp_path: Path):
    network = small_network()
    # Save out of order to prove discovery sorts by iteration, not by write time.
    for iteration in (0, 5, 2):
        save_checkpoint(network, checkpoint_path(tmp_path, iteration), configuration=_CONFIGURATION)

    discovered = discover_checkpoints(tmp_path)

    assert [checkpoint.iteration for checkpoint in discovered] == [0, 2, 5]
    assert all(checkpoint.path.exists() for checkpoint in discovered)


def test_checkpoint_loads_into_a_playable_seat(tmp_path: Path):
    # The AC's "any checkpoint can be loaded and used as a playing engine": the
    # loader composes the full evaluator + engine + player seat from the file.
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path, configuration=_CONFIGURATION)

    player = load_neural_player(path, "loaded", PRE_RELEASE_SETUP)

    assert isinstance(player, NeuralCtfPlayer)


def test_saved_checkpoint_is_stamped_with_the_current_engine_spec(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path, configuration=_CONFIGURATION)

    raw = torch.load(path, map_location="cpu", weights_only=True)

    assert raw["spec"] == _SPEC


def test_load_network_rejects_a_checkpoint_stamped_for_a_different_spec(tmp_path: Path):
    # Simulates a checkpoint saved under a later, incompatible spec revision.
    path = checkpoint_path(tmp_path, 0)
    torch.save({"spec": "ENG_NN_99", "state_dict": small_network().state_dict()}, path)

    with pytest.raises(ValueError, match="ENG_NN_99"):
        load_network(path, PRE_RELEASE_SETUP)


def test_load_network_rejects_a_checkpoint_from_before_spec_stamping(tmp_path: Path):
    # The pre-story checkpoint format: a bare state_dict, no wrapping/stamp at
    # all (what every ENG_NN_1 checkpoint on disk looks like).
    path = checkpoint_path(tmp_path, 0)
    torch.save(small_network().state_dict(), path)

    with pytest.raises(ValueError, match="engine-spec stamp"):
        load_network(path, PRE_RELEASE_SETUP)


def test_saved_checkpoint_is_stamped_with_the_networks_architecture(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(
        CtfCrn(PRE_RELEASE_TENSOR_LAYOUT, feature_count=12, residual_block_count=3),
        path,
        configuration=_CONFIGURATION,
    )

    raw = torch.load(path, map_location="cpu", weights_only=True)

    assert raw["architecture"] == {"feature_count": 12, "residual_block_count": 3}


def test_load_network_rebuilds_at_the_stamped_architecture(tmp_path: Path):
    # The asymmetry's payoff: a checkpoint trained at a non-default size loads
    # under code whose defaults are something else entirely, because the file —
    # not the current default — decides the shape the weights go back into.
    torch.manual_seed(0)
    original = CtfCrn(PRE_RELEASE_TENSOR_LAYOUT, feature_count=12, residual_block_count=3)
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path, configuration=_CONFIGURATION)

    restored = load_network(path, PRE_RELEASE_SETUP)

    assert restored.feature_count == 12
    assert restored.residual_block_count == 3
    assert restored.feature_count != CtfCrn(PRE_RELEASE_TENSOR_LAYOUT).feature_count  # genuinely non-default
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
    original = CtfCrn(PRE_RELEASE_TENSOR_LAYOUT)
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(original, path, configuration=_CONFIGURATION)

    restored = load_network(path, PRE_RELEASE_SETUP)

    assert restored.feature_count == original.feature_count
    assert restored.residual_block_count == original.residual_block_count


def test_load_network_rejects_a_checkpoint_with_no_architecture_stamp(tmp_path: Path):
    # Correctly spec-stamped but predating architecture stamping: the weights'
    # shape is unknowable, and guessing is exactly what stamping exists to avoid.
    path = checkpoint_path(tmp_path, 0)
    network = small_network()
    torch.save(
        {"spec": _SPEC, "state_dict": network.state_dict()}, path
    )

    with pytest.raises(ValueError, match="architecture stamp"):
        load_network(path, PRE_RELEASE_SETUP)


def test_load_network_rejects_a_malformed_architecture_stamp(tmp_path: Path):
    # A stamp that is present but unreadable is no better than an absent one, so
    # it gets the same named failure rather than a bare KeyError from indexing it.
    path = checkpoint_path(tmp_path, 0)
    torch.save(
        {
            "spec": _SPEC,
            "architecture": {"feature_count": 8},  # depth missing
            "state_dict": small_network().state_dict(),
        },
        path,
    )

    with pytest.raises(ValueError, match="malformed"):
        load_network(path, PRE_RELEASE_SETUP)


def _architecture_of(network: CtfCrn) -> dict[str, int]:
    return {
        "feature_count": network.feature_count,
        "residual_block_count": network.residual_block_count,
    }


def _checkpoint_without_ruleset(network: CtfCrn) -> dict[str, object]:
    """A checkpoint correct in every respect except that it predates ruleset
    stamping — the shape every file under `training-runs/` had before this
    story."""
    return {
        "spec": _SPEC,
        "architecture": _architecture_of(network),
        "state_dict": network.state_dict(),
    }


def test_saved_checkpoint_is_stamped_with_the_ruleset_configuration(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path, configuration=_CONFIGURATION)

    raw = torch.load(path, map_location="cpu", weights_only=True)

    # Structured, not concatenated: comparison over the parts is what produces a
    # rejection message naming the offending flag.
    assert raw["ruleset"] == {"edition": DEFAULT_EDITION, "flags": {}}


def test_checkpoint_configuration_reads_back_what_was_stamped(tmp_path: Path):
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(), path, configuration=_CONFIGURATION)

    assert checkpoint_configuration(path) == active_configuration()


def test_a_supplied_configuration_is_stamped_instead_of_the_active_one(tmp_path: Path):
    # What a resume passes: the configuration it adopted from the checkpoint it
    # continued from. Without this the generations a resume appends would be
    # stamped with the current active edition — re-tagging weights that were
    # trained under something else, which is the mis-tagging the stamp exists to
    # prevent.
    adopted = RulesetConfiguration("1-3:PRE-RELEASE", {"MOVABLE_TOWERS": "on"})
    path = checkpoint_path(tmp_path, 0)

    save_checkpoint(small_network(), path, configuration=adopted)

    raw = torch.load(path, map_location="cpu", weights_only=True)
    assert raw["ruleset"] == adopted.as_stamp()


def test_a_file_that_is_not_a_checkpoint_is_diagnosed_the_same_either_way(
    tmp_path: Path,
):
    # Both entry points load the same file, so a structurally broken one must not
    # be reported as missing whichever stamp its reader happened to want first.
    path = checkpoint_path(tmp_path, 0)
    torch.save([1, 2, 3], path)

    with pytest.raises(ValueError, match="not a checkpoint") as from_load:
        load_network(path, PRE_RELEASE_SETUP)
    with pytest.raises(ValueError, match="not a checkpoint") as from_configuration:
        checkpoint_configuration(path)

    assert str(from_load.value) == str(from_configuration.value)


def test_load_network_rejects_a_checkpoint_from_before_ruleset_stamping(tmp_path: Path):
    # A network is only valid for the rules it was trained under, and an unstamped
    # checkpoint cannot say what those were. Defaulting it would assert something
    # unknown, so it is refused — the same call the absent-architecture case makes.
    path = checkpoint_path(tmp_path, 0)
    torch.save(_checkpoint_without_ruleset(small_network()), path)

    with pytest.raises(ValueError, match="ruleset stamp"):
        load_network(path, PRE_RELEASE_SETUP)


def test_checkpoint_configuration_rejects_a_checkpoint_from_before_stamping(
    tmp_path: Path,
):
    path = checkpoint_path(tmp_path, 0)
    torch.save(_checkpoint_without_ruleset(small_network()), path)

    with pytest.raises(ValueError, match="ruleset stamp"):
        checkpoint_configuration(path)


def test_load_network_rejects_a_malformed_ruleset_stamp(tmp_path: Path):
    # The rendered string rather than the structured form: readable to a human,
    # unusable as a stamp, and it must fail by name rather than half-parse.
    path = checkpoint_path(tmp_path, 0)
    network = small_network()
    torch.save(
        {**_checkpoint_without_ruleset(network), "ruleset": DEFAULT_EDITION}, path
    )

    with pytest.raises(ValueError, match="ruleset stamp is malformed"):
        load_network(path, PRE_RELEASE_SETUP)


def test_load_network_rejects_a_configuration_this_code_cannot_implement(
    tmp_path: Path,
):
    # A checkpoint from a variant branch, arriving at a build that has no such
    # flag. Major 3 publishes none at all (`record.RULE_FLAGS` is empty), so
    # every flag lands here. The engine-spec stamp cannot catch this — a
    # rules-only change leaves the tensor shape untouched — so without the
    # ruleset stamp these weights would load cleanly and evaluate under rules
    # they were never trained for.
    path = checkpoint_path(tmp_path, 0)
    network = small_network()
    torch.save(
        {
            **_checkpoint_without_ruleset(network),
            "ruleset": {
                "edition": DEFAULT_EDITION,
                "flags": {"MOVABLE_TOWERS": "on"},
            },
        },
        path,
    )

    with pytest.raises(ValueError, match="MOVABLE_TOWERS") as rejection:
        load_network(path, PRE_RELEASE_SETUP)
    assert "no such flag" in str(rejection.value)


def test_the_spec_stamp_is_qualified_by_the_board_it_was_trained_on(tmp_path: Path):
    # One spec document, any number of boards, incompatible sets of weights per
    # board — so the stamp names the board as well as the contract.
    # `OTHER_TENSOR_LAYOUT` (a hand-built layout naming no published edition,
    # see `small_networks.py`) stands in for the second board major 2's
    # Skirmish used to play this role with; only the spec stamp is under test
    # here, so it is saved under the real configuration regardless of shape.
    pre_release_path = checkpoint_path(tmp_path / "pre_release", 0)
    other_path = checkpoint_path(tmp_path / "other", 0)
    save_checkpoint(small_network(PRE_RELEASE_TENSOR_LAYOUT), pre_release_path, configuration=_CONFIGURATION)
    save_checkpoint(
        small_network(OTHER_TENSOR_LAYOUT), other_path, configuration=_CONFIGURATION
    )

    pre_release_stamp = torch.load(pre_release_path, map_location="cpu", weights_only=True)["spec"]
    other_stamp = torch.load(other_path, map_location="cpu", weights_only=True)[
        "spec"
    ]

    assert pre_release_stamp == "ENG_NN_3/simple_64"
    assert other_stamp == "ENG_NN_3/test_only_small"


def test_load_network_rejects_a_checkpoint_trained_on_another_board(tmp_path: Path):
    # The failure the qualified stamp exists for. Without it the load would fail
    # deep inside `load_state_dict` on a policy-head shape, or — for a layout
    # change that preserved the dimensions — not fail at all.
    path = checkpoint_path(tmp_path, 0)
    save_checkpoint(small_network(OTHER_TENSOR_LAYOUT), path, configuration=_CONFIGURATION)

    with pytest.raises(ValueError, match="test_only_small") as rejection:
        load_network(path, PRE_RELEASE_SETUP)
    assert "simple_64" in str(rejection.value)


def test_load_network_rejects_a_checkpoint_stamped_with_a_historical_edition(
    tmp_path: Path,
):
    # `1-2:PRE-RELEASE` is still a *known* edition — it has to be, or a stamped
    # artifact could not name anything meaningful — but it is not Active. The
    # refusal is on that ground: the rules moved on, so these weights never saw
    # the ones being played. Not on the ground that a build holds only one
    # edition full stop; a build implements every Active edition and refuses
    # only the ones it no longer plays, which happens to be a set of one today.
    path = checkpoint_path(tmp_path, 0)
    network = small_network()
    torch.save(
        {
            **_checkpoint_without_ruleset(network),
            "ruleset": {"edition": "1-2:PRE-RELEASE", "flags": {}},
        },
        path,
    )

    with pytest.raises(ValueError, match="1-2:PRE-RELEASE") as rejection:
        load_network(path, PRE_RELEASE_SETUP)
    message = str(rejection.value)
    assert "historical edition" in message
    # The Active set it is measured against, not a single build constant.
    assert DEFAULT_EDITION in message
    assert set(ACTIVE_EDITIONS) == {DEFAULT_EDITION}


def test_load_network_rejects_a_flag_deviation_the_run_does_not_share(
    tmp_path: Path, monkeypatch
):
    # The case neither of the other two checks can reach: a flag this code can
    # resolve, at a value that is not what this run is playing. Major 3
    # publishes no flags at all (`record.RULE_FLAGS` is empty), so there is no
    # real deviation to exercise this with -- a synthetic flag is injected into
    # the real registry for the duration of the test, the same way
    # `test_record.py` exercises flag resolution generically. The tensors are
    # the same shape either way and the rules differ -- the silent failure the
    # ruleset stamp exists for.
    monkeypatch.setattr(
        "capture_the_flag.record.RULE_FLAGS",
        {
            "SYNTHETIC_FLAG": RuleFlag(
                flag_id="SYNTHETIC_FLAG", values=("off", "on"), default="off"
            )
        },
    )
    path = checkpoint_path(tmp_path, 0)
    trained_under = RulesetConfiguration(DEFAULT_EDITION, {"SYNTHETIC_FLAG": "on"})
    save_checkpoint(small_network(), path, configuration=trained_under)

    raw = torch.load(path, map_location="cpu", weights_only=True)
    assert raw["spec"] == _SPEC  # the spec check cannot see this

    with pytest.raises(ValueError, match="SYNTHETIC_FLAG") as rejection:
        load_network(path, PRE_RELEASE_SETUP)
    message = str(rejection.value)
    # Both sides named: the deviation the file carries, and the run that carries
    # none (the flag sits at its default there, so it renders as absent).
    assert "'on'" in message
    assert "no deviation" in message
    assert "this code implements" in message  # both are fine; this pairing is not


def test_checkpoint_configuration_does_not_compare_against_a_run(
    tmp_path: Path, monkeypatch
):
    # Adoption depends on this: a resume reads the stamp to find out what it is
    # playing, so this entry point has nothing to compare against and must not
    # invent one. It still applies every build-level check.
    monkeypatch.setattr(
        "capture_the_flag.record.RULE_FLAGS",
        {
            "SYNTHETIC_FLAG": RuleFlag(
                flag_id="SYNTHETIC_FLAG", values=("off", "on"), default="off"
            )
        },
    )
    path = checkpoint_path(tmp_path, 0)
    trained_under = RulesetConfiguration(DEFAULT_EDITION, {"SYNTHETIC_FLAG": "on"})
    save_checkpoint(small_network(), path, configuration=trained_under)

    assert checkpoint_configuration(path) == trained_under

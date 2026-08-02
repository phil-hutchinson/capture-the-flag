import pytest
import torch

from capture_the_flag.engines.neural_network.ctf_crn import (
    MAX_FEATURE_COUNT,
    MAX_RESIDUAL_BLOCK_COUNT,
    CtfCrn,
)
from capture_the_flag.engines.neural_network.tensor_layout import TensorLayout
from tests.engines.neural_network.small_networks import (
    BATTLE_TENSOR_LAYOUT,
    SKIRMISH_TENSOR_LAYOUT,
)

_BATCH_SIZE = 2


def _random_input(
    tensor_layout: TensorLayout = BATTLE_TENSOR_LAYOUT, seed=987
) -> torch.Tensor:
    torch.manual_seed(seed)
    return torch.randint(
        0, 2, size=(_BATCH_SIZE, *tensor_layout.input_shape)
    ).float()


def test_ctf_crn_basic_properties() -> None:
    input = _random_input()

    # The one place the default architecture is exercised end to end: everywhere
    # else that only needs *a* network builds a small one.
    crn = CtfCrn(BATTLE_TENSOR_LAYOUT)

    value, policy_logits = crn.forward(input)

    # value head shape and range
    assert value.shape == (_BATCH_SIZE, 1)
    assert ((-1 <= value) & (value <= 1)).all()
    # policy head shape
    assert policy_logits.shape == (_BATCH_SIZE, *BATTLE_TENSOR_LAYOUT.action_space_shape)


@pytest.mark.parametrize(
    "tensor_layout",
    [BATTLE_TENSOR_LAYOUT, SKIRMISH_TENSOR_LAYOUT],
    ids=["battle", "skirmish"],
)
def test_ctf_crn_is_shaped_by_its_tensor_layout(tensor_layout: TensorLayout) -> None:
    # The network's whole I/O shape follows the configured board: a Skirmish
    # network takes an 8x8 input and emits an 8x8 policy, and neither is a
    # constant any more.
    crn = CtfCrn(tensor_layout, feature_count=8, residual_block_count=2)

    value, policy_logits = crn.forward(_random_input(tensor_layout))

    assert crn.tensor_layout == tensor_layout
    assert value.shape == (_BATCH_SIZE, 1)
    assert policy_logits.shape == (_BATCH_SIZE, *tensor_layout.action_space_shape)


def test_ctf_crn_rejects_an_input_shaped_for_another_board() -> None:
    # The value head flattens the board, so a Battle-shaped input meeting a
    # Skirmish network is a shape error rather than a silently wrong evaluation.
    crn = CtfCrn(SKIRMISH_TENSOR_LAYOUT, feature_count=8, residual_block_count=2)

    with pytest.raises(RuntimeError):
        crn.forward(_random_input(BATTLE_TENSOR_LAYOUT))


def test_ctf_crn_honours_requested_width_and_depth() -> None:
    input = _random_input()

    crn = CtfCrn(BATTLE_TENSOR_LAYOUT, feature_count=10, residual_block_count=3)

    # The requested sizes are what the network reports (this is what a checkpoint
    # stamps) and what it is actually built out of...
    assert crn.feature_count == 10
    assert crn.residual_block_count == 3
    # ...including the trunk itself, not just the stem's output width: the first
    # residual convolution's weight is (out_channels, in_channels, 3, 3).
    weights = crn.state_dict()
    block_indices = {key.split(".")[1] for key in weights if key.startswith("_residual_blocks.")}
    assert len(block_indices) == 3
    assert tuple(weights["_residual_blocks.0.0.weight"].shape) == (10, 10, 3, 3)
    # ...and the heads still produce the same contract at any trunk size.
    value, policy_logits = crn.forward(input)
    assert value.shape == (_BATCH_SIZE, 1)
    assert policy_logits.shape == (_BATCH_SIZE, *BATTLE_TENSOR_LAYOUT.action_space_shape)


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"feature_count": 0}, "feature_count"),
        ({"feature_count": -1}, "feature_count"),
        ({"feature_count": MAX_FEATURE_COUNT + 1}, "feature_count"),
        ({"residual_block_count": 0}, "residual_block_count"),
        ({"residual_block_count": MAX_RESIDUAL_BLOCK_COUNT + 1}, "residual_block_count"),
    ],
)
def test_ctf_crn_rejects_out_of_range_architecture(kwargs, expected) -> None:
    # These reach the constructor from a CLI flag and from a checkpoint file, so
    # a value that could only be a typo has to fail here — `residual_block_count=0`
    # would otherwise build a trunkless network that trains and checkpoints
    # perfectly happily, surfacing as an inexplicably weak run rather than an error.
    with pytest.raises(ValueError, match=expected):
        CtfCrn(BATTLE_TENSOR_LAYOUT, **kwargs)


def test_ctf_crn_same_seed_reproducible() -> None:
    input = _random_input()

    torch.manual_seed(123)
    crn_a = CtfCrn(BATTLE_TENSOR_LAYOUT, feature_count=8, residual_block_count=2)
    torch.manual_seed(123)
    crn_b = CtfCrn(BATTLE_TENSOR_LAYOUT, feature_count=8, residual_block_count=2)

    value_a, policy_logits_a = crn_a.forward(input)
    value_b, policy_logits_b = crn_b.forward(input)

    assert torch.equal(value_a, value_b)
    assert torch.equal(policy_logits_a, policy_logits_b)

import torch

from capture_the_flag.board import BOARD_COLUMNS, BOARD_ROWS
from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.tensor_layout import (
    ACTION_SPACE_SHAPE,
    TOTAL_FP_COUNT,
)

_BATCH_SIZE = 2


def _random_input(seed = 987) -> torch.Tensor:
    torch.manual_seed(seed)
    return torch.randint(0, 2, size=(_BATCH_SIZE, TOTAL_FP_COUNT, BOARD_ROWS, BOARD_COLUMNS)).float()


def test_ctf_crn_basic_properties() -> None:
    input = _random_input()

    # The one place the default architecture is exercised end to end: everywhere
    # else that only needs *a* network builds a small one.
    crn = CtfCrn()

    value, policy_logits = crn.forward(input)

    # value head shape and range
    assert value.shape == (_BATCH_SIZE, 1)
    assert ((-1 <= value) & (value <= 1)).all()
    # policy head shape
    assert policy_logits.shape == (_BATCH_SIZE, *ACTION_SPACE_SHAPE)


def test_ctf_crn_honours_requested_width_and_depth() -> None:
    input = _random_input()

    crn = CtfCrn(feature_count=10, residual_block_count=3)

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
    assert policy_logits.shape == (_BATCH_SIZE, *ACTION_SPACE_SHAPE)


def test_ctf_crn_same_seed_reproducible() -> None:
    input = _random_input()

    torch.manual_seed(123)
    crn_a = CtfCrn(feature_count=8, residual_block_count=2)
    torch.manual_seed(123)
    crn_b = CtfCrn(feature_count=8, residual_block_count=2)

    value_a, policy_logits_a = crn_a.forward(input)
    value_b, policy_logits_b = crn_b.forward(input)

    assert torch.equal(value_a, value_b)
    assert torch.equal(policy_logits_a, policy_logits_b)

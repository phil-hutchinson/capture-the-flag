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

    crn = CtfCrn()

    value, policy_logits = crn.forward(input)

    # value head shape and range
    assert value.shape == (_BATCH_SIZE, 1)
    assert ((-1 <= value) & (value <= 1)).all()
    # policy head shape
    assert policy_logits.shape == (_BATCH_SIZE, *ACTION_SPACE_SHAPE)


def test_ctf_crn_same_seed_reproducible() -> None:
    input = _random_input()

    torch.manual_seed(123)
    crn_a = CtfCrn()
    torch.manual_seed(123)
    crn_b = CtfCrn()

    value_a, policy_logits_a = crn_a.forward(input)
    value_b, policy_logits_b = crn_b.forward(input)

    assert torch.equal(value_a, value_b)
    assert torch.equal(policy_logits_a, policy_logits_b)

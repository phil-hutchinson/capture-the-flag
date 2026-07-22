import pytest
import torch
import torch.nn as nn
from torch import Tensor

from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.neural_ctf_player import NeuralCtfPlayer
from capture_the_flag.engines.neural_network.tensor_layout import (
    ACTION_SPACE_SHAPE,
)
from capture_the_flag.engines.neural_network.train import ctf_policy_loss, transform_policy_to_white_perspective
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


def _create_policy_logits_bottom_left(a1a2: float, a1a3: float, b1b2: float, b1b3: float) -> Tensor:
    policy_logits = torch.rand(size=(ACTION_SPACE_SHAPE))
    policy_logits[0, 0, 0] = a1a2
    policy_logits[4, 0, 0] = a1a3
    policy_logits[0, 0, 1] = b1b2
    policy_logits[4, 0, 1] = b1b3
    policy_logits = policy_logits.unsqueeze(0)

    return policy_logits


def test_transform_policy_to_white_perspective_transforms_black():
    position = CtfPosition({}, Side.BLACK, 0)

    policy_orig: dict[str, float] = {
        "A3A4": 3.0,
        "F10H10": 5.0,
    }

    policy_conv = transform_policy_to_white_perspective(position, policy_orig)

    assert len(policy_conv) == 2
    assert "L10L9" in policy_conv
    assert policy_conv["L10L9"] == 3.0
    assert "G3E3" in policy_conv
    assert policy_conv["G3E3"] == 5.0

def test_transform_policy_to_white_perspective_leaves_white_unchanged():
    position = CtfPosition({}, Side.WHITE, 0)

    policy_orig: dict[str, float] = {
        "A3A4": 3.0,
        "F10H10": 5.0,
    }

    policy_conv = transform_policy_to_white_perspective(position, policy_orig)

    assert len(policy_conv) == 2
    assert "A3A4" in policy_conv
    assert policy_conv["A3A4"] == 3.0
    assert "F10H10" in policy_conv
    assert policy_conv["F10H10"] == 5.0

def test_transform_and_loss_pipeline_correct():
    black_position = CtfPosition({}, Side.BLACK, 0)
    black_target: dict[str, float] = {
        "C3C4": 2.5,
        "F10H10": 7.0,
    }
    black_target_conv = transform_policy_to_white_perspective(black_position, black_target)

    white_position = CtfPosition({}, Side.WHITE, 0)
    white_target: dict[str, float] = {
        "J10J9": 2.5,
        "G3E3": 7.0,
    }
    white_target_conv = transform_policy_to_white_perspective(white_position, white_target) # should be nullop


    policy_logits = torch.rand(ACTION_SPACE_SHAPE).unsqueeze(0)

    black_loss = ctf_policy_loss(policy_logits, [black_target_conv])
    white_loss = ctf_policy_loss(policy_logits, [white_target_conv])

    assert black_loss == white_loss


def test_ctf_policy_loss_grows_as_predicted_diverges():
    policy: dict[str, float] = {
        "A1A2": 0.25,
        "A1A3": 0.25,
        "B1B2": 0.25,
        "B1B3": 0.25,
    }

    matching_logits = _create_policy_logits_bottom_left(10, 10, 10, 10)
    loss_matching = ctf_policy_loss(matching_logits, [policy]).item()
    close_logits = _create_policy_logits_bottom_left(12, 11, 9, 8)
    loss_close = ctf_policy_loss(close_logits, [policy]).item()
    far_logits = _create_policy_logits_bottom_left(20, 15, 5, 0)
    loss_far = ctf_policy_loss(far_logits, [policy]).item()

    assert loss_matching < loss_close < loss_far

def test_ctf_policy_loss_means_over_batch():
    policy_1: dict[str, float] = {
        "A1A2": 0.25,
        "F1F3": 0.25,
        "L10K10": 0.25,
        "D6D8": 0.25,
    }
    logits_1 = torch.rand(size=(ACTION_SPACE_SHAPE))
    loss_1 = ctf_policy_loss(logits_1.unsqueeze(0), [policy_1])

    policy_2: dict[str, float] = {
        "A1A2": 0.25,
        "F1F3": 0.25,
        "L10K10": 0.25,
        "D6D8": 0.25,
    }
    logits_2 = torch.rand(size=(ACTION_SPACE_SHAPE))
    loss_2 = ctf_policy_loss(logits_2.unsqueeze(0), [policy_2])

    policy_3: dict[str, float] = {
        "A1A2": 0.25,
        "F1F3": 0.25,
        "L10K10": 0.25,
        "D6D8": 0.25,
    }
    logits_3 = torch.rand(size=(ACTION_SPACE_SHAPE))
    loss_3 = ctf_policy_loss(logits_3.unsqueeze(0), [policy_3])

    grouped_loss = ctf_policy_loss(torch.stack([logits_1, logits_2, logits_3]),[policy_1, policy_2, policy_3])

    assert (loss_1 + loss_2 + loss_3) / 3 == pytest.approx(grouped_loss)
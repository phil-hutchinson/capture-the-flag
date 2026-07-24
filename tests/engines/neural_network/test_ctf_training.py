"""Tests for the single-generation training glue (story 00000009, Step 4).

The overfit-a-batch sanity check: collect one small self-play batch and train
several epochs on it, asserting the loss trends down. Because it spins up real
MCTS self-play plus gradient descent it is `slow`-marked (excluded from the
default run; opt in with `pytest -m slow`).

A falling *policy* loss is the real payload here — it is the end-to-end proof
that the Step-1 str(ply) -> logit column mapping is correct. A flat or rising
policy loss is that mapping's bug signature.
"""

import random

import pytest
import torch
from torch.optim import Adam

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_training import train_one_generation


@pytest.mark.slow
def test_overfits_one_self_play_batch() -> None:
    random.seed(20260723)
    torch.manual_seed(20260723)

    network = CtfCrn()
    optimizer = Adam(network.parameters(), lr=1e-3)

    history = train_one_generation(
        network,
        optimizer,
        n_games=3,
        epochs=40,
        self_play_iterations=15,
        self_play_temperature=1.0,
    )

    # Training many epochs on one fixed batch must reduce the fit error. The
    # policy term carries the signal (value targets are near-constant when games
    # draw), so it is asserted on its own: a non-decreasing policy loss is the
    # Step-1 column-mapping bug signature.
    assert history[-1].total < history[0].total
    assert history[-1].policy < history[0].policy

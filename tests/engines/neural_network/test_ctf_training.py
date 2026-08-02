"""Tests for the single-generation training glue.

The overfit-a-batch sanity check: collect one small self-play batch and train
several epochs on it, asserting the loss trends down. Because it spins up real
MCTS self-play plus gradient descent it is `slow`-marked (excluded from the
default run; opt in with `pytest -m slow`).

A falling *policy* loss is the real payload here — it is the end-to-end proof
that the str(ply) -> logit column mapping is correct. A flat or rising policy
loss is that mapping's bug signature.
"""

import random

import pytest
import torch
from torch.optim import Adam

from capture_the_flag.engines.neural_network.ctf_training import train_one_generation
from tests.engines.neural_network.small_networks import BATTLE_SETUP, small_network


@pytest.mark.slow
def test_overfits_one_self_play_batch() -> None:
    random.seed(20260723)
    torch.manual_seed(20260723)

    # The claim is about the training loop's plumbing, not about capacity, so a
    # small network is used: it still has to fit the batch, and it keeps the
    # opt-in slow run from being dominated by a full-size trunk's gradients.
    network = small_network()
    optimizer = Adam(network.parameters(), lr=1e-3)

    history = train_one_generation(
        network,
        optimizer,
        setup=BATTLE_SETUP,
        n_games=3,
        epochs=40,
        self_play_iterations=15,
        self_play_temperature=1.0,
    )

    # Training many epochs on one fixed batch must reduce the fit error. The
    # policy term carries the signal (value targets are near-constant when games
    # draw), so it is asserted on its own: a non-decreasing policy loss is the
    # column-mapping bug signature.
    assert history[-1].total < history[0].total
    assert history[-1].policy < history[0].policy

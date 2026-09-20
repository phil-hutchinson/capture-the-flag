"""Integration test for the learned-engine player.

Plays one complete match through `play_match` — the production start-position
generation + `StandardGame` wrapper — with an untrained `NeuralCtfPlayer`
against a random opponent, and asserts the game reaches a legal terminal
result with no errors.
This is the first end-to-end exercise of the whole pipeline across a real game:
encode -> network -> decode -> MCTS -> applied plies, driven through the same
seam the runners use.

A whole game of real MCTS search is more than a per-commit test cycle should pay
for, so it is `slow`-marked (excluded from the default run; opt in with
`pytest -m slow`).
"""

import random

import pytest
import torch
from game_engine_core.engines.mcts_engine import MCTSEngine

from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.neural_ctf_player import (
    NeuralCtfPlayer,
    build_neural_player,
)
from capture_the_flag.game_setup import PRE_RELEASE_SETUP
from capture_the_flag.match import play_match
from capture_the_flag.outcome import (
    REASON_ATTRITION,
    REASON_FLAG_CAPTURED,
    REASON_INACTIVITY,
    REASON_MUTUAL_ATTRITION,
)
from capture_the_flag.player import RandomCtfPlayer
from tests.engines.neural_network.small_networks import (
    OTHER_SETUP,
    PRE_RELEASE_TENSOR_LAYOUT,
    small_network,
)

_LEGAL_REASONS = frozenset(
    {REASON_FLAG_CAPTURED, REASON_INACTIVITY, REASON_ATTRITION, REASON_MUTUAL_ATTRITION}
)


@pytest.mark.slow
def test_neural_player_completes_full_match_against_random():
    # Seed the network initialisation and the random opponent so a failure is
    # reproducible; the assertions are on game legality, not on any particular
    # outcome. A small iteration count keeps the match fast — the point is that
    # the player finishes a legal game, not that it plays well (untrained). A
    # small network keeps it that way: a full match is many forward passes, and
    # legality does not depend on the trunk's size.
    torch.manual_seed(0)
    engine = MCTSEngine(
        evaluator=CtfNNEvaluator(small_network(), PRE_RELEASE_TENSOR_LAYOUT),
        iterations=25,
        temperature=0.0,
    )
    neural_player = NeuralCtfPlayer(engine, name="neural")
    random.seed(1234)
    random_player = RandomCtfPlayer(name="random")

    result = play_match(neural_player, random_player, PRE_RELEASE_SETUP).game_result

    # A legal terminal result: a valid outcome, ended for a known reason, with a
    # non-empty log of the plies that were actually applied.
    assert result.outcome in (1, 0, -1)
    assert result.result_reason in _LEGAL_REASONS
    assert len(result.game_log) > 0


def test_a_network_built_for_another_board_cannot_be_seated():
    # Not slow: the refusal happens before any forward pass. Without it the
    # mismatch surfaces as a torch shape error from inside the trunk, which says
    # nothing about which board was wrong.
    pre_release_network = small_network(PRE_RELEASE_TENSOR_LAYOUT)

    with pytest.raises(ValueError, match="simple_64") as rejection:
        build_neural_player("neural", OTHER_SETUP, network=pre_release_network)
    # Both sides named, so the message says which way round the mismatch is.
    assert "test_only_small" in str(rejection.value)


def test_a_network_built_for_this_board_is_seated():
    player = build_neural_player(
        "neural", PRE_RELEASE_SETUP, network=small_network(PRE_RELEASE_TENSOR_LAYOUT)
    )

    assert isinstance(player, NeuralCtfPlayer)

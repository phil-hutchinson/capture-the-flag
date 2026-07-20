"""Integration test for the learned-engine player.

Plays one complete match through `play_match` — the production placement +
`StandardGame` wrapper — with an untrained `NeuralCtfPlayer` against a random
opponent, and asserts the game reaches a legal terminal result with no errors.
This is the first end-to-end exercise of the whole pipeline across a real game:
encode -> network -> decode -> MCTS -> applied plies, driven through the same
seam the runners use.
"""

import random

import torch
from game_engine_core.engines.mcts_engine import MCTSEngine

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.neural_ctf_player import NeuralCtfPlayer
from capture_the_flag.match import play_match
from capture_the_flag.outcome import (
    REASON_FLAG_CAPTURED,
    REASON_INACTIVITY,
    REASON_NO_LEGAL_MOVE,
)
from capture_the_flag.player import RandomCtfPlayer

_LEGAL_REASONS = frozenset(
    {REASON_FLAG_CAPTURED, REASON_INACTIVITY, REASON_NO_LEGAL_MOVE}
)


def test_neural_player_completes_full_match_against_random():
    # Seed the network initialisation and the random opponent so a failure is
    # reproducible; the assertions are on game legality, not on any particular
    # outcome. A small iteration count keeps the match fast — the point is that
    # the player finishes a legal game, not that it plays well (untrained).
    torch.manual_seed(0)
    engine = MCTSEngine(
        evaluator=CtfNNEvaluator(CtfCrn()),
        iterations=25,
        temperature=0.0,
    )
    neural_player = NeuralCtfPlayer(engine, name="neural")
    random_player = RandomCtfPlayer(name="random", rng=random.Random(1234))

    result = play_match(neural_player, random_player).game_result

    # A legal terminal result: a valid outcome, ended for a known reason, with a
    # non-empty log of the plies that were actually applied.
    assert result.outcome in (1, 0, -1)
    assert result.result_reason in _LEGAL_REASONS
    assert len(result.game_log) > 0

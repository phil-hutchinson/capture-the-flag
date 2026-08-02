"""Tests for the self-play random-placement position factory.

`CtfPositionFactory` is the zero-arg `position_factory` the shared
`SelfPlayCollector` calls once per game. It must return
a legal, fully-placed phase-2 starting position, and successive calls must differ
so self-play games actually diverge.

The setup is a constructor argument rather than a default, so each of these runs
against both published ones: a factory that quietly built Battle positions for a
Skirmish run would put the wrong board in front of the encoder.
"""

import pytest

from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.game_setup import GameSetup
from capture_the_flag.pieces import PieceType
from capture_the_flag.side import Side
from tests.engines.neural_network.small_networks import BATTLE_SETUP, SKIRMISH_SETUP

_SETUPS = pytest.mark.parametrize(
    "setup", [BATTLE_SETUP, SKIRMISH_SETUP], ids=["battle", "skirmish"]
)


def _piece_counts(position, side: Side) -> dict[PieceType, int]:
    counts: dict[PieceType, int] = {}
    for occupant_side, piece in position.board.values():
        if occupant_side is side:
            counts[piece] = counts.get(piece, 0) + 1
    return counts


def _squares_of(position, side: Side):
    return {
        square
        for square, (occupant_side, _) in position.board.items()
        if occupant_side is side
    }


@_SETUPS
def test_factory_returns_legal_phase_two_start(setup: GameSetup):
    position = CtfPositionFactory(setup=setup)()

    # White to move, clock reset, and a genuine (non-terminal) start.
    assert position.layout == setup.layout
    assert position.side_to_move is Side.WHITE
    assert position.inactivity_counter == 0
    assert position.outcome is None
    assert position.legal_plies  # White has at least one legal ply


@_SETUPS
def test_factory_places_both_full_armies(setup: GameSetup):
    position = CtfPositionFactory(setup=setup)()

    assert _piece_counts(position, Side.WHITE) == setup.composition.counts
    assert _piece_counts(position, Side.BLACK) == setup.composition.counts


@_SETUPS
def test_factory_keeps_each_side_in_its_home_zone_off_the_lakes(setup: GameSetup):
    position = CtfPositionFactory(setup=setup)()

    assert _squares_of(position, Side.WHITE) <= setup.layout.white_home_squares
    assert _squares_of(position, Side.BLACK) <= setup.layout.black_home_squares
    assert not (position.board.keys() & setup.layout.lake_squares)


@_SETUPS
def test_successive_calls_differ(setup: GameSetup):
    factory = CtfPositionFactory(setup=setup)

    # Two independent draws from an enormous placement space: an identical board
    # is astronomically unlikely, so a match here means the draw is not random.
    assert dict(factory().board) != dict(factory().board)

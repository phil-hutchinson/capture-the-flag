"""Tests for the self-play random-placement position factory.

`CtfPositionFactory` is the zero-arg `position_factory` the shared
`SelfPlayCollector` calls once per game (story 00000009, Step 2). It must return
a legal, fully-placed phase-2 starting position, and successive calls must differ
so self-play games actually diverge.
"""

from capture_the_flag.board import BLACK_HOME_SQUARES, LAKE_SQUARES, WHITE_HOME_SQUARES
from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.pieces import ARMY_ROSTER, PieceType
from capture_the_flag.side import Side


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


def test_factory_returns_legal_phase_two_start():
    position = CtfPositionFactory()()

    # White to move, clock reset, and a genuine (non-terminal) start.
    assert position.side_to_move is Side.WHITE
    assert position.inactivity_counter == 0
    assert position.outcome is None
    assert position.legal_plies  # White has at least one legal ply


def test_factory_places_both_full_armies():
    position = CtfPositionFactory()()

    assert _piece_counts(position, Side.WHITE) == ARMY_ROSTER
    assert _piece_counts(position, Side.BLACK) == ARMY_ROSTER


def test_factory_keeps_each_side_in_its_home_zone_off_the_lakes():
    position = CtfPositionFactory()()

    assert _squares_of(position, Side.WHITE) <= WHITE_HOME_SQUARES
    assert _squares_of(position, Side.BLACK) <= BLACK_HOME_SQUARES
    assert not (position.board.keys() & LAKE_SQUARES)


def test_successive_calls_differ():
    factory = CtfPositionFactory()

    # Two independent draws from ~10^40 placements per side: an identical board
    # is astronomically unlikely, so a match here means the draw is not random.
    assert dict(factory().board) != dict(factory().board)

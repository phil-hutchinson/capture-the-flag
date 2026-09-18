"""Tests for the self-play starting-position factory.

`CtfPositionFactory` is the zero-arg `position_factory` the shared
`SelfPlayCollector` calls once per game. It must return a legal, fully-placed
starting position for the setup it was built with.

Currently a thin wrapper over `match.stub_start_position` — the fixed
placeholder story 00000049 steps 7-8 replace with real generation — so unlike
before major 3, successive calls return the *same* board rather than
independent draws.
"""

from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.pieces import PieceType
from capture_the_flag.side import Side
from tests.engines.neural_network.small_networks import PRE_RELEASE_SETUP


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


def test_factory_returns_legal_start():
    position = CtfPositionFactory(setup=PRE_RELEASE_SETUP)()

    # White to move, clock reset, and a genuine (non-terminal) start.
    assert position.layout == PRE_RELEASE_SETUP.layout
    assert position.side_to_move is Side.WHITE
    assert position.inactivity_counter == 0
    assert position.outcome is None
    assert position.legal_plies  # White has at least one legal ply


def test_factory_places_both_full_armies():
    position = CtfPositionFactory(setup=PRE_RELEASE_SETUP)()

    assert _piece_counts(position, Side.WHITE) == PRE_RELEASE_SETUP.composition.counts
    assert _piece_counts(position, Side.BLACK) == PRE_RELEASE_SETUP.composition.counts


def test_factory_keeps_each_side_in_its_home_zone():
    position = CtfPositionFactory(setup=PRE_RELEASE_SETUP)()

    layout = PRE_RELEASE_SETUP.layout
    assert _squares_of(position, Side.WHITE) <= layout.white_home_squares
    assert _squares_of(position, Side.BLACK) <= layout.black_home_squares


def test_successive_calls_return_the_same_stub_position():
    # Not the eventual contract (story 00000049 steps 7-8 make this a fresh
    # draw each call, the way it always was pre-major-3) -- but it is the
    # correct, honestly-tested behaviour of today's fixed stub.
    factory = CtfPositionFactory(setup=PRE_RELEASE_SETUP)

    assert dict(factory().board) == dict(factory().board)

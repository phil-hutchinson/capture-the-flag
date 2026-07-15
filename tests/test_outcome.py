"""Tests for outcome and endings (rules.md Section 5)."""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.outcome import (
    REASON_FLAG_CAPTURED,
    REASON_INACTIVITY,
    REASON_NO_LEGAL_MOVE,
)
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

# Neutral squares to park each side's Flag in tests that aren't about flag
# capture -- the outcome check for Section 5.1 requires both to be present.
_WHITE_FLAG_SQUARE = Square(11, 1)  # L1
_BLACK_FLAG_SQUARE = Square(11, 12)  # L12


def _position(
    board: dict,
    side_to_move: Side = Side.WHITE,
    inactivity_counter: int = 0,
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=inactivity_counter,
    )


def _ongoing_board() -> dict:
    # Both flags present and each side has a mobile piece with room to move.
    return {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(5, 8): (Side.BLACK, P.FOOT_SOLDIER),
    }


def _boxed_in_white_board() -> dict:
    # White has only immobile pieces (Flag + Tower), so no legal ply.
    return {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(0, 2): (Side.WHITE, P.TOWER),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(5, 8): (Side.BLACK, P.FOOT_SOLDIER),
    }


def test_fresh_ongoing_position_has_no_outcome():
    position = _position(_ongoing_board())
    assert position.outcome is None
    assert position.outcome_reason is None


def test_active_players_own_flag_missing_is_a_loss():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
    }
    position = _position(board, side_to_move=Side.WHITE)
    assert position.outcome == -1


def test_opponents_flag_missing_is_a_win():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        Square(5, 5): (Side.WHITE, P.FOOT_SOLDIER),
    }
    position = _position(board, side_to_move=Side.WHITE)
    assert position.outcome == 1


def test_no_legal_move_is_a_loss():
    position = _position(_boxed_in_white_board(), side_to_move=Side.WHITE)
    assert position.legal_plies == ()
    assert position.outcome == -1


def test_inactivity_at_limit_is_a_draw():
    position = _position(_ongoing_board(), inactivity_counter=50)
    assert position.outcome == 0


def test_inactivity_draw_is_side_independent():
    # The shared counter draws for whoever is to move.
    white = _position(_ongoing_board(), side_to_move=Side.WHITE, inactivity_counter=50)
    black = _position(_ongoing_board(), side_to_move=Side.BLACK, inactivity_counter=50)
    assert white.outcome == 0
    assert black.outcome == 0


def test_inactivity_draw_precedes_active_no_legal_move():
    # White is boxed in, but the shared counter already hit its limit on Black's
    # previous ply -- the game ended in a draw before White's turn begins, rather
    # than as a White loss for having no legal move.
    position = _position(
        _boxed_in_white_board(), side_to_move=Side.WHITE, inactivity_counter=50
    )
    assert position.legal_plies == ()  # White really is boxed in
    assert position.outcome == 0


def test_below_inactivity_limit_is_still_ongoing():
    position = _position(_ongoing_board(), inactivity_counter=49)
    assert position.outcome is None


# --- outcome_reason (game-engine-core GamePosition.outcome_reason) ------------
#
# Each ending reports a label from `outcome.py`'s reason vocabulary, sharing its
# branch logic with `outcome` so the two can never disagree.


def test_ongoing_position_has_no_reason():
    position = _position(_ongoing_board())
    assert position.outcome_reason is None


def test_flag_capture_reason():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
    }
    position = _position(board, side_to_move=Side.WHITE)  # White's flag missing.
    assert position.outcome_reason == REASON_FLAG_CAPTURED


def test_no_legal_move_reason():
    position = _position(_boxed_in_white_board(), side_to_move=Side.WHITE)
    assert position.legal_plies == ()
    assert position.outcome_reason == REASON_NO_LEGAL_MOVE


def test_inactivity_reason():
    position = _position(_ongoing_board(), inactivity_counter=50)
    assert position.outcome_reason == REASON_INACTIVITY

"""Tests for outcome and endings (rules.md Section 5)."""

from types import MappingProxyType

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.outcome import (
    REASON_ATTRITION,
    REASON_FLAG_CAPTURED,
    REASON_INACTIVITY,
    REASON_MUTUAL_ATTRITION,
)
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

# Neutral squares to park each side's Flag in tests that aren't about flag
# capture -- the outcome check for Section 5.1 requires both to be present.
_WHITE_FLAG_SQUARE = Square(7, 1)  # H1
_BLACK_FLAG_SQUARE = Square(7, 8)  # H8


def _position(
    board: dict,
    side_to_move: Side = Side.WHITE,
    inactivity_counter: int = 0,
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=inactivity_counter,
        layout=SIMPLE_64,
        ply_count=0,
    )


def _ongoing_board() -> dict:
    # Both flags present and each side has a mobile piece with room to move.
    return {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(5, 8): (Side.BLACK, P.FOOT_SOLDIER),
    }


def _white_attrition_board() -> dict:
    # White holds nothing but its Flag -- no numbered pieces, an immediate
    # loss for White regardless of whose turn it is (rules.md Section 5.2).
    return {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(5, 8): (Side.BLACK, P.FOOT_SOLDIER),
    }


def _mutual_attrition_board() -> dict:
    # Neither side has a numbered piece left, as if a single ply had just
    # traded off each side's last piece at once (rules.md Section 5.3).
    return {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
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


def test_attrition_is_a_loss_for_the_side_with_no_army():
    white_to_move = _position(_white_attrition_board(), side_to_move=Side.WHITE)
    assert white_to_move.outcome == -1

    black_to_move = _position(_white_attrition_board(), side_to_move=Side.BLACK)
    assert black_to_move.outcome == 1  # Black's opponent has no army


def test_mutual_attrition_is_a_draw():
    position = _position(_mutual_attrition_board())
    assert position.outcome == 0


def test_mutual_attrition_precedes_single_sided_attrition():
    # Both the mutual case and the single-sided case are satisfied by this
    # board; the mutual check runs first, so the result is a draw rather than
    # a win for whichever side happens to be "active".
    for side in (Side.WHITE, Side.BLACK):
        position = _position(_mutual_attrition_board(), side_to_move=side)
        assert position.outcome == 0


def test_attrition_precedes_inactivity():
    # Even with the inactivity counter also at its limit, an emptied army
    # reports as attrition.
    position = _position(
        _white_attrition_board(), side_to_move=Side.WHITE, inactivity_counter=50
    )
    assert position.outcome == -1
    assert position.outcome_reason == REASON_ATTRITION


def test_inactivity_at_limit_is_a_draw():
    position = _position(_ongoing_board(), inactivity_counter=50)
    assert position.outcome == 0


def test_inactivity_draw_is_side_independent():
    # The shared counter draws for whoever is to move.
    white = _position(_ongoing_board(), side_to_move=Side.WHITE, inactivity_counter=50)
    black = _position(_ongoing_board(), side_to_move=Side.BLACK, inactivity_counter=50)
    assert white.outcome == 0
    assert black.outcome == 0


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


def test_attrition_reason():
    position = _position(_white_attrition_board(), side_to_move=Side.WHITE)
    assert position.outcome_reason == REASON_ATTRITION


def test_mutual_attrition_reason():
    position = _position(_mutual_attrition_board())
    assert position.outcome_reason == REASON_MUTUAL_ATTRITION


def test_inactivity_reason():
    position = _position(_ongoing_board(), inactivity_counter=50)
    assert position.outcome_reason == REASON_INACTIVITY

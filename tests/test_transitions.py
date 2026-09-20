"""Tests for apply_ply: board transitions, rank reduction, and the inactivity
clock (rules.md Section 4.3, "Rank reduction" and Section 5.3).
"""

from types import MappingProxyType

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


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


def test_plain_move_updates_board_side_and_clock():
    board = {Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)}
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER)}
    assert new_position.side_to_move is Side.BLACK
    assert new_position.inactivity_counter == 6  # non-attack: +1


def test_winning_attack_resets_the_clock_and_reduces_the_attacker():
    # The higher-numbered rank wins (story 00000049 step 14), and the
    # surviving attacker is reduced by one rank (step 15): a winning
    # Master-of-Arms (5) stands on the destination as a Champion (4).
    board = {
        Square(3, 2): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(3, 3): (Side.BLACK, P.PEASANT),
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.CHAMPION)}
    assert new_position.inactivity_counter == 0  # attack: reset


def test_flag_capture_does_not_reduce_the_capturing_piece():
    # Capturing the Flag is not combat (rules.md Section 4.3), so the
    # attacker keeps its rank -- unlike an ordinary winning attack.
    board = {
        Square(3, 2): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(3, 3): (Side.BLACK, P.FLAG),
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.MASTER_OF_ARMS)}
    assert new_position.inactivity_counter == 0  # attack: reset


def test_mutual_loss_resets_the_clock_and_reduces_nothing():
    # A draw leaves no survivor, so there is nothing left to reduce.
    board = {
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(3, 3): (Side.BLACK, P.MILITIA),  # same rank -> mutual loss
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {}
    assert new_position.inactivity_counter == 0  # attack: reset


def test_complete_sacrifice_resets_the_clock_and_reduces_the_defender():
    # The attacker loses cleanly and is removed; the surviving defender is
    # reduced in place by one rank.
    board = {
        Square(3, 2): (Side.WHITE, P.PEASANT),
        Square(3, 3): (Side.BLACK, P.MASTER_OF_ARMS),  # attacker loses cleanly
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.BLACK, P.CHAMPION)}
    assert new_position.inactivity_counter == 0  # attack (even losing): reset


def test_clock_accumulates_across_consecutive_non_attacks():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 7): (Side.BLACK, P.FOOT_SOLDIER),
    }
    position = _position(board, inactivity_counter=10)

    after_white = position.apply_ply(CtfPly(Square(3, 2), Square(3, 3)))
    assert after_white.inactivity_counter == 11
    assert after_white.side_to_move is Side.BLACK

    after_black = after_white.apply_ply(CtfPly(Square(4, 7), Square(4, 6)))
    assert after_black.inactivity_counter == 12

"""Tests for apply_ply: board transitions and the inactivity clock
(rules.md Sections 4.3, 5.3).
"""

from types import MappingProxyType

from capture_the_flag.board import Square
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
    )


def test_plain_move_updates_board_side_and_clock():
    board = {Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)}
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER)}
    assert new_position.side_to_move is Side.BLACK
    assert new_position.inactivity_counter == 6  # non-attack: +1


def test_winning_attack_resets_the_clock():
    board = {
        Square(3, 2): (Side.WHITE, P.CHAMPION),
        Square(3, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.CHAMPION)}
    assert new_position.inactivity_counter == 0  # attack: reset


def test_mutual_loss_resets_the_clock():
    board = {
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(3, 3): (Side.BLACK, P.MILITIA),  # same rank -> mutual loss
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {}
    assert new_position.inactivity_counter == 0  # attack: reset


def test_complete_sacrifice_resets_the_clock():
    board = {
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(3, 3): (Side.BLACK, P.MASTER_OF_ARMS),  # attacker loses cleanly
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.BLACK, P.MASTER_OF_ARMS)}
    assert new_position.inactivity_counter == 0  # attack (even losing): reset


def test_tower_destruction_resets_the_clock():
    board = {
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(3, 3): (Side.BLACK, P.TOWER),  # any attack -> mutual loss
    }
    position = _position(board, inactivity_counter=5)
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {}
    assert new_position.inactivity_counter == 0  # tower destruction: reset


def test_clock_accumulates_across_consecutive_non_attacks():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(8, 11): (Side.BLACK, P.FOOT_SOLDIER),
    }
    position = _position(board, inactivity_counter=10)

    after_white = position.apply_ply(CtfPly(Square(3, 2), Square(3, 3)))
    assert after_white.inactivity_counter == 11
    assert after_white.side_to_move is Side.BLACK

    after_black = after_white.apply_ply(CtfPly(Square(8, 11), Square(8, 10)))
    assert after_black.inactivity_counter == 12

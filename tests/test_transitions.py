"""Tests for apply_ply: transitions, clocks, and the breachability cache
(rules.md Sections 4.3, 6.4, 6.5).
"""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.breachability import BreachabilityCache
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.reachability import compute_breachability
from capture_the_flag.side import Side

_SENTINEL_BREACHABILITY = BreachabilityCache(
    white_flag_enclosed=True,
    black_flag_enclosed=True,
    white_sappers_available=True,
    black_sappers_available=True,
)


def _position(
    board: dict,
    side_to_move: Side = Side.WHITE,
    white_inactivity_counter: int = 0,
    black_inactivity_counter: int = 0,
    progress_counter: int = 0,
    breachability: BreachabilityCache | None = _SENTINEL_BREACHABILITY,
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        white_inactivity_counter=white_inactivity_counter,
        black_inactivity_counter=black_inactivity_counter,
        progress_counter=progress_counter,
        breachability=breachability,
    )


def test_plain_move_updates_board_side_and_clocks():
    board = {Square(3, 2): (Side.WHITE, P.INFANTRY)}
    position = _position(
        board, white_inactivity_counter=5, black_inactivity_counter=7, progress_counter=10
    )
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.INFANTRY)}
    assert new_position.side_to_move is Side.BLACK
    assert new_position.white_inactivity_counter == 6  # non-attack: +1
    assert new_position.black_inactivity_counter == 7  # unaffected
    assert new_position.progress_counter == 11  # no capture: +1
    assert new_position.breachability == _SENTINEL_BREACHABILITY  # carried forward


def test_winning_attack_resets_movers_clock_and_progress():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(
        board, white_inactivity_counter=5, black_inactivity_counter=7, progress_counter=10
    )
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.WHITE, P.INFANTRY)}
    assert new_position.white_inactivity_counter == 0  # attack: reset
    assert new_position.black_inactivity_counter == 7  # not a sacrifice: unaffected
    assert new_position.progress_counter == 0  # capture: reset


def test_mutual_loss_resets_both_clocks_and_progress():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.INFANTRY),  # same rank -> mutual loss
    }
    position = _position(
        board, white_inactivity_counter=5, black_inactivity_counter=7, progress_counter=10
    )
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {}
    assert new_position.white_inactivity_counter == 0  # attack: reset
    assert new_position.black_inactivity_counter == 0  # mover's sacrifice: reset
    assert new_position.progress_counter == 0  # capture: reset


def test_complete_sacrifice_resets_both_clocks_but_not_progress():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.LORD_MARSHAL),  # attacker loses cleanly
    }
    position = _position(
        board, white_inactivity_counter=5, black_inactivity_counter=7, progress_counter=10
    )
    ply = CtfPly(Square(3, 2), Square(3, 3))

    new_position = position.apply_ply(ply)

    assert new_position.board == {Square(3, 3): (Side.BLACK, P.LORD_MARSHAL)}
    assert new_position.white_inactivity_counter == 0  # attack (even losing): reset
    assert new_position.black_inactivity_counter == 0  # opponent's sacrifice: reset
    assert new_position.progress_counter == 11  # complete sacrifice: no capture, +1


def test_opponents_clock_reset_carries_into_their_next_non_attack_move():
    # White makes a complete sacrifice, resetting Black's clock to 0; Black's
    # very next (non-attacking) ply should increment from that reset value,
    # not from whatever it held before.
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.LORD_MARSHAL),
    }
    position = _position(board, black_inactivity_counter=20)
    after_sacrifice = position.apply_ply(CtfPly(Square(3, 2), Square(3, 3)))
    assert after_sacrifice.black_inactivity_counter == 0
    assert after_sacrifice.side_to_move is Side.BLACK

    after_black_move = after_sacrifice.apply_ply(CtfPly(Square(3, 3), Square(3, 4)))
    assert after_black_move.black_inactivity_counter == 1


def test_breachability_carried_forward_on_non_tower_sapper_ply():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    new_position = position.apply_ply(CtfPly(Square(3, 2), Square(3, 3)))
    assert new_position.breachability == _SENTINEL_BREACHABILITY


def test_breachability_recomputed_when_a_tower_is_destroyed():
    # A1 is White's Flag, fully sealed by White Towers at A2 and B1 (a
    # board corner has only those two orthogonal neighbours).
    flag = Square(0, 1)
    tower_a2 = Square(0, 2)
    tower_b1 = Square(1, 1)
    sapper = Square(0, 3)  # Black Sapper, adjacent to the A2 Tower
    black_flag = Square(11, 12)  # irrelevant to this check, just needs to exist
    board = {
        flag: (Side.WHITE, P.FLAG),
        tower_a2: (Side.WHITE, P.TOWER),
        tower_b1: (Side.WHITE, P.TOWER),
        sapper: (Side.BLACK, P.SAPPER),
        black_flag: (Side.BLACK, P.FLAG),
    }
    position = _position(board, side_to_move=Side.BLACK)

    # Sanity check: with both walls intact, White's Flag really is enclosed.
    assert compute_breachability(board).white_flag_enclosed is True

    new_position = position.apply_ply(CtfPly(sapper, tower_a2))

    assert new_position.breachability != _SENTINEL_BREACHABILITY
    expected = compute_breachability(new_position.board)
    assert new_position.breachability == expected
    assert expected.white_flag_enclosed is False


def test_breachability_recomputed_when_a_sapper_is_captured():
    white_flag = Square(11, 1)
    black_flag = Square(11, 12)
    board = {
        white_flag: (Side.WHITE, P.FLAG),
        black_flag: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.BLACK, P.SAPPER),
        Square(3, 3): (Side.WHITE, P.LORD_MARSHAL),  # wins, capturing the Sapper
    }
    position = _position(board, side_to_move=Side.WHITE)

    new_position = position.apply_ply(CtfPly(Square(3, 3), Square(3, 2)))

    assert new_position.breachability != _SENTINEL_BREACHABILITY
    expected = compute_breachability(new_position.board)
    assert new_position.breachability == expected

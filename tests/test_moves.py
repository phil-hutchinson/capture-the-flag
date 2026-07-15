"""Tests for legal move generation (rules.md Section 4.2)."""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


def _position(board: dict, side_to_move: Side = Side.WHITE) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        white_inactivity_counter=0,
        black_inactivity_counter=0,
        progress_counter=0,
    )


def _ply_strings(position: CtfPosition) -> set[str]:
    return {str(ply) for ply in position.legal_plies}


def _own_plies(position: CtfPosition, prefix: str) -> set[str]:
    return {s for s in _ply_strings(position) if s.startswith(prefix)}


def test_unencumbered_piece_moves_one_or_two_squares_orthogonally():
    # D2 is deep in White's home zone (rows 1-4) with no enemy nearby, so it is
    # unencumbered and may step one or two squares in every clear direction.
    position = _position({Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)})
    assert _ply_strings(position) == {
        "D2D3",
        "D2D4",  # two squares north
        "D2D1",  # one square south (row 0 is off-board)
        "D2E2",
        "D2F2",  # two squares east
        "D2C2",
        "D2B2",  # two squares west
    }


def test_two_square_move_needs_a_clear_intermediate_square():
    # A friendly piece at D3 blocks the north direction entirely (it never
    # causes encumbrance -- only enemies do -- so D2 stays unencumbered).
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(3, 3): (Side.WHITE, P.MILITIA),
    }
    position = _position(board)
    north = {s for s in _own_plies(position, "D2") if s in {"D2D3", "D2D4"}}
    assert north == set()  # neither the blocked step nor the hop past it
    assert {"D2E2", "D2F2"} <= _own_plies(position, "D2")  # other directions open


def test_encumbered_piece_is_limited_to_one_square():
    # A diagonally-adjacent enemy at E3 encumbers D2 without blocking any
    # orthogonal step, so every legal move is a single square.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {"D2D3", "D2D1", "D2E2", "D2C2"}


def test_encumbered_piece_can_still_attack_an_adjacent_enemy():
    # An orthogonally-adjacent enemy both encumbers the piece and is attackable.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(3, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {"D2D3", "D2D1", "D2E2", "D2C2"}


def test_unencumbered_two_square_attack_at_distance_two():
    # An enemy two squares north (E-W/N-S distance 2, so outside the eight
    # surrounding squares) leaves D2 unencumbered; the empty D3 in between lets
    # it attack at distance two.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(3, 4): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    strings = _own_plies(position, "D2")
    assert "D2D3" in strings  # step onto the empty intermediate square
    assert "D2D4" in strings  # attack the enemy at distance two


def test_sacrificial_attack_is_legal_regardless_of_rank():
    # A lowly Militia may attack the Master-of-Arms even though it will lose.
    board = {
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(3, 3): (Side.BLACK, P.MASTER_OF_ARMS),
    }
    position = _position(board)
    assert "D2D3" in _ply_strings(position)


def test_immobile_pieces_have_no_plies():
    board = {
        Square(5, 5): (Side.WHITE, P.TOWER),
        Square(0, 1): (Side.WHITE, P.FLAG),
    }
    position = _position(board)
    assert position.legal_plies == ()


def test_movement_blocked_and_bounded_by_a_lake():
    # Column F (index 5) is a lake column in both lake rows (6, 7): F5 cannot
    # move north at all, but south and sideways remain open.
    position = _position({Square(5, 5): (Side.WHITE, P.FOOT_SOLDIER)})
    strings = _own_plies(position, "F5")
    assert "F5F6" not in strings
    assert "F5F7" not in strings
    assert "F5F4" in strings  # one square south
    assert "F5F3" in strings  # two squares south (unencumbered)
    assert "F5G5" in strings


def test_all_ply_strings_distinct_in_a_dense_position():
    # A spread of White pieces with a couple of enemies mixed in: every ply
    # string must be unique (no piece generates a duplicate destination).
    board = {
        Square(1, 2): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(4, 3): (Side.WHITE, P.CHAMPION),
        Square(7, 2): (Side.WHITE, P.KNIGHT),
        Square(9, 4): (Side.WHITE, P.HALBERDIER),
        Square(2, 4): (Side.WHITE, P.FOOT_SOLDIER),
        Square(6, 5): (Side.BLACK, P.MILITIA),
        Square(10, 5): (Side.BLACK, P.KNIGHT),
    }
    position = _position(board)
    strings = [str(ply) for ply in position.legal_plies]
    assert len(strings) == len(set(strings))
    assert len(strings) > 0

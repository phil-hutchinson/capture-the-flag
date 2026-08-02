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
        inactivity_counter=0,
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
    # orthogonal step, so every legal move is a single square -- including the
    # diagonal attack on the piece doing the encumbering, which is itself one
    # square.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {"D2D3", "D2D1", "D2E2", "D2C2", "D2E3"}


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
    # Each immobile piece has an enemy on its diagonal, so this also pins down
    # that the diagonal is a direction a *mover* gains, not one that gives a
    # Tower or the Flag something to do.
    board = {
        Square(5, 5): (Side.WHITE, P.TOWER),
        Square(4, 4): (Side.BLACK, P.MILITIA),
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(1, 2): (Side.BLACK, P.KNIGHT),
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


def test_diagonal_attack_available_in_all_four_directions():
    # Enemies on every diagonal of D3. Each is attackable, and each encumbers
    # D3, so the orthogonal steps are one square apiece.
    board = {
        Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER),
        Square(2, 2): (Side.BLACK, P.MILITIA),
        Square(4, 2): (Side.BLACK, P.MILITIA),
        Square(2, 4): (Side.BLACK, P.MILITIA),
        Square(4, 4): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D3") == {
        "D3D4",
        "D3D2",
        "D3E3",
        "D3C3",
        "D3C2",  # the four diagonal attacks
        "D3E2",
        "D3C4",
        "D3E4",
    }


def test_no_diagonal_move_onto_an_empty_square():
    # C4 and E4 are empty, so neither is a destination: the diagonal is an
    # attacking direction and nothing else.
    position = _position({Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER)})
    strings = _own_plies(position, "D3")
    assert "D3C4" not in strings
    assert "D3E4" not in strings
    assert "D3C2" not in strings
    assert "D3E2" not in strings


def test_towers_and_the_flag_cannot_be_attacked_diagonally():
    # A Tower on E4 and the enemy Flag on C4 both encumber D3 -- so the
    # orthogonal steps shorten to one square -- but neither is a legal diagonal
    # target. This is what leaves the Flag capturable only from an orthogonally
    # adjacent square (rules.md Section 5.1).
    board = {
        Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 4): (Side.BLACK, P.TOWER),
        Square(2, 4): (Side.BLACK, P.FLAG),
    }
    position = _position(board)
    assert _own_plies(position, "D3") == {"D3D4", "D3D2", "D3E3", "D3C3"}


def test_unencumbered_bonus_never_extends_a_diagonal():
    # F5 is two squares diagonally from D3 -- outside the eight surrounding
    # squares, so D3 is unencumbered and does get its two-square orthogonal
    # moves. It gets no two-square diagonal, because there is no such thing.
    board = {
        Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER),
        Square(5, 5): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    strings = _own_plies(position, "D3")
    assert "D3D5" in strings  # the two-square orthogonal bonus is in play
    assert "D3F5" not in strings  # but never on the diagonal
    assert "D3E4" not in strings  # nor a step towards it onto an empty square


def test_diagonal_attack_past_a_lake_corner():
    # B6 is a lake, A6 and B5 are not. A one-square diagonal has no intermediate
    # square to clear, so only the attacked square itself must be open: the
    # attack skirts the lake corner and is legal (rules.md Section 4.3).
    board = {
        Square(0, 6): (Side.WHITE, P.FOOT_SOLDIER),
        Square(1, 5): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert "A6B5" in _own_plies(position, "A6")


def test_diagonal_sacrificial_attack_is_legal():
    # Relative strength never restricts an attack, on the diagonal as anywhere
    # else: the Militia may throw itself at a Master-of-Arms.
    board = {
        Square(3, 3): (Side.WHITE, P.MILITIA),
        Square(4, 4): (Side.BLACK, P.MASTER_OF_ARMS),
    }
    position = _position(board)
    assert "D3E4" in _own_plies(position, "D3")


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

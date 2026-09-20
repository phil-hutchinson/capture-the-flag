"""Tests for legal move generation (rules.md Section 4.2)."""

from types import MappingProxyType

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


def _position(
    board: dict, side_to_move: Side = Side.WHITE, ply_count: int = 1
) -> CtfPosition:
    # `ply_count` defaults non-zero: these tests exercise ordinary movement,
    # not the game's first ply (story 00000049 step 11), which is covered
    # separately by `test_first_ply_is_limited_to_one_square`.
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=0,
        layout=SIMPLE_64,
        ply_count=ply_count,
    )


def _ply_strings(position: CtfPosition) -> set[str]:
    return {str(ply) for ply in position.legal_plies}


def _own_plies(position: CtfPosition, prefix: str) -> set[str]:
    return {s for s in _ply_strings(position) if s.startswith(prefix)}


def test_unencumbered_piece_moves_one_or_two_squares_orthogonally():
    # D2 is in White's home zone (rows 1-2) with no enemy nearby, so it is
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


def test_first_ply_is_limited_to_one_square():
    # The game's first ply (ply_count == 0) drops the two-square bonus even for
    # an otherwise-unencumbered piece; the same board at a later ply is
    # unaffected (story 00000049 step 11).
    board = {Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)}
    first_ply = _position(board, ply_count=0)
    later_ply = _position(board, ply_count=1)

    assert _ply_strings(first_ply) == {"D2D3", "D2D1", "D2E2", "D2C2"}
    assert {"D2D4", "D2F2", "D2B2"} <= _ply_strings(later_ply)


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


def test_enemy_behind_does_not_encumber_the_forward_direction():
    # An enemy due south of D2 (behind it, travelling north) does not encumber
    # the northward direction -- only west, east and south, of which south is
    # already capped at one square by the board edge (story 00000049 step 12).
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(3, 1): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {"D2D3", "D2D4", "D2D1", "D2E2", "D2C2"}


def test_enemy_diagonally_ahead_removes_only_the_two_square_moves_it_touches():
    # An enemy at E3 -- north-east of D2 -- sits among the five squares ahead of
    # or beside D2 for *both* the northward and eastward directions, so those two
    # lose their two-square bonus while west (unaffected) keeps it.
    # `D2D1` is the one-square southward step (row 0 is off-board, so south
    # never had a two-square option to lose).
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 3): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {
        "D2D3",
        "D2D1",
        "D2E2",
        "D2C2",
        "D2B2",  # west stays unencumbered
        "D2E3",  # the diagonal attack on the encumbering piece itself
    }


def test_piece_unencumbered_one_way_and_encumbered_another():
    # An enemy immediately west of D2, at C2, is one of the two "beside"
    # squares for both a northward- and a southward-travelling piece, and is
    # also the "ahead" square for westward travel itself -- so it encumbers
    # north, south and west. Eastward travel does not have C2 among its five
    # squares, and so keeps its two-square move.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(2, 2): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert _own_plies(position, "D2") == {
        "D2D3",  # north is capped at one square
        "D2D1",  # south (already capped by the board edge)
        "D2E2",
        "D2F2",  # east keeps its two-square move
        "D2C2",  # west is capped at one square -- and is the attack itself
    }


def test_encumbered_piece_can_still_attack_an_adjacent_enemy():
    # An enemy directly ahead at D3 is attackable, and is one of the five
    # squares for north, east and west alike, so all three are capped at one
    # square; south is untouched but was already capped by the board edge.
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
    # The Flag has an enemy on its diagonal, which also pins down that the
    # diagonal is a direction a *mover* gains, not one that gives the Flag
    # something to do.
    board = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(1, 2): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    assert position.legal_plies == ()


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


def test_flag_is_attackable_diagonally():
    # The movable-target restriction is gone (story 00000049 step 13): the
    # Flag has no immunity to diagonal attack, and D3C4 has an open path (both
    # of its flanking squares, C3 and D4, are empty). C4 -- north-west of D3 --
    # also encumbers only north and west, capping each at one square; south and
    # east are untouched and keep their two-square move.
    board = {
        Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER),
        Square(2, 4): (Side.BLACK, P.FLAG),
    }
    position = _position(board)
    assert _own_plies(position, "D3") == {
        "D3D4",  # north capped at one square
        "D3D2",
        "D3D1",  # south keeps its two-square move
        "D3E3",
        "D3F3",  # east keeps its two-square move
        "D3C3",  # west capped at one square
        "D3C4",  # the diagonal attack on the Flag itself
    }


def test_diagonal_attack_needs_an_open_path():
    # C3 attacking D4 (rules.md Section 4.4's worked example): legal so long as
    # at least one of the two flanking squares, C4 and D3, is empty -- and
    # illegal once both are occupied, even by friendly pieces.
    base = {
        Square(2, 3): (Side.WHITE, P.FOOT_SOLDIER),  # C3, the attacker
        Square(3, 4): (Side.BLACK, P.MILITIA),  # D4, the target
    }

    c4_occupied = dict(base)
    c4_occupied[Square(2, 4)] = (Side.BLACK, P.MILITIA)  # C4 occupied, D3 empty
    assert "C3D4" in _own_plies(_position(c4_occupied), "C3")

    d3_occupied = dict(base)
    d3_occupied[Square(3, 3)] = (Side.WHITE, P.MILITIA)  # D3 occupied, C4 empty
    assert "C3D4" in _own_plies(_position(d3_occupied), "C3")

    both_occupied = dict(base)
    both_occupied[Square(2, 4)] = (Side.WHITE, P.MILITIA)  # friendly C4
    both_occupied[Square(3, 3)] = (Side.WHITE, P.MILITIA)  # friendly D3
    assert "C3D4" not in _own_plies(_position(both_occupied), "C3")


def test_unencumbered_bonus_never_extends_a_diagonal():
    # F5 is two squares diagonally from D3 -- outside every direction's five
    # squares -- so D3 is unencumbered in all four and does get its two-square
    # orthogonal moves. It gets no two-square diagonal, because there is no
    # such thing.
    board = {
        Square(3, 3): (Side.WHITE, P.FOOT_SOLDIER),
        Square(5, 5): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    strings = _own_plies(position, "D3")
    assert "D3D5" in strings  # the two-square orthogonal bonus is in play
    assert "D3F5" not in strings  # but never on the diagonal
    assert "D3E4" not in strings  # nor a step towards it onto an empty square


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
        Square(6, 2): (Side.WHITE, P.PEASANT),
        Square(6, 4): (Side.WHITE, P.MILITIA),
        Square(2, 4): (Side.WHITE, P.FOOT_SOLDIER),
        Square(6, 5): (Side.BLACK, P.MILITIA),
        Square(7, 5): (Side.BLACK, P.PEASANT),
    }
    position = _position(board)
    strings = [str(ply) for ply in position.legal_plies]
    assert len(strings) == len(set(strings))
    assert len(strings) > 0

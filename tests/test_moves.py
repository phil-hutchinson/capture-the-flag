"""Tests for legal move generation (rules.md Section 4.2)."""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.placement import assemble_position, random_placement
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


def test_baseline_piece_moves_to_all_open_orthogonal_neighbors():
    # D2 is deep in White's home zone (rows 1-4): no lakes anywhere near it.
    position = _position({Square(3, 2): (Side.WHITE, P.INFANTRY)})
    assert _ply_strings(position) == {"D2D3", "D2D1", "D2E2", "D2C2"}


def test_baseline_piece_blocked_by_friendly_and_can_attack_enemy():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.WHITE, P.MILITIA),  # friendly: blocks north
        Square(3, 1): (Side.BLACK, P.MILITIA),  # enemy: attackable south
    }
    position = _position(board)
    # The friendly Militia at D3 is also White's to move and contributes its
    # own plies, so restrict the check to the Infantry's own moves (D2...).
    infantry_plies = {s for s in _ply_strings(position) if s.startswith("D2")}
    assert infantry_plies == {"D2D1", "D2E2", "D2C2"}


def test_sacrificial_attack_is_legal_regardless_of_rank():
    # A lowly Infantry may attack the Lord Marshal even though it will lose.
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(3, 3): (Side.BLACK, P.LORD_MARSHAL),
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


def test_knight_baseline_step_and_charge():
    # Column D (index 3) is open in both lake rows, so a vertical charge has
    # a clear line all the way from row 5 to row 8.
    board = {
        Square(3, 5): (Side.WHITE, P.KNIGHT),
        Square(3, 8): (Side.BLACK, P.MILITIA),  # 3 squares north, clear line
    }
    position = _position(board)
    strings = _ply_strings(position)
    # Only the Knight is White's to move, so the exact set is expected.
    assert strings == {
        "D5D6",  # 1-square step north (not a charge)
        "D5D8",  # 3-square charge landing on the enemy
        "D5D4",  # 1-square step south
        "D5E5",  # 1-square step east
        "D5C5",  # 1-square step west
    }
    # D5D7 (a 2-square hop onto the empty square in between) must be absent:
    # a Knight's multi-square move is only legal when it ends in an attack.
    assert "D5D7" not in strings


def test_knight_non_attacking_move_limited_to_one_square():
    # Nothing at distance 2/3 north, so those squares must NOT appear as
    # non-attack "moves" -- a Knight's multi-square move is attack-only.
    board = {Square(3, 5): (Side.WHITE, P.KNIGHT)}
    position = _position(board)
    strings = _ply_strings(position)
    assert "D5D6" in strings
    assert "D5D7" not in strings
    assert "D5D8" not in strings


def test_knight_charge_forbidden_against_halberdier_but_adjacent_attack_allowed():
    board = {
        Square(3, 5): (Side.WHITE, P.KNIGHT),
        Square(3, 7): (Side.BLACK, P.HALBERDIER),  # 2-square charge target
        Square(3, 4): (Side.BLACK, P.HALBERDIER),  # adjacent attack target
    }
    position = _position(board)
    strings = _ply_strings(position)
    assert "D5D7" not in strings  # charge vs. Halberdier: forbidden
    assert "D5D4" in strings  # adjacent attack vs. Halberdier: allowed


def test_knight_charge_blocked_by_intervening_piece():
    board = {
        Square(3, 5): (Side.WHITE, P.KNIGHT),
        Square(3, 6): (Side.WHITE, P.MILITIA),  # friendly blocks the line
        Square(3, 7): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    strings = _ply_strings(position)
    assert "D5D6" not in strings  # friendly-occupied: no move onto it
    assert "D5D7" not in strings  # and the charge cannot pass through it


def test_knight_charge_blocked_by_lake():
    # Column F (index 5) is a lake column in both lake rows (6, 7), so
    # anything north of F5 is unreachable; south (F4) is unaffected.
    board = {Square(5, 5): (Side.WHITE, P.KNIGHT)}
    position = _position(board)
    strings = _ply_strings(position)
    assert "F5F6" not in strings
    assert "F5F7" not in strings
    assert "F5F8" not in strings
    assert "F5F4" in strings


def test_skirmisher_rush_up_to_three_squares_move_or_attack():
    board = {
        Square(0, 5): (Side.WHITE, P.SKIRMISHER),
        Square(3, 5): (Side.BLACK, P.MILITIA),
    }
    position = _position(board)
    strings = _ply_strings(position)
    assert {"A5B5", "A5C5", "A5D5"} <= strings


def test_skirmisher_rush_stops_at_first_occupied_square():
    board = {
        Square(0, 5): (Side.WHITE, P.SKIRMISHER),
        Square(2, 5): (Side.BLACK, P.MILITIA),  # 2 squares away, attackable
    }
    position = _position(board)
    strings = _ply_strings(position)
    assert "A5B5" in strings  # move to the empty square before the enemy
    assert "A5C5" in strings  # attack the enemy at distance 2
    assert "A5D5" not in strings  # cannot rush past the enemy


def test_skirmisher_blocked_entirely_by_lake_in_one_direction():
    # Column F (index 5) is a lake column; row 5 -> row 6 is blocked outright,
    # but south (F4) and the other directions remain open.
    board = {Square(5, 5): (Side.WHITE, P.SKIRMISHER)}
    position = _position(board)
    strings = _ply_strings(position)
    assert "F5F6" not in strings
    assert "F5F7" not in strings
    assert "F5F8" not in strings
    assert "F5F4" in strings
    assert "F5G5" in strings


def test_all_ply_strings_distinct_in_a_full_random_position():
    white = random_placement(Side.WHITE)
    black = random_placement(Side.BLACK)
    position = assemble_position(white, black)
    strings = [str(ply) for ply in position.legal_plies]
    assert len(strings) == len(set(strings))
    assert len(strings) > 0

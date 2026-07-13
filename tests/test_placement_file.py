"""Tests for placement-file parsing and loading."""

import pytest

from capture_the_flag.board import (
    BLACK_HOME_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
    parse_square,
)
from capture_the_flag.pieces import ARMY_ROSTER, PieceType
from capture_the_flag.placement_file import (
    PlacementFileError,
    load_placement_file,
    parse_placement_file,
)
from capture_the_flag.side import Side

# All 48 symbols in enum order, chunked into the 4x12 file shape. The Lord
# Marshal ('1') is the first character of the first line and the Flag ('F')
# the last character of the last line, giving the rotation tests distinctive
# one-of-a-kind pieces at known file positions.
_SYMBOLS = "".join(piece.symbol * piece.army_count for piece in PieceType)
VALID_TEXT = "\n".join(_SYMBOLS[i : i + 12] for i in range(0, 48, 12))


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_valid_file_fills_home_zone_with_correct_roster(side):
    placement = parse_placement_file(VALID_TEXT, side)
    expected_squares = WHITE_HOME_SQUARES if side is Side.WHITE else BLACK_HOME_SQUARES
    assert set(placement.keys()) == expected_squares
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    assert counts == ARMY_ROSTER


@pytest.mark.parametrize(
    ("side", "lord_marshal_square", "flag_square"),
    [
        # First line/first char is the row nearest the lakes at the player's
        # left; last line/last char is the back rank at the player's right.
        # Black's frame is White's rotated 180 degrees.
        (Side.WHITE, "A4", "L1"),
        (Side.BLACK, "L9", "A12"),
    ],
)
def test_file_is_read_side_relatively(side, lord_marshal_square, flag_square):
    placement = parse_placement_file(VALID_TEXT, side)
    assert placement[parse_square(lord_marshal_square)] is PieceType.LORD_MARSHAL
    assert placement[parse_square(flag_square)] is PieceType.FLAG


def test_trailing_newlines_are_tolerated():
    placement = parse_placement_file(VALID_TEXT + "\n\n", Side.WHITE)
    assert set(placement.keys()) == WHITE_HOME_SQUARES


def test_wrong_row_count_is_a_form_error():
    with pytest.raises(PlacementFileError, match="4 rows.*got 3"):
        parse_placement_file("\n".join(VALID_TEXT.splitlines()[:3]), Side.WHITE)


def test_wrong_row_length_is_a_form_error():
    lines = VALID_TEXT.splitlines()
    lines[1] = lines[1][:-1]
    with pytest.raises(PlacementFileError, match="Row 2 has 11 characters"):
        parse_placement_file("\n".join(lines), Side.WHITE)


def test_unknown_character_is_a_form_error():
    lines = VALID_TEXT.splitlines()
    lines[2] = "Z" + lines[2][1:]
    with pytest.raises(PlacementFileError, match="Row 3: unknown piece character 'Z'"):
        parse_placement_file("\n".join(lines), Side.WHITE)


def test_roster_mismatch_names_surplus_and_shortfall_types():
    # Replace the lone Flag with a seventh Tower: too many Towers, no Flag.
    text = VALID_TEXT.replace("F", "T")
    with pytest.raises(
        PlacementFileError,
        match=r"too many: Tower \(7 of 6\); too few: Flag \(0 of 1\)",
    ):
        parse_placement_file(text, Side.WHITE)


def test_load_reads_a_file_from_the_placements_folder(tmp_path):
    (tmp_path / "setup.txt").write_text(VALID_TEXT, encoding="utf-8")
    placement = load_placement_file("setup.txt", Side.BLACK, tmp_path)
    assert set(placement.keys()) == BLACK_HOME_SQUARES


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(PlacementFileError, match="No placement file named 'nope.txt'"):
        load_placement_file("nope.txt", Side.WHITE, tmp_path)


def test_parsed_placement_has_a_flag_on_the_board():
    # Guard the test fixture itself: VALID_TEXT is roster-exact.
    placement = parse_placement_file(VALID_TEXT, Side.WHITE)
    assert Square(11, 1) in placement

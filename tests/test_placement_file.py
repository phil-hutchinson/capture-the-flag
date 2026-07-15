"""Tests for placement-file parsing and loading."""

import pytest

from capture_the_flag.board import (
    BLACK_HOME_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
    parse_square,
)
from capture_the_flag.pieces import ARMY_ROSTER, ARMY_SIZE, PieceType
from capture_the_flag.placement_file import (
    PlacementFileError,
    load_placement_file,
    parse_placement_file,
)
from capture_the_flag.side import Side

# A valid 25-piece setup in the 4x12 file shape: three of each numbered rank,
# six spaced Towers, one Flag, and 23 `-` empty squares. The Master-of-Arms
# ('1') is the first character of the first line and the Flag ('F') the last
# character of the last line, giving the rotation tests distinctive pieces at
# known file positions.
VALID_TEXT = "\n".join(
    [
        "123456123456",
        "123456------",
        "T-T-T-T-T-T-",
        "-----------F",
    ]
)


def _piece_counts(placement) -> dict[PieceType, int]:
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    return counts


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_valid_file_fills_25_squares_with_correct_roster(side):
    placement = parse_placement_file(VALID_TEXT, side)
    home = WHITE_HOME_SQUARES if side is Side.WHITE else BLACK_HOME_SQUARES
    assert placement.keys() <= home  # inside the home zone
    assert len(placement) == ARMY_SIZE == 25  # `-` squares left unfilled
    assert _piece_counts(placement) == ARMY_ROSTER


def test_empty_squares_are_left_unoccupied():
    placement = parse_placement_file(VALID_TEXT, Side.WHITE)
    # Row 3 of the file (front rank, nearest the lakes) is all `-`, so its whole
    # board row must be absent from the placement.
    assert len(placement) == 25
    assert all(square in WHITE_HOME_SQUARES for square in placement)


@pytest.mark.parametrize(
    ("side", "master_of_arms_square", "flag_square"),
    [
        # First line/first char is the row nearest the lakes at the player's
        # left; last line/last char is the back rank at the player's right.
        # Black's frame is White's rotated 180 degrees.
        (Side.WHITE, "A4", "L1"),
        (Side.BLACK, "L9", "A12"),
    ],
)
def test_file_is_read_side_relatively(side, master_of_arms_square, flag_square):
    placement = parse_placement_file(VALID_TEXT, side)
    assert placement[parse_square(master_of_arms_square)] is PieceType.MASTER_OF_ARMS
    assert placement[parse_square(flag_square)] is PieceType.FLAG


def test_trailing_newlines_are_tolerated():
    placement = parse_placement_file(VALID_TEXT + "\n\n", Side.WHITE)
    assert len(placement) == 25


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
    lines[0] = "Z" + lines[0][1:]
    with pytest.raises(PlacementFileError, match="Row 1: unknown piece character 'Z'"):
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
    assert placement.keys() <= BLACK_HOME_SQUARES
    assert len(placement) == 25


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(PlacementFileError, match="No placement file named 'nope.txt'"):
        load_placement_file("nope.txt", Side.WHITE, tmp_path)


def test_parsed_placement_has_a_flag_on_the_board():
    # Guard the test fixture itself: VALID_TEXT is roster-exact.
    placement = parse_placement_file(VALID_TEXT, Side.WHITE)
    assert Square(11, 1) in placement  # L1, the Flag square

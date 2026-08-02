"""Tests for placement-file parsing and loading."""

import pytest

from capture_the_flag.board import (
    STANDARD_144,
    Square,
    parse_square,
)
from capture_the_flag.game_setup import (
    BATTLE_SETUP,
    SPACING_ONLY,
    resolve_setup,
    setup_for_ruleset,
)
from capture_the_flag.pieces import STANDARD_BATTLE, PieceType
from capture_the_flag.placement_file import (
    PlacementFileError,
    load_placement_file,
    parse_placement_file,
)
from capture_the_flag.record import RulesetConfiguration
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
    placement = parse_placement_file(VALID_TEXT, side, BATTLE_SETUP)
    home = STANDARD_144.white_home_squares if side is Side.WHITE else STANDARD_144.black_home_squares
    assert placement.keys() <= home  # inside the home zone
    assert len(placement) == STANDARD_BATTLE.size == 25  # `-` squares left unfilled
    assert _piece_counts(placement) == STANDARD_BATTLE.counts


def test_empty_squares_are_left_unoccupied():
    placement = parse_placement_file(VALID_TEXT, Side.WHITE, BATTLE_SETUP)
    # Row 3 of the file (front rank, nearest the lakes) is all `-`, so its whole
    # board row must be absent from the placement.
    assert len(placement) == 25
    assert all(square in STANDARD_144.white_home_squares for square in placement)


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
    placement = parse_placement_file(VALID_TEXT, side, BATTLE_SETUP)
    assert placement[parse_square(master_of_arms_square)] is PieceType.MASTER_OF_ARMS
    assert placement[parse_square(flag_square)] is PieceType.FLAG


def test_trailing_newlines_are_tolerated():
    placement = parse_placement_file(VALID_TEXT + "\n\n", Side.WHITE, BATTLE_SETUP)
    assert len(placement) == 25


def test_wrong_row_count_is_a_form_error():
    with pytest.raises(PlacementFileError, match="4 rows.*got 3"):
        parse_placement_file(
            "\n".join(VALID_TEXT.splitlines()[:3]), Side.WHITE, BATTLE_SETUP
        )


def test_wrong_row_length_is_a_form_error():
    lines = VALID_TEXT.splitlines()
    lines[1] = lines[1][:-1]
    with pytest.raises(PlacementFileError, match="Row 2 has 11 characters"):
        parse_placement_file("\n".join(lines), Side.WHITE, BATTLE_SETUP)


def test_unknown_character_is_a_form_error():
    lines = VALID_TEXT.splitlines()
    lines[0] = "Z" + lines[0][1:]
    with pytest.raises(PlacementFileError, match="Row 1: unknown piece character 'Z'"):
        parse_placement_file("\n".join(lines), Side.WHITE, BATTLE_SETUP)


def test_roster_mismatch_names_surplus_and_shortfall_types():
    # Replace the lone Flag with a seventh Tower: too many Towers, no Flag.
    text = VALID_TEXT.replace("F", "T")
    with pytest.raises(
        PlacementFileError,
        match=r"too many: Tower \(7 of 6\); too few: Flag \(0 of 1\)",
    ):
        parse_placement_file(text, Side.WHITE, BATTLE_SETUP)


def test_load_reads_a_file_from_the_placements_folder(tmp_path):
    (tmp_path / "setup.txt").write_text(VALID_TEXT, encoding="utf-8")
    placement = load_placement_file("setup.txt", Side.BLACK, BATTLE_SETUP, tmp_path)
    assert placement.keys() <= STANDARD_144.black_home_squares
    assert len(placement) == 25


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(PlacementFileError, match="No placement file named 'nope.txt'"):
        load_placement_file("nope.txt", Side.WHITE, BATTLE_SETUP, tmp_path)


def test_parsed_placement_has_a_flag_on_the_board():
    # Guard the test fixture itself: VALID_TEXT is roster-exact.
    placement = parse_placement_file(VALID_TEXT, Side.WHITE, BATTLE_SETUP)
    assert Square(11, 1) in placement  # L1, the Flag square


# --- Tower rules at the file seam (story 37, step 10) ------------------------
#
# Both Tower rules are checked here as well as in `placement`, because a player
# typing a file name is still at a prompt they can retry from: a
# `PlacementFileError` is printed and re-prompted, while the plain `ValueError`
# `assemble_position` raises would end the game.

# The published Skirmish edition already sets the flag on; the spacing-only
# variant is resolved from a configuration deviating on `TOWER_PLACEMENT` alone,
# so that it stays stampable — a setup's configuration has to resolve to its
# fields (see `game_setup.GameSetup`).
_SKIRMISH = setup_for_ruleset("SKIRMISH")
_SKIRMISH_SPACING_ONLY = resolve_setup(
    RulesetConfiguration(
        edition=_SKIRMISH.stamp.edition, flags={"TOWER_PLACEMENT": SPACING_ONLY}
    )
)

# A legal Skirmish file, front rank first: Towers on the back rank at A1, D1 and
# G1, the Flag beside them, and the twelve numbered pieces above.
SKIRMISH_TEXT = "\n".join(
    [
        "12341234",
        "1234----",
        "T--T--TF",
    ]
)

# The same roster with one Tower moved to the mouth of the A lane (A3 for White).
SKIRMISH_LANE_TOWER_TEXT = "\n".join(
    [
        "T2341234",
        "1234----",
        "1--T--TF",
    ]
)


def test_a_valid_skirmish_file_parses_under_both_tower_rules():
    for setup in (_SKIRMISH_SPACING_ONLY, _SKIRMISH):
        placement = parse_placement_file(SKIRMISH_TEXT, Side.WHITE, setup)
        assert _piece_counts(placement)[PieceType.TOWER] == 3


def test_a_lane_mouth_tower_is_rejected_under_spacing_and_lanes():
    with pytest.raises(PlacementFileError, match="in front of a lane") as rejection:
        parse_placement_file(SKIRMISH_LANE_TOWER_TEXT, Side.WHITE, _SKIRMISH)
    # The offending square by name: a file is a grid of characters, so "a Tower is
    # badly placed" is not something a player can act on.
    assert "A3" in str(rejection.value)


def test_a_lane_mouth_tower_is_accepted_under_spacing_only():
    placement = parse_placement_file(
        SKIRMISH_LANE_TOWER_TEXT, Side.WHITE, _SKIRMISH_SPACING_ONLY
    )

    assert placement[parse_square("A3")] is PieceType.TOWER


def test_the_lane_rule_follows_the_side_the_file_is_read_for():
    # The same file read for Black lands on Black's home zone, so the square it
    # closes is A6 rather than A3 — the restriction is per side, derived from the
    # same geometry.
    with pytest.raises(PlacementFileError, match="in front of a lane") as rejection:
        parse_placement_file(SKIRMISH_LANE_TOWER_TEXT, Side.BLACK, _SKIRMISH)
    assert "H6" in str(rejection.value)


def test_adjacent_towers_are_reported_at_the_file_seam():
    # Not new to this story's flag, but reachable through the same seam: without
    # the check the file parses and the game then dies in `assemble_position`.
    text = "\n".join(
        [
            "12341234",
            "1234----",
            "TT---T-F",
        ]
    )
    with pytest.raises(PlacementFileError, match="next to each other") as rejection:
        parse_placement_file(text, Side.WHITE, _SKIRMISH)
    message = str(rejection.value)
    assert "A1" in message and "B1" in message

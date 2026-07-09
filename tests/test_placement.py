"""Tests for the placement seam and the random placement generator."""

import random

import pytest

from capture_the_flag.board import (
    BLACK_HOME_SQUARES,
    LAKE_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
)
from capture_the_flag.pieces import ARMY_ROSTER, PieceType
from capture_the_flag.placement import assemble_position, random_placement
from capture_the_flag.side import Side

BUFFER_ROWS = (5, 8)


def _piece_counts(placement) -> dict[PieceType, int]:
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    return counts


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_placement_fills_home_zone_with_correct_roster(side):
    for _ in range(20):
        placement = random_placement(side, random.Random())
        expected_squares = (
            WHITE_HOME_SQUARES if side is Side.WHITE else BLACK_HOME_SQUARES
        )
        assert set(placement.keys()) == expected_squares
        assert _piece_counts(placement) == ARMY_ROSTER


def test_random_placement_is_reproducible_with_a_fixed_seed():
    first = random_placement(Side.WHITE, random.Random(12345))
    second = random_placement(Side.WHITE, random.Random(12345))
    assert first == second


def test_random_placement_is_not_always_identical():
    placements = {
        tuple(sorted(random_placement(Side.WHITE, random.Random(seed)).items()))
        for seed in range(10)
    }
    assert len(placements) > 1


def test_assemble_position_builds_a_fully_populated_start():
    white_placement = random_placement(Side.WHITE, random.Random(1))
    black_placement = random_placement(Side.BLACK, random.Random(2))
    position = assemble_position(white_placement, black_placement)

    white_squares = {
        square
        for square, (side, _piece) in position.board.items()
        if side is Side.WHITE
    }
    black_squares = {
        square
        for square, (side, _piece) in position.board.items()
        if side is Side.BLACK
    }
    assert white_squares == WHITE_HOME_SQUARES
    assert black_squares == BLACK_HOME_SQUARES

    white_counts = _piece_counts(
        {sq: piece for sq, (side, piece) in position.board.items() if side is Side.WHITE}
    )
    black_counts = _piece_counts(
        {sq: piece for sq, (side, piece) in position.board.items() if side is Side.BLACK}
    )
    assert white_counts == ARMY_ROSTER
    assert black_counts == ARMY_ROSTER


def test_assemble_position_leaves_buffer_and_lake_rows_unoccupied():
    white_placement = random_placement(Side.WHITE, random.Random(3))
    black_placement = random_placement(Side.BLACK, random.Random(4))
    position = assemble_position(white_placement, black_placement)

    occupied = set(position.board.keys())
    assert occupied.isdisjoint(LAKE_SQUARES)
    for row in BUFFER_ROWS:
        buffer_squares = {Square(c, row) for c in range(12)}
        assert occupied.isdisjoint(buffer_squares)


def test_assemble_position_side_to_move_and_clocks():
    white_placement = random_placement(Side.WHITE, random.Random(5))
    black_placement = random_placement(Side.BLACK, random.Random(6))
    position = assemble_position(white_placement, black_placement)

    assert position.side_to_move is Side.WHITE
    assert position.active_player_id == 1
    assert position.white_inactivity_counter == 0
    assert position.black_inactivity_counter == 0
    assert position.progress_counter == 0
    assert position.breachability is None


def test_assemble_position_rejects_wrong_zone_or_roster():
    good_white = random_placement(Side.WHITE, random.Random(7))
    good_black = random_placement(Side.BLACK, random.Random(8))

    with pytest.raises(ValueError):
        # A Black placement offered as White's (wrong home zone).
        assemble_position(good_black, good_black)

    mismatched_roster = dict(good_white)
    a_square = next(iter(mismatched_roster))
    mismatched_roster[a_square] = PieceType.TOWER
    # Now missing one of whatever piece used to be there and has 7 Towers.
    with pytest.raises(ValueError):
        assemble_position(mismatched_roster, good_black)

"""Tests for the placement seam and the random placement generator."""

import itertools
import random

import pytest

from capture_the_flag.board import (
    BLACK_HOME_SQUARES,
    LAKE_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
)
from capture_the_flag.pieces import ARMY_ROSTER, ARMY_SIZE, PieceType
from capture_the_flag.placement import Placement, assemble_position, random_placement
from capture_the_flag.side import Side

BUFFER_ROWS = (5, 8)


def _home_squares(side: Side):
    return WHITE_HOME_SQUARES if side is Side.WHITE else BLACK_HOME_SQUARES


def _piece_counts(placement) -> dict[PieceType, int]:
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    return counts


def _towers(placement: Placement):
    return [square for square, piece in placement.items() if piece is PieceType.TOWER]


def _chebyshev(a: Square, b: Square) -> int:
    return max(abs(a.column - b.column), abs(a.row - b.row))


def _has_adjacent_towers(placement: Placement) -> bool:
    return any(_chebyshev(a, b) <= 1 for a, b in itertools.combinations(_towers(placement), 2))


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_placement_fills_25_of_home_zone_with_correct_roster(side):
    for _ in range(20):
        placement = random_placement(side, random.Random())
        assert placement.keys() <= _home_squares(side)  # inside the home zone
        assert len(placement) == ARMY_SIZE == 25  # 25 of the 48 squares filled
        assert _piece_counts(placement) == ARMY_ROSTER


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_placement_never_places_adjacent_towers(side):
    for seed in range(200):
        placement = random_placement(side, random.Random(seed))
        assert not _has_adjacent_towers(placement)


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


def test_assemble_position_places_both_armies_in_their_home_zones():
    white_placement = random_placement(Side.WHITE, random.Random(1))
    black_placement = random_placement(Side.BLACK, random.Random(2))
    position = assemble_position(white_placement, black_placement)

    white = {
        sq: piece
        for sq, (side, piece) in position.board.items()
        if side is Side.WHITE
    }
    black = {
        sq: piece
        for sq, (side, piece) in position.board.items()
        if side is Side.BLACK
    }
    assert white.keys() <= WHITE_HOME_SQUARES
    assert black.keys() <= BLACK_HOME_SQUARES
    assert len(white) == len(black) == ARMY_SIZE
    assert _piece_counts(white) == ARMY_ROSTER
    assert _piece_counts(black) == ARMY_ROSTER


def test_assemble_position_leaves_buffer_and_lake_rows_unoccupied():
    white_placement = random_placement(Side.WHITE, random.Random(3))
    black_placement = random_placement(Side.BLACK, random.Random(4))
    position = assemble_position(white_placement, black_placement)

    occupied = set(position.board.keys())
    assert occupied.isdisjoint(LAKE_SQUARES)
    for row in BUFFER_ROWS:
        buffer_squares = {Square(c, row) for c in range(12)}
        assert occupied.isdisjoint(buffer_squares)


def test_assemble_position_side_to_move_and_clock():
    white_placement = random_placement(Side.WHITE, random.Random(5))
    black_placement = random_placement(Side.BLACK, random.Random(6))
    position = assemble_position(white_placement, black_placement)

    assert position.side_to_move is Side.WHITE
    assert position.active_player_id == 1
    assert position.inactivity_counter == 0


def test_assemble_position_rejects_wrong_zone_or_roster():
    good_white = random_placement(Side.WHITE, random.Random(7))
    good_black = random_placement(Side.BLACK, random.Random(8))

    with pytest.raises(ValueError):
        # A Black placement offered as White's (wrong home zone).
        assemble_position(good_black, good_black)

    mismatched_roster = dict(good_white)
    non_tower = next(sq for sq, piece in mismatched_roster.items() if piece is not PieceType.TOWER)
    mismatched_roster[non_tower] = PieceType.TOWER  # now 7 Towers, short one rank
    with pytest.raises(ValueError):
        assemble_position(mismatched_roster, good_black)


def test_assemble_position_rejects_a_full_home_zone_fill():
    # Filling all 48 squares can never match the 25-piece roster.
    full_white = {square: PieceType.MILITIA for square in WHITE_HOME_SQUARES}
    good_black = random_placement(Side.BLACK, random.Random(9))
    with pytest.raises(ValueError):
        assemble_position(full_white, good_black)


def test_assemble_position_rejects_adjacent_towers():
    good_white = random_placement(Side.WHITE, random.Random(10))
    good_black = random_placement(Side.BLACK, random.Random(11))
    clustered = _force_adjacent_towers(good_white, WHITE_HOME_SQUARES)

    # The tampered placement keeps the exact roster, so only the spacing rule
    # can be what rejects it.
    assert _piece_counts(clustered) == ARMY_ROSTER
    assert _has_adjacent_towers(clustered)
    with pytest.raises(ValueError):
        assemble_position(clustered, good_black)


def _force_adjacent_towers(placement: Placement, home) -> dict:
    """Relocate one Tower next to another without disturbing the roster: the
    moved Tower's old square takes on whatever piece (if any) sat in the new
    square, so counts are preserved and only Tower spacing is violated.
    """
    result = dict(placement)
    towers = _towers(result)
    anchor, mover = towers[0], towers[1]
    for dc, dr in itertools.product((-1, 0, 1), repeat=2):
        target = Square(anchor.column + dc, anchor.row + dr)
        if target not in home or target == mover or result.get(target) is PieceType.TOWER:
            continue
        occupant = result.pop(mover)  # the Tower being relocated
        displaced = result.get(target)
        if displaced is not None:
            result[mover] = displaced
        result[target] = occupant
        return result
    raise AssertionError("expected a free neighbour of the anchor Tower")

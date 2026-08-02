"""Tests for the placement seam and the random placement generator."""

import dataclasses
import itertools
import random

import pytest

from capture_the_flag.board import (
    STANDARD_144,
    Square,
)
from capture_the_flag.game_setup import (
    BATTLE_SETUP,
    SPACING_AND_LANES,
    SPACING_ONLY,
    setup_for_ruleset,
)
from capture_the_flag.pieces import STANDARD_BATTLE, STANDARD_SKIRMISH, PieceType
from capture_the_flag.placement import Placement, assemble_position, random_placement
from capture_the_flag.side import Side

BUFFER_ROWS = (5, 8)


def _home_squares(side: Side):
    return STANDARD_144.white_home_squares if side is Side.WHITE else STANDARD_144.black_home_squares


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
        placement = random_placement(side, BATTLE_SETUP, random.Random())
        assert placement.keys() <= _home_squares(side)  # inside the home zone
        assert len(placement) == STANDARD_BATTLE.size == 25  # 25 of the 48 squares filled
        assert _piece_counts(placement) == STANDARD_BATTLE.counts


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_placement_never_places_adjacent_towers(side):
    for seed in range(200):
        placement = random_placement(side, BATTLE_SETUP, random.Random(seed))
        assert not _has_adjacent_towers(placement)


def test_random_placement_is_reproducible_with_a_fixed_seed():
    first = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(12345))
    second = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(12345))
    assert first == second


def test_random_placement_is_not_always_identical():
    placements = {
        tuple(sorted(random_placement(Side.WHITE, BATTLE_SETUP, random.Random(seed)).items()))
        for seed in range(10)
    }
    assert len(placements) > 1


def test_assemble_position_places_both_armies_in_their_home_zones():
    white_placement = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(1))
    black_placement = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(2))
    position = assemble_position(white_placement, black_placement, BATTLE_SETUP)

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
    assert white.keys() <= STANDARD_144.white_home_squares
    assert black.keys() <= STANDARD_144.black_home_squares
    assert len(white) == len(black) == STANDARD_BATTLE.size
    assert _piece_counts(white) == STANDARD_BATTLE.counts
    assert _piece_counts(black) == STANDARD_BATTLE.counts


def test_assemble_position_leaves_buffer_and_lake_rows_unoccupied():
    white_placement = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(3))
    black_placement = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(4))
    position = assemble_position(white_placement, black_placement, BATTLE_SETUP)

    occupied = set(position.board.keys())
    assert occupied.isdisjoint(STANDARD_144.lake_squares)
    for row in BUFFER_ROWS:
        buffer_squares = {Square(c, row) for c in range(12)}
        assert occupied.isdisjoint(buffer_squares)


def test_assemble_position_side_to_move_and_clock():
    white_placement = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(5))
    black_placement = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(6))
    position = assemble_position(white_placement, black_placement, BATTLE_SETUP)

    assert position.side_to_move is Side.WHITE
    assert position.active_player_id == 1
    assert position.inactivity_counter == 0


def test_assemble_position_rejects_wrong_zone_or_roster():
    good_white = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(7))
    good_black = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(8))

    with pytest.raises(ValueError):
        # A Black placement offered as White's (wrong home zone).
        assemble_position(good_black, good_black, BATTLE_SETUP)

    mismatched_roster = dict(good_white)
    non_tower = next(sq for sq, piece in mismatched_roster.items() if piece is not PieceType.TOWER)
    mismatched_roster[non_tower] = PieceType.TOWER  # now 7 Towers, short one rank
    with pytest.raises(ValueError):
        assemble_position(mismatched_roster, good_black, BATTLE_SETUP)


def test_assemble_position_rejects_a_full_home_zone_fill():
    # Filling all 48 squares can never match the 25-piece roster.
    full_white = {square: PieceType.MILITIA for square in STANDARD_144.white_home_squares}
    good_black = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(9))
    with pytest.raises(ValueError):
        assemble_position(full_white, good_black, BATTLE_SETUP)


def test_assemble_position_rejects_adjacent_towers():
    good_white = random_placement(Side.WHITE, BATTLE_SETUP, random.Random(10))
    good_black = random_placement(Side.BLACK, BATTLE_SETUP, random.Random(11))
    clustered = _force_adjacent_towers(good_white, STANDARD_144.white_home_squares)

    # The tampered placement keeps the exact roster, so only the spacing rule
    # can be what rejects it.
    assert _piece_counts(clustered) == STANDARD_BATTLE.counts
    assert _has_adjacent_towers(clustered)
    with pytest.raises(ValueError):
        assemble_position(clustered, good_black, BATTLE_SETUP)


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


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_skirmish_placement_fills_its_own_home_zone_and_roster(side):
    setup = setup_for_ruleset("SKIRMISH")
    for _ in range(20):
        placement = random_placement(side, setup, random.Random())
        assert placement.keys() <= setup.layout.home_squares(side)
        assert len(placement) == 16  # 16 of the 24 home squares filled
        assert _piece_counts(placement) == STANDARD_SKIRMISH.counts


def test_the_skirmish_tower_walk_never_stalls():
    # The greedy Tower-first walk is only safe while the home zone is big enough:
    # each Tower removes at most its nine-square closed neighbourhood, so 3 into
    # 24 leaves at least 6 candidates for the third. Battle's proof (6 into 48)
    # does not carry over, so it is re-derived here rather than assumed.
    setup = setup_for_ruleset("SKIRMISH")
    for seed in range(300):
        placement = random_placement(Side.WHITE, setup, random.Random(seed))
        assert len(_towers(placement)) == 3
        assert not _has_adjacent_towers(placement)


def test_a_skirmish_placement_assembles_into_a_skirmish_position():
    setup = setup_for_ruleset("SKIRMISH")
    rng = random.Random(7)
    position = assemble_position(
        random_placement(Side.WHITE, setup, rng),
        random_placement(Side.BLACK, setup, rng),
        setup,
    )
    # The position carries the board it is played on, which is how move
    # generation knows an 8 x 8 board from a 12 x 12 one.
    assert position.layout is setup.layout
    assert len(position.board) == 32  # both 16-piece armies
    # Front ranks 3 rows apart, not Battle's 4: there is no neutral buffer.
    assert max(s.row for s in position.board if s.row <= 3) == 3
    assert min(s.row for s in position.board if s.row >= 6) == 6


# --- TOWER_PLACEMENT (story 37, step 10) -------------------------------------

# The published Skirmish edition sets the flag on, so `setup_for_ruleset` already
# carries it; the spacing-only variant has to be constructed. Battle with the flag
# turned on is not a published pairing and exists only to pin that the restriction
# is inert there.
_SKIRMISH = setup_for_ruleset("SKIRMISH")
_SKIRMISH_SPACING_ONLY = dataclasses.replace(_SKIRMISH, tower_placement=SPACING_ONLY)
_BATTLE_LANES_ON = dataclasses.replace(BATTLE_SETUP, tower_placement=SPACING_AND_LANES)


def test_spacing_and_lanes_closes_the_skirmish_lane_mouths():
    # The four lanes on the 8x8 board are columns A, D, E and H — the columns the
    # lake pattern leaves open — and each home zone's front rank sits directly
    # against a lake row, so exactly those four squares close per side.
    white = _SKIRMISH.forbidden_tower_squares(Side.WHITE)
    black = _SKIRMISH.forbidden_tower_squares(Side.BLACK)

    assert {str(square) for square in white} == {"A3", "D3", "E3", "H3"}
    assert {str(square) for square in black} == {"A6", "D6", "E6", "H6"}


def test_spacing_and_lanes_leaves_the_squares_behind_the_lakes_open():
    # B, C, F and G are lake columns, so nothing behind them fronts a lane and
    # the restriction must not touch them — a rule that closed the whole front
    # rank would be a different (and much heavier) rule.
    closed = _SKIRMISH.forbidden_tower_squares(Side.WHITE)

    assert not closed & {Square(column, 3) for column in (1, 2, 5, 6)}


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_spacing_and_lanes_closes_nothing_on_the_battle_board(side):
    # Battle has a neutral buffer row between each home zone and the lakes, so no
    # home square is adjacent to a lane. The flag is well-defined there and inert,
    # and that falls out of the geometry rather than being special-cased.
    assert _BATTLE_LANES_ON.forbidden_tower_squares(side) == frozenset()


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_spacing_only_closes_nothing_anywhere(side):
    assert _SKIRMISH_SPACING_ONLY.forbidden_tower_squares(side) == frozenset()
    assert BATTLE_SETUP.forbidden_tower_squares(side) == frozenset()


@pytest.mark.parametrize("side", [Side.WHITE, Side.BLACK])
def test_random_skirmish_placement_never_puts_a_tower_on_a_closed_square(side):
    # Many seeds rather than a few: three Towers in twenty candidate squares is
    # the tightest the greedy walk gets under any published pairing, so this is
    # also the stall check — a seed that stalls raises out of `random_placement`.
    closed = _SKIRMISH.forbidden_tower_squares(side)
    for seed in range(400):
        placement = random_placement(side, _SKIRMISH, random.Random(seed))
        assert not closed & set(_towers(placement))
        assert not _has_adjacent_towers(placement)
        assert _piece_counts(placement) == STANDARD_SKIRMISH.counts


def _skirmish_placement(side: Side, tower_squares: tuple[Square, ...]) -> Placement:
    """A roster-exact Skirmish placement with the Towers on `tower_squares`.

    Built by hand rather than drawn, so the only thing that varies between the
    cases below is where the Towers stand.
    """
    placement: dict[Square, PieceType] = dict.fromkeys(tower_squares, PieceType.TOWER)
    rest = [
        square
        for square in sorted(_SKIRMISH_SPACING_ONLY.layout.home_squares(side))
        if square not in placement
    ]
    pieces = [PieceType.FLAG] + [
        rank
        for rank in (
            PieceType.MASTER_OF_ARMS,
            PieceType.CHAMPION,
            PieceType.KNIGHT,
            PieceType.HALBERDIER,
        )
        for _ in range(3)
    ]
    placement.update(zip(rest, pieces, strict=False))
    return placement


_A3, _D1, _G1 = Square(0, 3), Square(3, 1), Square(6, 1)


def test_assemble_position_rejects_a_tower_in_a_lane_mouth():
    # A3 is the mouth of the A lane; D1 and G1 are back-rank squares far enough
    # from it and from each other that the spacing rule is satisfied, so the lane
    # rule is the only thing that can reject this placement.
    white = _skirmish_placement(Side.WHITE, (_A3, _D1, _G1))
    black = random_placement(Side.BLACK, _SKIRMISH, random.Random(2))

    with pytest.raises(ValueError, match="in front of a lane") as rejection:
        assemble_position(white, black, _SKIRMISH)
    assert "A3" in str(rejection.value)


def test_the_same_placement_is_legal_under_spacing_only():
    # Same board, flag at its default: accepted. That is what makes this a flag
    # rather than a rules change — no existing edition's play is altered.
    white = _skirmish_placement(Side.WHITE, (_A3, _D1, _G1))
    black = random_placement(Side.BLACK, _SKIRMISH_SPACING_ONLY, random.Random(2))

    position = assemble_position(white, black, _SKIRMISH_SPACING_ONLY)

    assert position.board[_A3] == (Side.WHITE, PieceType.TOWER)


def test_game_setup_rejects_an_unimplemented_tower_placement():
    with pytest.raises(ValueError, match="TOWER_PLACEMENT"):
        dataclasses.replace(BATTLE_SETUP, tower_placement="lanes_only_on_tuesdays")

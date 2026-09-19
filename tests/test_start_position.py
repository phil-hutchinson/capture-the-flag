"""Tests for starting-position generation (`doc/ruleset/start-position.md`)."""

import random
from collections import Counter

from capture_the_flag.board import BoardLayout, Square
from capture_the_flag.game_setup import PRE_RELEASE_SETUP, GameSetup
from capture_the_flag.pieces import ArmyComposition, PieceType
from capture_the_flag.side import Side
from capture_the_flag.start_position import generate_start_position, strength_threshold

_SEEDS = range(300)


def _rank(piece: PieceType) -> int:
    assert piece.rank is not None, "the Flag has no rank"
    return piece.rank


def _side_arrangement(position, side: Side) -> dict[Square, PieceType]:
    return {
        square: piece
        for square, (occupant_side, piece) in position.board.items()
        if occupant_side is side
    }


def test_generated_position_starts_white_to_move_with_a_clean_clock():
    position = generate_start_position(PRE_RELEASE_SETUP, random.Random(0))

    assert position.side_to_move is Side.WHITE
    assert position.inactivity_counter == 0
    assert position.layout is PRE_RELEASE_SETUP.layout


def test_generated_position_is_reproducible_with_a_fixed_seed():
    first = generate_start_position(PRE_RELEASE_SETUP, random.Random(123))
    second = generate_start_position(PRE_RELEASE_SETUP, random.Random(123))

    assert dict(first.board) == dict(second.board)


def test_generation_is_not_always_the_same_position():
    positions = {
        tuple(sorted(generate_start_position(PRE_RELEASE_SETUP, random.Random(seed)).board.items()))
        for seed in range(20)
    }
    assert len(positions) > 1


def test_both_home_zones_are_always_completely_full():
    layout = PRE_RELEASE_SETUP.layout
    composition = PRE_RELEASE_SETUP.composition
    for seed in _SEEDS:
        position = generate_start_position(PRE_RELEASE_SETUP, random.Random(seed))
        white = _side_arrangement(position, Side.WHITE)
        black = _side_arrangement(position, Side.BLACK)

        assert white.keys() == layout.white_home_squares
        assert black.keys() == layout.black_home_squares
        assert Counter(white.values()) == Counter(composition.counts)
        assert Counter(black.values()) == Counter(composition.counts)


def test_the_flag_is_always_on_the_back_row():
    layout = PRE_RELEASE_SETUP.layout
    for seed in _SEEDS:
        position = generate_start_position(PRE_RELEASE_SETUP, random.Random(seed))
        white = _side_arrangement(position, Side.WHITE)
        black = _side_arrangement(position, Side.BLACK)

        white_flag = next(sq for sq, piece in white.items() if piece is PieceType.FLAG)
        black_flag = next(sq for sq, piece in black.items() if piece is PieceType.FLAG)
        assert white_flag.row == layout.white_home_rows[0] == 1
        assert black_flag.row == layout.black_home_rows[-1] == layout.rows


def test_black_is_white_turned_by_the_strength_rule():
    # Re-derives the expected turn from `start-position.md` Section 3 directly,
    # independent of `start_position.py`'s own helpers, so this checks the
    # documented rule rather than the implementation's agreement with itself.
    layout = PRE_RELEASE_SETUP.layout
    boundary = layout.columns // 2
    threshold = strength_threshold(PRE_RELEASE_SETUP)

    for seed in _SEEDS:
        position = generate_start_position(PRE_RELEASE_SETUP, random.Random(seed))
        white = _side_arrangement(position, Side.WHITE)
        black = _side_arrangement(position, Side.BLACK)

        flag_square = next(sq for sq, piece in white.items() if piece is PieceType.FLAG)
        flag_in_left_half = flag_square.column < boundary
        strength = sum(
            _rank(piece)
            for square, piece in white.items()
            if piece is not PieceType.FLAG and (square.column < boundary) == flag_in_left_half
        )

        if strength >= threshold:
            # Half-turn: 180 degrees.
            expected = {
                Square(layout.columns - 1 - sq.column, layout.rows + 1 - sq.row): piece
                for sq, piece in white.items()
            }
        else:
            # Reflection: top-to-bottom, column unchanged.
            expected = {
                Square(sq.column, layout.rows + 1 - sq.row): piece
                for sq, piece in white.items()
            }
        assert black == expected


def test_strength_threshold_for_the_standard_army():
    # `start-position.md` Section 3: three each of ranks 1-5 derives 22.
    assert strength_threshold(PRE_RELEASE_SETUP) == 22


def test_strength_threshold_is_derived_from_the_army_not_hardcoded():
    # A differently-sized army on a differently-sized board, so a threshold
    # that happened to be hardcoded to 22 (or to any formula tied to this
    # board's width) would be caught here rather than only agreeing by luck on
    # the published army.
    small_setup = GameSetup(
        layout=BoardLayout(layout_id="test_only_small", columns=4, rows=8, home_rows=2),
        composition=ArmyComposition(
            composition_id="test_only_seven_fives",
            counts={PieceType.MASTER_OF_ARMS: 7, PieceType.FLAG: 1},
        ),
    )
    # Each half holds 4 squares (2 columns x 2 rows); minus the Flag, 3 numbered
    # pieces of rank 5 apiece; total rank across all 7 numbered pieces is 35.
    # An even share of 3 of 7 pieces is 35 x 3 / 7 = 15 exactly, so the
    # threshold -- the smallest S strictly greater than that -- is 16.
    assert strength_threshold(small_setup) == 16


def test_opening_plies_originate_only_from_the_front_row():
    # The cheapest check that generation and the rules agree: a completely full
    # home area encloses every back-row piece (`start-position.md` Section 1),
    # so only the eight front-row (numbered) pieces can move, and only forwards.
    # Movement's own first-ply restriction lands at step 11, so each front-row
    # piece still has both its one- and two-square forward move here.
    layout = PRE_RELEASE_SETUP.layout
    front_row = layout.white_home_rows[-1]
    expected_sources = {Square(column, front_row) for column in range(layout.columns)}

    for seed in _SEEDS:
        position = generate_start_position(PRE_RELEASE_SETUP, random.Random(seed))
        legal_plies = position.legal_plies

        assert {ply.source for ply in legal_plies} == expected_sources
        assert len(legal_plies) == 2 * layout.columns
        for ply in legal_plies:
            assert ply.destination.column == ply.source.column
            assert ply.destination.row in (ply.source.row + 1, ply.source.row + 2)

"""Tests for board coordinate geometry: squares, zones, lakes, and paths."""

import pytest

from capture_the_flag.board import (
    STANDARD_144,
    BoardLayout,
    Square,
    parse_square,
    path_between,
)


def test_square_str_and_parse_round_trip_over_all_squares():
    for row in range(1, STANDARD_144.rows + 1):
        for column in range(STANDARD_144.columns):
            square = Square(column, row)
            assert parse_square(str(square)) == square


def test_parse_square_rejects_malformed_notation():
    # `parse_square` validates the notation, not the board: a column letter and a
    # positive row number. Whether a square is on any particular board is a
    # `BoardLayout` question, which this function has no layout to answer with.
    with pytest.raises(ValueError):
        parse_square("A0")
    with pytest.raises(ValueError):
        parse_square("4A")
    with pytest.raises(ValueError):
        parse_square("AA")


def test_parse_square_accepts_coordinates_beyond_a_given_board():
    # 'Z40' names no square on either published board, but it is well-formed
    # notation. Legality is what rejects it in play.
    assert parse_square("Z40") == Square(25, 40)
    assert not STANDARD_144.contains(parse_square("Z40"))


def test_lake_squares_are_the_twelve_expected_squares():
    assert len(STANDARD_144.lake_squares) == 12
    expected = {
        Square(c, r)
        for r in (6, 7)
        for c in range(STANDARD_144.columns)
        if STANDARD_144.lake_pattern[c]
    }
    assert STANDARD_144.lake_squares == expected


def test_home_zones_have_48_squares_each_and_do_not_overlap():
    assert len(STANDARD_144.white_home_squares) == 48
    assert len(STANDARD_144.black_home_squares) == 48
    assert STANDARD_144.white_home_squares.isdisjoint(STANDARD_144.black_home_squares)
    assert all(1 <= s.row <= 4 for s in STANDARD_144.white_home_squares)
    assert all(9 <= s.row <= 12 for s in STANDARD_144.black_home_squares)


def test_home_zones_and_lakes_do_not_overlap():
    assert STANDARD_144.white_home_squares.isdisjoint(STANDARD_144.lake_squares)
    assert STANDARD_144.black_home_squares.isdisjoint(STANDARD_144.lake_squares)


def test_orthogonal_neighbors_interior_square():
    neighbors = STANDARD_144.orthogonal_neighbors(Square(5, 5))
    assert set(neighbors) == {
        Square(5, 6),
        Square(5, 4),
        Square(6, 5),
        Square(4, 5),
    }


def test_orthogonal_neighbors_corner_square():
    neighbors = STANDARD_144.orthogonal_neighbors(Square(0, 1))
    assert set(neighbors) == {Square(0, 2), Square(1, 1)}


def test_path_between_adjacent_squares_is_empty():
    assert path_between(Square(0, 1), Square(0, 2)) == ()


def test_path_between_same_column():
    assert path_between(Square(3, 1), Square(3, 5)) == (
        Square(3, 2),
        Square(3, 3),
        Square(3, 4),
    )


def test_path_between_same_row_reversed():
    assert path_between(Square(5, 1), Square(1, 1)) == (
        Square(4, 1),
        Square(3, 1),
        Square(2, 1),
    )


def test_path_between_rejects_non_collinear_pairs():
    assert path_between(Square(0, 1), Square(2, 3)) is None


def test_path_between_rejects_same_square():
    assert path_between(Square(4, 4), Square(4, 4)) is None


def test_layout_rejects_a_lake_row_inside_a_home_zone():
    with pytest.raises(ValueError, match="lies inside a home zone"):
        BoardLayout(
            layout_id="broken",
            columns=4,
            rows=8,
            home_rows=3,
            lake_rows=(3, 4),  # row 3 is still White's home zone
            lake_pattern=(False, True, True, False),
        )


def test_layout_rejects_a_lake_pattern_of_the_wrong_width():
    with pytest.raises(ValueError, match="lake pattern covers"):
        BoardLayout(
            layout_id="broken",
            columns=8,
            rows=8,
            home_rows=3,
            lake_rows=(4, 5),
            lake_pattern=(False, True, True, False),
        )


def test_layout_rejects_home_zones_that_leave_no_gap():
    with pytest.raises(ValueError, match="do not fit"):
        BoardLayout(
            layout_id="broken",
            columns=4,
            rows=8,
            home_rows=4,  # 4 + 4 fills the board, leaving no middle
            lake_rows=(),
            lake_pattern=(False,) * 4,
        )


def test_a_layout_derives_its_zones_from_its_dimensions():
    # A small board that is not either published layout, to pin down that the
    # derivation is general rather than tuned to Battle.
    layout = BoardLayout(
        layout_id="tiny",
        columns=4,
        rows=6,
        home_rows=2,
        lake_rows=(3, 4),
        lake_pattern=(False, True, True, False),
    )
    assert layout.white_home_rows == range(1, 3)
    assert layout.black_home_rows == range(5, 7)
    assert len(layout.white_home_squares) == 8
    assert layout.lake_squares == {
        Square(1, 3), Square(2, 3), Square(1, 4), Square(2, 4)
    }
    assert layout.column_letters == "ABCD"
    assert layout.contains(Square(3, 6))
    assert not layout.contains(Square(4, 6))

"""Tests for board coordinate geometry: squares, zones, lakes, and paths."""

import pytest

from capture_the_flag.board import (
    BLACK_HOME_SQUARES,
    BOARD_COLUMNS,
    BOARD_ROWS,
    LAKE_PATTERN,
    LAKE_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
    orthogonal_neighbors,
    parse_square,
    path_between,
)


def test_square_str_and_parse_round_trip_over_all_squares():
    for row in range(1, BOARD_ROWS + 1):
        for column in range(BOARD_COLUMNS):
            square = Square(column, row)
            assert parse_square(str(square)) == square


def test_parse_square_rejects_malformed_input():
    with pytest.raises(ValueError):
        parse_square("Z4")
    with pytest.raises(ValueError):
        parse_square("A13")
    with pytest.raises(ValueError):
        parse_square("A0")


def test_lake_squares_are_the_twelve_expected_squares():
    assert len(LAKE_SQUARES) == 12
    expected = {
        Square(c, r)
        for r in (6, 7)
        for c in range(BOARD_COLUMNS)
        if LAKE_PATTERN[c]
    }
    assert LAKE_SQUARES == expected


def test_home_zones_have_48_squares_each_and_do_not_overlap():
    assert len(WHITE_HOME_SQUARES) == 48
    assert len(BLACK_HOME_SQUARES) == 48
    assert WHITE_HOME_SQUARES.isdisjoint(BLACK_HOME_SQUARES)
    assert all(1 <= s.row <= 4 for s in WHITE_HOME_SQUARES)
    assert all(9 <= s.row <= 12 for s in BLACK_HOME_SQUARES)


def test_home_zones_and_lakes_do_not_overlap():
    assert WHITE_HOME_SQUARES.isdisjoint(LAKE_SQUARES)
    assert BLACK_HOME_SQUARES.isdisjoint(LAKE_SQUARES)


def test_orthogonal_neighbors_interior_square():
    neighbors = orthogonal_neighbors(Square(5, 5))
    assert set(neighbors) == {
        Square(5, 6),
        Square(5, 4),
        Square(6, 5),
        Square(4, 5),
    }


def test_orthogonal_neighbors_corner_square():
    neighbors = orthogonal_neighbors(Square(0, 1))
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

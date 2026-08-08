"""Tests for board coordinate geometry: squares, zones, lakes, and paths."""

import pytest

from capture_the_flag.board import (
    ASYMMETRIC_100,
    BOARD_LAYOUTS,
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


def test_clash_home_zones_have_30_squares_each_separated_by_buffer_rows():
    assert len(ASYMMETRIC_100.white_home_squares) == 30
    assert len(ASYMMETRIC_100.black_home_squares) == 30
    assert all(1 <= s.row <= 3 for s in ASYMMETRIC_100.white_home_squares)
    assert all(8 <= s.row <= 10 for s in ASYMMETRIC_100.black_home_squares)
    # Rows 4 and 7 are neutral buffer: neither home nor lake. This is the
    # geometry that makes `spacing_and_lanes` inert on Clash, so it is worth
    # pinning rather than reading off the row counts.
    buffer_squares = {
        Square(c, r) for r in (4, 7) for c in range(ASYMMETRIC_100.columns)
    }
    assert buffer_squares.isdisjoint(ASYMMETRIC_100.white_home_squares)
    assert buffer_squares.isdisjoint(ASYMMETRIC_100.black_home_squares)
    assert buffer_squares.isdisjoint(ASYMMETRIC_100.lake_squares)


def test_clash_lakes_split_the_lake_rows_evenly_but_unequally():
    # 10 lake and 10 open squares across the 2 x 10 lake zone -- the same 50:50
    # ratio the other two layouts have, distributed in blocks of 1, 1 and 3
    # columns rather than uniform 2s.
    assert len(ASYMMETRIC_100.lake_squares) == 10
    assert len(ASYMMETRIC_100.lane_squares) == 10
    assert all(s.row in (5, 6) for s in ASYMMETRIC_100.lake_squares)
    lake_columns = {s.column for s in ASYMMETRIC_100.lake_squares}
    assert lake_columns == {0, 3, 6, 7, 8}  # A, D, G-I
    lane_columns = {s.column for s in ASYMMETRIC_100.lane_squares}
    assert lane_columns == {1, 2, 4, 5, 9}  # B-C, E-F, J
    # Column A is a lake and column J a lane: the one published board that is not
    # open at both far edges, and not its own mirror image.
    assert ASYMMETRIC_100.is_lake(Square(0, 5))
    assert not ASYMMETRIC_100.is_lake(Square(9, 5))


def test_clash_home_zones_and_lakes_do_not_overlap():
    assert ASYMMETRIC_100.white_home_squares.isdisjoint(ASYMMETRIC_100.lake_squares)
    assert ASYMMETRIC_100.black_home_squares.isdisjoint(ASYMMETRIC_100.lake_squares)


def _squeezes(
    columns: int, rows: int, lake_squares: frozenset[Square] | set[Square]
) -> list[tuple[Square, Square]]:
    """Every diagonal on a board of this size whose two flanking squares are both
    lakes while its source and destination stay open — the *squeeze*.

    Written against a lake set and a size rather than a `BoardLayout` so it can
    be pointed at a hypothetical board too, which is what makes the assertion
    below more than a restatement of the type's own guarantees.
    """
    found = []
    for row in range(1, rows + 1):
        for column in range(columns):
            source = Square(column, row)
            for column_step, row_step in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                destination = Square(column + column_step, row + row_step)
                if not (
                    0 <= destination.column < columns and 1 <= destination.row <= rows
                ):
                    continue
                flanks = (
                    Square(destination.column, source.row),
                    Square(source.column, destination.row),
                )
                if (
                    source not in lake_squares
                    and destination not in lake_squares
                    and all(flank in lake_squares for flank in flanks)
                ):
                    found.append((source, destination))
    return found


def test_no_registered_layout_makes_the_diagonal_squeeze_reachable():
    # The *squeeze* is decided illegal in advance but deliberately left out of
    # `rules.md`, on the grounds that no published layout can produce one
    # (`technical-notes.md`, "Diagonal attacks and lakes"). That claim has to be
    # re-earned by every layout added, so this runs over the registry rather than
    # over any one board: a layout that made the squeeze reachable would reopen a
    # reserved rules decision, silently.
    #
    # It holds because every lake row shares one column pattern, not because the
    # published lakes are uniform 2x2 blocks -- `asymmetric_100`'s are 1, 1 and 3
    # columns wide and it is still unreachable.
    for layout in BOARD_LAYOUTS.values():
        assert not _squeezes(
            layout.columns, layout.rows, layout.lake_squares
        ), layout.layout_id


def test_the_squeeze_check_detects_one_when_it_exists():
    # Without this, the assertion above passes for a reason stronger than it
    # states and weaker than it appears: `BoardLayout` holds *one* lake pattern
    # shared by every lake row, so a squeeze is not merely absent from the
    # published layouts but inexpressible -- a lake column is lake in every lake
    # row, which makes the diagonal's own source or destination a lake.
    #
    # So the hypothetical is built by hand: two single-square lakes placed
    # diagonally, which is what per-row lake patterns would make possible. B1-A2
    # is squeezed between the lakes at A1 and B2. Naming the shape that would
    # trip the check is also the point -- it is the layout change that would send
    # the reserved decision to `rules.md`.
    lakes = {Square(0, 1), Square(1, 2)}
    # Both directions of the one diagonal: a squeeze is a property of the pair,
    # and either piece could be the attacker.
    assert set(_squeezes(4, 4, lakes)) == {
        (Square(1, 1), Square(0, 2)),
        (Square(0, 2), Square(1, 1)),
    }


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


def test_layout_rejects_a_lake_row_off_the_board():
    # Silent if unchecked: an off-board lake row is outside both home zones, so
    # it passes the check above, and every square it contributes is then filtered
    # out by `contains` — leaving a board with no lakes, no lanes, and a
    # `spacing_and_lanes` restriction that closes nothing.
    with pytest.raises(ValueError, match="is not on a 8-row board"):
        BoardLayout(
            layout_id="broken",
            columns=4,
            rows=8,
            home_rows=3,
            lake_rows=(4, 40),
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

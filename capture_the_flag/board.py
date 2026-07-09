"""Board geometry for Capture the Flag.

The board is 12 columns x 12 rows: two 4-row home zones separated by a doubled
neutral buffer and two rows of lakes. Coordinates follow the global, White's-
perspective frame used throughout the project (columns A-L left to right, rows
1-12 with row 1 as White's back rank and row 12 as Black's back rank) — see
`doc/ruleset/rules.md` Section 2.1 and `.local/game-notation-suggestion.md`.
"""

from typing import NamedTuple

BOARD_COLUMNS = 12
BOARD_ROWS = 12

# Lake layout across the 12 columns of each of the two lake rows:
# 1 open | 2 lake | 2 open | 2 lake | 2 open | 2 lake | 1 open — three separate
# 2x2 lakes with single-column lanes at the edges. True = lake (impassable),
# False = open.
_L = True
_O = False
LAKE_PATTERN = (_O, _L, _L, _O, _O, _L, _L, _O, _O, _L, _L, _O)

_COLUMN_LETTERS = "ABCDEFGHIJKL"

# Global row ranges (1-indexed), per the row-to-region map in rules.md 2.1.
WHITE_HOME_ROWS = range(1, 5)
LAKE_ROWS = (6, 7)
BLACK_HOME_ROWS = range(9, 13)


class Square(NamedTuple):
    """A board square in the global, White's-perspective coordinate frame.

    `column` is 0-indexed (0 = 'A' .. 11 = 'L'); `row` is 1-indexed (1 =
    White's back rank .. 12 = Black's back rank), matching the letter/number
    pair the rules and move notation use directly.
    """

    column: int
    row: int

    def __str__(self) -> str:
        return f"{_COLUMN_LETTERS[self.column]}{self.row}"


def parse_square(text: str) -> Square:
    """Parse a square in `<column-letter><row>` form (e.g. 'A4', 'L12').

    Inverse of `str(square)`.
    """
    letter, digits = text[0], text[1:]
    if letter not in _COLUMN_LETTERS or not digits.isdigit():
        raise ValueError(f"Malformed square: {text!r}")
    column = _COLUMN_LETTERS.index(letter)
    row = int(digits)
    if not (1 <= row <= BOARD_ROWS):
        raise ValueError(f"Row out of range: {text!r}")
    return Square(column, row)


def _zone_squares(rows: range) -> frozenset[Square]:
    return frozenset(Square(c, r) for r in rows for c in range(BOARD_COLUMNS))


# The two home zones: 4 rows x 12 columns = 48 squares each.
WHITE_HOME_SQUARES: frozenset[Square] = _zone_squares(WHITE_HOME_ROWS)
BLACK_HOME_SQUARES: frozenset[Square] = _zone_squares(BLACK_HOME_ROWS)

# Lake squares: the columns marked True in LAKE_PATTERN, across both lake rows.
LAKE_SQUARES: frozenset[Square] = frozenset(
    Square(c, r) for r in LAKE_ROWS for c in range(BOARD_COLUMNS) if LAKE_PATTERN[c]
)


def orthogonal_neighbors(square: Square) -> tuple[Square, ...]:
    """On-board squares one orthogonal step from `square` (up/down/left/right).

    Board-edge only: does not account for lakes or piece occupancy, which are
    move-legality concerns for later stories.
    """
    candidates = (
        Square(square.column, square.row + 1),
        Square(square.column, square.row - 1),
        Square(square.column + 1, square.row),
        Square(square.column - 1, square.row),
    )
    return tuple(
        s
        for s in candidates
        if 0 <= s.column < BOARD_COLUMNS and 1 <= s.row <= BOARD_ROWS
    )


def path_between(source: Square, destination: Square) -> tuple[Square, ...] | None:
    """Intermediate squares strictly between `source` and `destination`.

    Squares are returned in order walking from `source` to `destination`,
    exclusive of both endpoints, for a straight orthogonal line (same row or
    same column). Adjacent squares yield an empty tuple. Returns `None` if the
    squares are not collinear, or are the same square.
    """
    if source == destination:
        return None
    if source.column == destination.column:
        step = 1 if destination.row > source.row else -1
        return tuple(
            Square(source.column, r)
            for r in range(source.row + step, destination.row, step)
        )
    if source.row == destination.row:
        step = 1 if destination.column > source.column else -1
        return tuple(
            Square(c, source.row)
            for c in range(source.column + step, destination.column, step)
        )
    return None

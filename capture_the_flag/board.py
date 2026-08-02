"""Board geometry for Capture the Flag.

Since major 2 a board is a **rectangular grid of any size**, not a fixed 12x12:
two home zones of equal depth at the two ends, lake rows somewhere between them,
and any rows left over as neutral buffer. `BoardLayout` is that shape as a value,
and `STANDARD_144` is the Battle board expressed in it. Coordinates follow the
global, White's-perspective frame used throughout the project (columns lettered
from A left to right, rows numbered from 1 with row 1 as White's back rank) — see
`doc/ruleset/rules.md` Section 2.1 and Section 4.4.

**A layout is a value, never a module constant.** A `CtfPosition` carries the one
it is played on, which is the only way move generation can reach it:
`legal_plies` implements a `game-engine-core` protocol property and takes no
arguments, so the position is its sole channel. Code that reads geometry from
anywhere else is assuming a single board, which `doc/ruleset/CLAUDE.md` names as
a bug even when it happens to be right about Battle.
"""

from dataclasses import dataclass, field
from typing import NamedTuple

from .side import Side

# Single-letter column names run out at 26, which `technical-notes.md` records as
# the width at which the notation would need a new major.
_COLUMN_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
MAX_COLUMNS = len(_COLUMN_LETTERS)


class Square(NamedTuple):
    """A board square in the global, White's-perspective coordinate frame.

    `column` is 0-indexed (0 = 'A'); `row` is 1-indexed (1 = White's back rank),
    matching the letter/number pair the rules and move notation use directly.

    A `Square` is layout-independent: column 3 is 'D' on every board. Whether a
    given square is *on* a particular board is a `BoardLayout` question.
    """

    column: int
    row: int

    def __str__(self) -> str:
        return f"{_COLUMN_LETTERS[self.column]}{self.row}"


def parse_square(text: str) -> Square:
    """Parse a square in `<column-letter><row>` form (e.g. 'A4', 'L12').

    Inverse of `str(square)`. Validates the *notation* only — a column letter and
    a positive row number. Whether the square lies on a board is a question for
    that board's `BoardLayout`, which this function has no access to, and which a
    caller holding a position answers through `layout.contains`.
    """
    letter, digits = text[0], text[1:]
    if letter not in _COLUMN_LETTERS or not digits.isdigit():
        raise ValueError(f"Malformed square: {text!r}")
    row = int(digits)
    if row < 1:
        raise ValueError(f"Row out of range: {text!r}")
    return Square(_COLUMN_LETTERS.index(letter), row)


@dataclass(frozen=True)
class BoardLayout:
    """One complete board: grid dimensions, home-zone depth, and lake placement.

    A layout names a **complete** board rather than a size, which is what keeps
    board geometry from needing several independent axes — an 8x8 grid with two
    home rows instead of three is a different layout, not a parameter of this one
    (`rules.md` Appendix A, `BOARD_LAYOUT`).

    `layout_id` is the published `BOARD_LAYOUT` value label. It is permanent once
    published and is what a record or checkpoint resolves back to, so it belongs
    on the geometry rather than beside it.

    Rows run 1..`rows` from White's back rank. White's home zone is the first
    `home_rows` of them and Black's the last `home_rows`; whatever remains in the
    middle is lake rows and neutral buffer. Buffer rows are not stated because
    they are exactly the middle rows that are not lake rows.
    """

    layout_id: str
    columns: int
    rows: int
    home_rows: int
    lake_rows: tuple[int, ...]
    lake_pattern: tuple[bool, ...]
    """Per column, `True` where a lake row is lake and `False` where it is open.
    Every lake row shares this pattern, which is what makes a lake a rectangular
    block and a lane a full-height column through the middle of the board."""

    white_home_rows: range = field(init=False, compare=False, repr=False)
    black_home_rows: range = field(init=False, compare=False, repr=False)
    white_home_squares: frozenset[Square] = field(
        init=False, compare=False, repr=False
    )
    black_home_squares: frozenset[Square] = field(
        init=False, compare=False, repr=False
    )
    lake_squares: frozenset[Square] = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        # Derived members are excluded from equality: they are a function of the
        # defining fields, so comparing them would be comparing the same thing
        # twice, at the cost of walking two square sets.
        if not 1 <= self.columns <= MAX_COLUMNS:
            raise ValueError(
                f"{self.layout_id}: columns must be 1-{MAX_COLUMNS}, "
                f"got {self.columns}"
            )
        if len(self.lake_pattern) != self.columns:
            raise ValueError(
                f"{self.layout_id}: lake pattern covers {len(self.lake_pattern)} "
                f"columns, board has {self.columns}"
            )
        if self.home_rows < 1 or 2 * self.home_rows >= self.rows:
            raise ValueError(
                f"{self.layout_id}: {self.home_rows} home rows do not fit "
                f"{self.rows} rows with a gap between the two zones"
            )

        white_home = range(1, self.home_rows + 1)
        black_home = range(self.rows - self.home_rows + 1, self.rows + 1)
        # A lake inside a home zone would make placement geometry ill-defined and
        # is far more likely a typo in a new layout than an intended board.
        for row in self.lake_rows:
            if row in white_home or row in black_home:
                raise ValueError(
                    f"{self.layout_id}: lake row {row} lies inside a home zone"
                )

        object.__setattr__(self, "white_home_rows", white_home)
        object.__setattr__(self, "black_home_rows", black_home)
        object.__setattr__(self, "white_home_squares", self._zone(white_home))
        object.__setattr__(self, "black_home_squares", self._zone(black_home))
        object.__setattr__(
            self,
            "lake_squares",
            frozenset(
                Square(column, row)
                for row in self.lake_rows
                for column in range(self.columns)
                if self.lake_pattern[column]
            ),
        )

    def _zone(self, rows: range) -> frozenset[Square]:
        return frozenset(
            Square(column, row) for row in rows for column in range(self.columns)
        )

    @property
    def column_letters(self) -> str:
        """The column names in order, left to right ('A'..)."""
        return _COLUMN_LETTERS[: self.columns]

    def contains(self, square: Square) -> bool:
        """Whether `square` lies on this board at all (edges only, not lakes)."""
        return 0 <= square.column < self.columns and 1 <= square.row <= self.rows

    def is_lake(self, square: Square) -> bool:
        """Whether `square` is a lake, and so impassable to every piece."""
        return square in self.lake_squares

    def home_squares(self, side: Side) -> frozenset[Square]:
        """The home zone `side` places its army in (`rules.md` Section 3)."""
        return (
            self.white_home_squares
            if side is Side.WHITE
            else self.black_home_squares
        )

    def orthogonal_neighbors(self, square: Square) -> tuple[Square, ...]:
        """On-board squares one orthogonal step from `square`.

        Board-edge only: does not account for lakes or piece occupancy, which are
        move-legality concerns (see `moves.py`).
        """
        candidates = (
            Square(square.column, square.row + 1),
            Square(square.column, square.row - 1),
            Square(square.column + 1, square.row),
            Square(square.column - 1, square.row),
        )
        return tuple(s for s in candidates if self.contains(s))


_L = True
_O = False

STANDARD_144: BoardLayout = BoardLayout(
    layout_id="standard_144",
    columns=12,
    rows=12,
    home_rows=4,
    lake_rows=(6, 7),
    # 1 open | 2 lake | 2 open | 2 lake | 2 open | 2 lake | 1 open — three
    # separate 2x2 lakes, single-column lanes at the two edges and double-column
    # lanes through the interior (rules.md Section 2.1).
    lake_pattern=(_O, _L, _L, _O, _O, _L, _L, _O, _O, _L, _L, _O),
)
"""The Battle board: 12x12, 4 home / 1 buffer / 2 lake / 1 buffer / 4 home."""

STANDARD_64: BoardLayout = BoardLayout(
    layout_id="standard_64",
    columns=8,
    rows=8,
    home_rows=3,
    lake_rows=(4, 5),
    # The 12x12 pattern scaled down: two separate 2x2 lakes, single-column lanes
    # at the two edges and one double-column lane through the interior
    # (rules.md Section 2.1).
    lake_pattern=(_O, _L, _L, _O, _O, _L, _L, _O),
)
"""The Skirmish board: 8x8, 3 home / 2 lake / 3 home.

**No neutral buffer rows.** Each home zone sits directly against the lakes, so
the two front ranks start 3 rows apart instead of Battle's 4 and contact happens
sooner. That is deliberate — it is part of what makes Skirmish the faster game —
and it is also what puts a home-zone square directly in front of every lane,
which is the geometry the `TOWER_PLACEMENT` flag exists to address."""

BOARD_LAYOUTS: dict[str, BoardLayout] = {
    layout.layout_id: layout for layout in (STANDARD_144, STANDARD_64)
}
"""Every `BOARD_LAYOUT` value this build can actually play, keyed by its label.

Membership is *implementability*, not publication: `rules.md` Appendix A is what
publishes a value label, and a label published there but absent here is a board
this build cannot set up. `record.unsupported_aspects` is what turns that into a
legible refusal rather than a crash."""


def path_between(source: Square, destination: Square) -> tuple[Square, ...] | None:
    """Intermediate squares strictly between `source` and `destination`.

    Squares are returned in order walking from `source` to `destination`,
    exclusive of both endpoints, for a straight orthogonal line (same row or
    same column). Adjacent squares yield an empty tuple. Returns `None` if the
    squares are not collinear, or are the same square.

    Pure geometry, and layout-independent: what lies on the path is a board
    question, but which squares the path consists of is not.
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

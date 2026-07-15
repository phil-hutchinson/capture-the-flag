"""Placement files: a prepared phase-1 setup read from a text file.

A placement file is 4 rows of 12 characters, written from the owning player's
seat — the first line is the home row nearest the lakes, the last line the back
rank, columns left to right as that player sees them. Each character is either a
one-character piece symbol (`PieceType.symbol`: `1`-`6`, `T`, `F`) or `-` for an
empty square. The full 4×12 grid is always written even though only 25 of the 48
squares are filled, so every row is 12 characters, padding the rest with `-`. The
same file therefore produces the same setup for either side; mapping it onto
Black's home squares is a 180-degree rotation of the board frame.

`parse_placement_file` turns file text into a `Placement`;
`load_placement_file` first resolves a plain file name against the
placements folder (`placements/` by default, gitignored). Both raise
`PlacementFileError` with a player-facing message, in two vocabularies: a
file not in proper form (row count, row length, unknown character) is
reported structurally, while a well-formed file with the wrong piece mix is
reported as which piece types appear too many and too few times.
"""

from collections import Counter
from pathlib import Path

from .board import BLACK_HOME_ROWS, BOARD_COLUMNS, WHITE_HOME_ROWS, Square
from .pieces import ARMY_ROSTER, PIECE_BY_SYMBOL, PieceType
from .placement import Placement
from .side import Side

DEFAULT_PLACEMENT_DIR = Path("placements")
"""Default folder placement files are read from (gitignored)."""

_HOME_ROW_COUNT = len(WHITE_HOME_ROWS)
_EMPTY_SQUARE = "-"


class PlacementFileError(ValueError):
    """A placement file that cannot be used, with a player-facing message."""


def _square_for(side: Side, line_index: int, char_index: int) -> Square:
    if side is Side.WHITE:
        return Square(char_index, WHITE_HOME_ROWS.stop - 1 - line_index)
    return Square(BOARD_COLUMNS - 1 - char_index, BLACK_HOME_ROWS.start + line_index)


def _check_roster(placement: Placement) -> None:
    counts = Counter(placement.values())
    # The 25 filled squares must match the roster exactly; report every type
    # that appears too many or too few times (either can occur independently,
    # since the empty-square count is not fixed).
    too_many = [p for p in PieceType if counts[p] > ARMY_ROSTER[p]]
    too_few = [p for p in PieceType if counts[p] < ARMY_ROSTER[p]]
    if not too_many and not too_few:
        return

    def describe(pieces: list[PieceType]) -> str:
        return ", ".join(
            f"{p.piece_name} ({counts[p]} of {ARMY_ROSTER[p]})" for p in pieces
        )

    raise PlacementFileError(
        "Placement does not match the army roster — "
        f"too many: {describe(too_many)}; too few: {describe(too_few)}"
    )


def parse_placement_file(text: str, side: Side) -> Placement:
    """Parse placement-file `text` into a `Placement` for `side`.

    Raises `PlacementFileError` if the text is not 4 rows of 12 characters, each
    a known piece symbol or `-` (empty), or if the filled squares do not match
    the army roster.
    """
    lines = text.splitlines()
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) != _HOME_ROW_COUNT:
        raise PlacementFileError(
            f"Expected {_HOME_ROW_COUNT} rows of pieces, got {len(lines)}"
        )

    placement: dict[Square, PieceType] = {}
    for line_index, line in enumerate(lines):
        if len(line) != BOARD_COLUMNS:
            raise PlacementFileError(
                f"Row {line_index + 1} has {len(line)} characters, "
                f"expected {BOARD_COLUMNS}"
            )
        for char_index, symbol in enumerate(line):
            if symbol == _EMPTY_SQUARE:
                continue
            piece = PIECE_BY_SYMBOL.get(symbol)
            if piece is None:
                raise PlacementFileError(
                    f"Row {line_index + 1}: unknown piece character {symbol!r} "
                    f"(expected one of {', '.join(PIECE_BY_SYMBOL)} or "
                    f"{_EMPTY_SQUARE!r} for empty)"
                )
            placement[_square_for(side, line_index, char_index)] = piece

    _check_roster(placement)
    return placement


def load_placement_file(
    name: str, side: Side, directory: Path = DEFAULT_PLACEMENT_DIR
) -> Placement:
    """Load the placement file called `name` from `directory` for `side`.

    Raises `PlacementFileError` if no such file exists or if its content is
    rejected by `parse_placement_file`.
    """
    path = directory / name
    if not path.is_file():
        raise PlacementFileError(f"No placement file named {name!r} in {directory}/")
    return parse_placement_file(path.read_text(encoding="utf-8"), side)

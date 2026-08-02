"""Placement files: a prepared phase-1 setup read from a text file.

A placement file is one line per home-zone row, each as wide as the board,
written from the owning player's seat — the first line is the home row nearest
the lakes, the last line the back rank, columns left to right as that player sees
them. Each character is either a one-character piece symbol (`PieceType.symbol`:
`1`-`6`, `T`, `F`) or `-` for an empty square. The full grid is always written
even though a home zone holds more squares than the army fills, padding the rest
with `-`. The same file therefore produces the same setup for either side;
mapping it onto Black's home squares is a 180-degree rotation of the board frame.

**A file's shape identifies the board it is for**: Battle's home zone is 4 rows
of 12 and Skirmish's 3 rows of 8, so a file written for one board is rejected
against the other by the row-count and row-length checks, without needing a
ruleset marker of its own.

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

from .board import BoardLayout, Square
from .game_setup import GameSetup
from .pieces import PIECE_BY_SYMBOL, PieceType
from .placement import Placement
from .side import Side

DEFAULT_PLACEMENT_DIR = Path("placements")
"""Default folder placement files are read from (gitignored)."""

_EMPTY_SQUARE = "-"


class PlacementFileError(ValueError):
    """A placement file that cannot be used, with a player-facing message."""


def _square_for(
    side: Side, line_index: int, char_index: int, layout: BoardLayout
) -> Square:
    if side is Side.WHITE:
        return Square(char_index, layout.white_home_rows.stop - 1 - line_index)
    return Square(
        layout.columns - 1 - char_index, layout.black_home_rows.start + line_index
    )


def _check_roster(placement: Placement, setup: GameSetup) -> None:
    counts = Counter(placement.values())
    # The filled squares must match the army exactly; report every type that
    # appears too many or too few times (either can occur independently, since
    # the empty-square count is not fixed). Iterating `PieceType` rather than the
    # composition's own keys is what catches a piece the army does not field at
    # all -- a Militia in a Skirmish file is a surplus of a type whose count is 0.
    army = setup.composition
    too_many = [p for p in PieceType if counts[p] > army.count(p)]
    too_few = [p for p in PieceType if counts[p] < army.count(p)]
    if not too_many and not too_few:
        return

    def describe(pieces: list[PieceType]) -> str:
        return ", ".join(
            f"{p.piece_name} ({counts[p]} of {army.count(p)})" for p in pieces
        )

    raise PlacementFileError(
        "Placement does not match the army roster — "
        f"too many: {describe(too_many)}; too few: {describe(too_few)}"
    )


def parse_placement_file(text: str, side: Side, setup: GameSetup) -> Placement:
    """Parse placement-file `text` into a `Placement` for `side` under `setup`.

    Raises `PlacementFileError` if the text is not one row per home-zone row,
    each as wide as the board and made of known piece symbols or `-` (empty), or
    if the filled squares do not match the setup's army.
    """
    layout = setup.layout
    lines = text.splitlines()
    while lines and lines[-1] == "":
        lines.pop()
    if len(lines) != layout.home_rows:
        raise PlacementFileError(
            f"Expected {layout.home_rows} rows of pieces, got {len(lines)}"
        )

    placement: dict[Square, PieceType] = {}
    for line_index, line in enumerate(lines):
        if len(line) != layout.columns:
            raise PlacementFileError(
                f"Row {line_index + 1} has {len(line)} characters, "
                f"expected {layout.columns}"
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
            placement[_square_for(side, line_index, char_index, layout)] = piece

    _check_roster(placement, setup)
    return placement


def load_placement_file(
    name: str,
    side: Side,
    setup: GameSetup,
    directory: Path = DEFAULT_PLACEMENT_DIR,
) -> Placement:
    """Load the placement file called `name` from `directory` for `side`.

    Raises `PlacementFileError` if no such file exists or if its content is
    rejected by `parse_placement_file`.
    """
    path = directory / name
    if not path.is_file():
        raise PlacementFileError(f"No placement file named {name!r} in {directory}/")
    return parse_placement_file(path.read_text(encoding="utf-8"), side, setup)

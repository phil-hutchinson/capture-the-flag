"""Shared position-block text rendering and parsing.

Working spec: `.local/game-notation-suggestion.md`, promoted into
`technical-notes.md` in Story 00000004. Renders the full board from White's
perspective — the highest-numbered row at the top, row 1 at the bottom, column A
at the left — as one line per board row, cells space-separated. This is the same
string reused by the game-record file and the library-facing `text_board`.
`parse_position_block` is its inverse.

**The block is size-describing, not fully self-describing.** Since major 2 the
board is a rectangular grid of any size, so a reader recovers its *dimensions* by
counting lines and cells and its *lakes* from the `XXX` cells — which is why
parsing needs no layout, while rendering does. What the block cannot carry is the
home-zone row count: a mid-game position does not reveal where the home zones
were. Nothing here needs it, and anything that does reads it from the
configuration's `BOARD_LAYOUT` value.
"""

from collections.abc import Mapping

from .board import BoardLayout, Square
from .pieces import PIECE_BY_SYMBOL, PieceType
from .side import Side

Board = Mapping[Square, tuple[Side, PieceType]]


def _render_cell(square: Square, board: Board, layout: BoardLayout) -> str:
    occupant = board.get(square)
    if occupant is not None:
        side, piece = occupant
        return f"[{piece.symbol}]" if side is Side.WHITE else f"*{piece.symbol}*"
    if layout.is_lake(square):
        return "XXX"
    return "---"


def render_position_block(board: Board, layout: BoardLayout) -> str:
    """The position block for `board` on `layout`.

    One line per board row of space-separated 3-character cells: `[R]` a White
    piece, `*R*` a Black piece, `XXX` a lake, `---` an empty square. The
    highest-numbered row is the first line, row 1 the last; column A is the first
    cell of every line.
    """
    lines = []
    for row in range(layout.rows, 0, -1):
        cells = (
            _render_cell(Square(column, row), board, layout)
            for column in range(layout.columns)
        )
        lines.append(" ".join(cells))
    return "\n".join(lines)


def _parse_cell(cell: str) -> tuple[Side, PieceType] | None:
    if cell == "---" or cell == "XXX":
        return None
    if len(cell) == 3 and cell[0] == "[" and cell[2] == "]":
        return Side.WHITE, _piece_from_symbol(cell[1])
    if len(cell) == 3 and cell[0] == "*" and cell[2] == "*":
        return Side.BLACK, _piece_from_symbol(cell[1])
    raise ValueError(f"Malformed position-block cell: {cell!r}")


def _piece_from_symbol(symbol: str) -> PieceType:
    try:
        return PIECE_BY_SYMBOL[symbol]
    except KeyError:
        raise ValueError(f"Unknown piece symbol: {symbol!r}") from None


def parse_position_block(text: str) -> dict[Square, tuple[Side, PieceType]]:
    """Parse a position block (the inverse of `render_position_block`) into a
    board mapping. Accepts both LF and CRLF line endings.

    Takes no layout: the block states its own dimensions. Row count is the number
    of lines and column count the number of cells in each, so a reader never has
    to be told which board it is looking at — the property major 2's
    size-parametric notation exists to provide. The grid must be rectangular,
    which is the only shape check available without a layout to compare against.

    **What that gives up.** Before major 2 the dimensions were fixed, so a block
    of the wrong width was caught here. Now the first row *defines* the width, and
    a block that is uniformly wrong — 11 cells on every line of what should be a
    12-wide Battle record — parses cleanly into an 11-column board. Only a ragged
    block is detectable. Nothing in this repository reads records (see the module
    docstring), so there is no caller to hand a layout to and no signature here
    for one; a consumer that does read them, and knows which board it asked for,
    should compare the parsed dimensions against that board's `BoardLayout` rather
    than assume this function validated them.
    """
    lines = text.splitlines()
    if not lines:
        raise ValueError("Expected at least one board row, got none")

    rows = len(lines)
    columns = len(lines[0].split(" "))
    board: dict[Square, tuple[Side, PieceType]] = {}
    for line_index, line in enumerate(lines):
        row = rows - line_index
        cells = line.split(" ")
        if len(cells) != columns:
            raise ValueError(
                f"Row {row} has {len(cells)} cells, but the block's first row "
                f"has {columns}: a position block must be rectangular"
            )
        for column, cell in enumerate(cells):
            occupant = _parse_cell(cell)
            if occupant is not None:
                board[Square(column, row)] = occupant
    return board

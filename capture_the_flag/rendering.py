"""Shared position-block text rendering and parsing.

Working spec: `.local/game-notation-suggestion.md`, promoted into
`technical-notes.md` in Story 00000004. Renders the full 12x12 board from
White's perspective — row 12 at the top, row 1 at the bottom, column A at the
left — as one line per board row, cells space-separated. This is the same
string reused by the game-record file and the library-facing `text_board`.
`parse_position_block` is its exact inverse, used by the record reader.
"""

from collections.abc import Mapping

from .board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from .pieces import PieceType
from .side import Side

Board = Mapping[Square, tuple[Side, PieceType]]

_PIECE_BY_SYMBOL = {piece.symbol: piece for piece in PieceType}


def _render_cell(square: Square, board: Board) -> str:
    occupant = board.get(square)
    if occupant is not None:
        side, piece = occupant
        return f"[{piece.symbol}]" if side is Side.WHITE else f"*{piece.symbol}*"
    if square in LAKE_SQUARES:
        return "XXX"
    return "---"


def render_position_block(board: Board) -> str:
    """The position block for `board`.

    12 lines of 12 space-separated 3-character cells: `[R]` a White piece,
    `*R*` a Black piece, `XXX` a lake, `---` an empty square. Row 12 is the
    first line, row 1 the last; column A is the first cell of every line.
    """
    lines = []
    for row in range(BOARD_ROWS, 0, -1):
        cells = (
            _render_cell(Square(column, row), board) for column in range(BOARD_COLUMNS)
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
        return _PIECE_BY_SYMBOL[symbol]
    except KeyError:
        raise ValueError(f"Unknown piece symbol: {symbol!r}") from None


def parse_position_block(text: str) -> dict[Square, tuple[Side, PieceType]]:
    """Parse a position block (the inverse of `render_position_block`) into a
    board mapping. Accepts both LF and CRLF line endings.
    """
    lines = text.splitlines()
    if len(lines) != BOARD_ROWS:
        raise ValueError(f"Expected {BOARD_ROWS} board rows, got {len(lines)}")

    board: dict[Square, tuple[Side, PieceType]] = {}
    for line_index, line in enumerate(lines):
        row = BOARD_ROWS - line_index
        cells = line.split(" ")
        if len(cells) != BOARD_COLUMNS:
            raise ValueError(
                f"Expected {BOARD_COLUMNS} cells in row {row}, got {len(cells)}"
            )
        for column, cell in enumerate(cells):
            occupant = _parse_cell(cell)
            if occupant is not None:
                board[Square(column, row)] = occupant
    return board

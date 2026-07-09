"""Shared position-block text rendering.

Working spec: `.local/game-notation-suggestion.md` (promoted into
`technical-notes.md` in a later story). Renders the full 12x12 board from
White's perspective — row 12 at the top, row 1 at the bottom, column A at the
left — as one line per board row, cells space-separated. This is the same
string later reused by the game-record file and the library-facing
`text_board`.
"""

from .board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from .position import CtfPosition
from .side import Side


def _render_cell(square: Square, position: CtfPosition) -> str:
    occupant = position.board.get(square)
    if occupant is not None:
        side, piece = occupant
        return f"[{piece.symbol}]" if side is Side.WHITE else f"*{piece.symbol}*"
    if square in LAKE_SQUARES:
        return "XXX"
    return "---"


def render_position_block(position: CtfPosition) -> str:
    """The position block for `position`.

    12 lines of 12 space-separated 3-character cells: `[R]` a White piece,
    `*R*` a Black piece, `XXX` a lake, `---` an empty square. Row 12 is the
    first line, row 1 the last; column A is the first cell of every line.
    """
    lines = []
    for row in range(BOARD_ROWS, 0, -1):
        cells = (
            _render_cell(Square(column, row), position)
            for column in range(BOARD_COLUMNS)
        )
        lines.append(" ".join(cells))
    return "\n".join(lines)

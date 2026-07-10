"""Golden test for the position-block text rendering and parsing.

The expected output is the illustrative example from
`.local/game-notation-suggestion.md` (both sides given the same formation),
including the documented lake columns (B, C, F, G, J, K).
"""

from capture_the_flag.board import Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.rendering import parse_position_block, render_position_block
from capture_the_flag.side import Side

# One army's row-by-row formation (front to back), reused for both sides so
# the same 12-piece rows appear in the expected output for White and Black.
_BACK_RANK = [P.FLAG, *([P.TOWER] * 6), *([P.SAPPER] * 5)]
_ROW_2 = [P.SAPPER, P.SAPPER, P.ASSASSIN, *([P.ARCHER] * 3), *([P.SKIRMISHER] * 6)]
_ROW_3 = [*([P.MILITIA] * 6), *([P.HALBERDIER] * 6)]
_FRONT_RANK = [
    P.SAPPER,
    P.LORD_MARSHAL,
    P.CHAMPION,
    P.CHAMPION,
    *([P.KNIGHT] * 4),
    *([P.INFANTRY] * 4),
]

EXPECTED_BLOCK = "\n".join(
    [
        "*F* *T* *T* *T* *T* *T* *T* *9* *9* *9* *9* *9*",
        "*9* *9* *A* *8* *8* *8* *7* *7* *7* *7* *7* *7*",
        "*6* *6* *6* *6* *6* *6* *5* *5* *5* *5* *5* *5*",
        "*9* *1* *2* *2* *3* *3* *3* *3* *4* *4* *4* *4*",
        "--- --- --- --- --- --- --- --- --- --- --- ---",
        "--- XXX XXX --- --- XXX XXX --- --- XXX XXX ---",
        "--- XXX XXX --- --- XXX XXX --- --- XXX XXX ---",
        "--- --- --- --- --- --- --- --- --- --- --- ---",
        "[9] [1] [2] [2] [3] [3] [3] [3] [4] [4] [4] [4]",
        "[6] [6] [6] [6] [6] [6] [5] [5] [5] [5] [5] [5]",
        "[9] [9] [A] [8] [8] [8] [7] [7] [7] [7] [7] [7]",
        "[F] [T] [T] [T] [T] [T] [T] [9] [9] [9] [9] [9]",
    ]
)


def _row_board(side: Side, row: int, pieces: list[P]) -> dict[Square, tuple[Side, P]]:
    return {Square(col, row): (side, piece) for col, piece in enumerate(pieces)}


def _build_board() -> dict[Square, tuple[Side, P]]:
    board: dict[Square, tuple[Side, P]] = {}
    board.update(_row_board(Side.WHITE, 1, _BACK_RANK))
    board.update(_row_board(Side.WHITE, 2, _ROW_2))
    board.update(_row_board(Side.WHITE, 3, _ROW_3))
    board.update(_row_board(Side.WHITE, 4, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 9, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 10, _ROW_3))
    board.update(_row_board(Side.BLACK, 11, _ROW_2))
    board.update(_row_board(Side.BLACK, 12, _BACK_RANK))
    return board


def test_render_position_block_matches_golden_example():
    assert render_position_block(_build_board()) == EXPECTED_BLOCK


def test_render_position_block_has_twelve_lines_of_twelve_cells():
    lines = render_position_block(_build_board()).split("\n")
    assert len(lines) == 12
    for line in lines:
        cells = line.split(" ")
        assert len(cells) == 12
        assert all(len(cell) == 3 for cell in cells)


def test_parse_position_block_round_trips_through_render():
    board = _build_board()
    rendered = render_position_block(board)
    parsed = parse_position_block(rendered)
    assert parsed == board
    assert render_position_block(parsed) == rendered


def test_parse_position_block_accepts_crlf():
    rendered = render_position_block(_build_board())
    crlf_text = rendered.replace("\n", "\r\n")
    assert parse_position_block(crlf_text) == _build_board()

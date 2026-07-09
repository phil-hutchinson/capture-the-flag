"""Golden test for the position-block text rendering.

The expected output is the illustrative example from
`.local/game-notation-suggestion.md` (both sides given the same formation),
including the documented lake columns (B, C, F, G, J, K).
"""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.rendering import render_position_block
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


def _build_position() -> CtfPosition:
    board: dict[Square, tuple[Side, P]] = {}
    board.update(_row_board(Side.WHITE, 1, _BACK_RANK))
    board.update(_row_board(Side.WHITE, 2, _ROW_2))
    board.update(_row_board(Side.WHITE, 3, _ROW_3))
    board.update(_row_board(Side.WHITE, 4, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 9, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 10, _ROW_3))
    board.update(_row_board(Side.BLACK, 11, _ROW_2))
    board.update(_row_board(Side.BLACK, 12, _BACK_RANK))
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        white_inactivity_counter=0,
        black_inactivity_counter=0,
        progress_counter=0,
    )


def test_render_position_block_matches_golden_example():
    position = _build_position()
    assert render_position_block(position) == EXPECTED_BLOCK


def test_render_position_block_has_twelve_lines_of_twelve_cells():
    position = _build_position()
    lines = render_position_block(position).split("\n")
    assert len(lines) == 12
    for line in lines:
        cells = line.split(" ")
        assert len(cells) == 12
        assert all(len(cell) == 3 for cell in cells)

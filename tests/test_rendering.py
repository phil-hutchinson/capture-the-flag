"""Golden test for the position-block text rendering and parsing.

A representative setup (both sides given the same formation): one of each
numbered rank and a Flag in the two home rows, empty squares rendered as `---`.
"""

import pytest

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.rendering import parse_position_block, render_position_block
from capture_the_flag.side import Side

# One army's row-by-row formation, back rank first, reused for both sides. `None`
# marks an empty home square.
_BACK_RANK = [P.FLAG, P.MASTER_OF_ARMS, P.CHAMPION, P.FOOT_SOLDIER, P.MILITIA, P.PEASANT, None, None]
_FRONT_RANK = [P.MASTER_OF_ARMS, P.CHAMPION, P.FOOT_SOLDIER, P.MILITIA, P.PEASANT, None, None, None]

EXPECTED_BLOCK = "\n".join(
    [
        "*F* *5* *4* *3* *2* *1* --- ---",
        "*5* *4* *3* *2* *1* --- --- ---",
        "--- --- --- --- --- --- --- ---",
        "--- --- --- --- --- --- --- ---",
        "--- --- --- --- --- --- --- ---",
        "--- --- --- --- --- --- --- ---",
        "[5] [4] [3] [2] [1] --- --- ---",
        "[F] [5] [4] [3] [2] [1] --- ---",
    ]
)


def _row_board(side: Side, row: int, pieces) -> dict[Square, tuple[Side, P]]:
    return {
        Square(col, row): (side, piece)
        for col, piece in enumerate(pieces)
        if piece is not None
    }


def _build_board() -> dict[Square, tuple[Side, P]]:
    board: dict[Square, tuple[Side, P]] = {}
    board.update(_row_board(Side.WHITE, 1, _BACK_RANK))
    board.update(_row_board(Side.WHITE, 2, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 7, _FRONT_RANK))
    board.update(_row_board(Side.BLACK, 8, _BACK_RANK))
    return board


def test_render_position_block_matches_golden_example():
    assert render_position_block(_build_board(), SIMPLE_64) == EXPECTED_BLOCK


def test_render_position_block_has_eight_lines_of_eight_cells():
    lines = render_position_block(_build_board(), SIMPLE_64).split("\n")
    assert len(lines) == 8
    for line in lines:
        cells = line.split(" ")
        assert len(cells) == 8
        assert all(len(cell) == 3 for cell in cells)


def test_parse_position_block_round_trips_through_render():
    board = _build_board()
    rendered = render_position_block(board, SIMPLE_64)
    parsed = parse_position_block(rendered)
    assert parsed == board
    assert render_position_block(parsed, SIMPLE_64) == rendered


def test_parse_position_block_accepts_crlf():
    rendered = render_position_block(_build_board(), SIMPLE_64)
    crlf_text = rendered.replace("\n", "\r\n")
    assert parse_position_block(crlf_text) == _build_board()


def test_parse_position_block_reads_its_own_dimensions():
    # The block states its size: three rows of four cells parse as a 4x3 board
    # with no layout supplied. This is the size-parametric property major 2's
    # notation exists to provide.
    block = "\n".join(["--- *F* --- ---", "--- --- --- [2]", "[5] --- --- ---"])
    parsed = parse_position_block(block)
    assert parsed == {
        Square(1, 3): (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.MILITIA),
        Square(0, 1): (Side.WHITE, P.MASTER_OF_ARMS),
    }


def test_parse_position_block_rejects_a_ragged_grid():
    with pytest.raises(ValueError, match="must be rectangular"):
        parse_position_block("--- --- ---\n--- ---")


def test_parse_position_block_rejects_the_retired_lake_cell():
    # `XXX` named a lake cell before major 3 deleted lakes from `BoardLayout`
    # (story 00000049 step 4); it is no longer a recognised token.
    with pytest.raises(ValueError, match="Malformed position-block cell"):
        parse_position_block("--- XXX ---")

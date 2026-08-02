"""The interactive game view: everything two players need on screen.

Composes the shared position block — labelled with the coordinate frame the
move notation uses, which the record format leaves off — with the game status
read straight from a `CtfPosition`: whose turn it is, each side's captured
pieces so far (derived by diffing the board against the army roster, so no
capture history is threaded through the game), and the shared inactivity
counter against its limit, so players can apply the inactivity rule
(Section 5.3).
"""

from collections import Counter

from .game_setup import GameSetup
from .outcome import INACTIVITY_LIMIT
from .pieces import PieceType
from .position import CtfPosition
from .rendering import render_position_block
from .side import Side


def _labelled_board(position: CtfPosition) -> str:
    # Row labels are 2 characters wide plus 2 of gap, so each column letter
    # sits over the middle character of its 3-character cell.
    layout = position.layout
    header = "    " + " ".join(f" {letter} " for letter in layout.column_letters)
    block_lines = render_position_block(position.board, layout).splitlines()
    rows = (
        f"{layout.rows - index:>2}  {line}"
        for index, line in enumerate(block_lines)
    )
    return "\n".join([header, *rows])


def _captured_summary(position: CtfPosition, setup: GameSetup, side: Side) -> str:
    on_board = Counter(
        piece for piece_side, piece in position.board.values() if piece_side is side
    )
    parts = []
    for piece in PieceType:
        missing = setup.composition.count(piece) - on_board[piece]
        if missing > 0:
            parts.append(
                f"{piece.piece_name} x{missing}" if missing > 1 else piece.piece_name
            )
    return ", ".join(parts) if parts else "none"


def render_game_view(position: CtfPosition, setup: GameSetup) -> str:
    """The full game view for `position`: labelled board, turn, captures, clocks.

    `setup` supplies the army the captured tally is measured against -- what is
    missing from the board is only meaningful against the army that started on
    it, and the position alone does not carry that.
    """
    side_name = position.side_to_move.name.title()
    return (
        f"{_labelled_board(position)}\n"
        f"\n"
        f"{side_name} to move\n"
        f"Captured — White: {_captured_summary(position, setup, Side.WHITE)}\n"
        f"Captured — Black: {_captured_summary(position, setup, Side.BLACK)}\n"
        f"Inactivity — {position.inactivity_counter}/{INACTIVITY_LIMIT}"
    )

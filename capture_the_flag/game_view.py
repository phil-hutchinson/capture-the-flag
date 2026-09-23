"""The interactive game view: everything two players need on screen.

Composes the shared position block — labelled with the coordinate frame the
move notation uses, which the record format leaves off — with the game status
read straight from a `CtfPosition`: whose turn it is, a census of each side's
standing pieces by rank, and the shared inactivity counter against its limit,
so players can apply the inactivity rule (Section 5.4).

**Standing pieces rather than captured ones**, since rank reduction
(Section 4.3): a piece that survives combat leaves its rank without leaving the
board, so "what has this side lost" no longer reads off the ranks the way it
does in a game with fixed pieces — a rank can *gain* members mid-game. What is
standing is the quantity the rules actually turn on. Its total is the attrition
clock exactly as `inactivity_counter` is the inactivity clock: a side reaches
zero numbered pieces and loses on the spot (Section 5.2), which is why the
Flag, which never counts toward that and only leaves the board by ending the
game, is left out of the census.
"""

from collections import Counter

from .game_setup import GameSetup
from .outcome import INACTIVITY_LIMIT
from .pieces import PieceType
from .position import CtfPosition
from .rendering import render_position_block
from .side import Side

# Wide enough for a two-digit count: `12xR1`.
_CELL_WIDTH = 5


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


def _standing_summary(position: CtfPosition, setup: GameSetup, side: Side) -> str:
    """`side`'s numbered pieces by rank, then the total against its army size.

    Every rank is listed whether or not any survive: the ranks hold still so
    the two sides' lines can be compared column against column, and so a rank
    emptying reads as the `0x` it is rather than as a piece silently dropping
    out of the line. Cells are padded to a fixed width for the same reason —
    rank reduction can push a rank's population into two digits without
    shifting the columns beside it.
    """
    on_board = Counter(
        piece for piece_side, piece in position.board.values() if piece_side is side
    )
    numbered = [piece for piece in PieceType if piece.rank is not None]
    cells = " ".join(
        f"{on_board[piece]}xR{piece.rank}".ljust(_CELL_WIDTH) for piece in numbered
    )
    standing = sum(on_board[piece] for piece in numbered)
    army = setup.composition.size - setup.composition.count(PieceType.FLAG)
    return f"{cells} — {standing:>2} of {army}"


def render_game_view(position: CtfPosition, setup: GameSetup) -> str:
    """The full game view for `position`: labelled board, turn, armies, clocks.

    `setup` supplies the army size each census is reported against. The census
    itself is read off the board alone; the starting size is what turns it into
    "how much of my army is left", and the position does not carry that.
    """
    side_name = position.side_to_move.name.title()
    return (
        f"{_labelled_board(position)}\n"
        f"\n"
        f"{side_name} to move\n"
        f"Standing — White: {_standing_summary(position, setup, Side.WHITE)}\n"
        f"Standing — Black: {_standing_summary(position, setup, Side.BLACK)}\n"
        f"Inactivity — {position.inactivity_counter}/{INACTIVITY_LIMIT}"
    )

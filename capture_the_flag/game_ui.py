"""`game-engine-core`'s `GameUI` implementation for Capture the Flag.

Interactive display and input only; game-record rendering (`text_board`,
`ply_annotation`) lives in `CtfGameLogging` since v0.1.1 split the two.
"""

from collections.abc import Callable

from game_engine_core.protocols.game_ui import GameUI

from .game_setup import GameSetup
from .game_view import render_game_view
from .moves import (
    diagonal_flank_squares,
    diagonal_path_is_open,
    is_encumbered_in_direction,
)
from .ply import CtfPly, parse_ply
from .position import CtfPosition
from .side import Side


class CtfGameUI(GameUI[CtfPly, CtfPosition]):
    """Interactive board display and human move entry for a `CtfPosition`.

    `setup` is the board and army being played. The `GameUI` protocol hands
    `render_board` a position and nothing else, and the standing-piece census
    is reported against the army that started on the board, which a position
    does not carry -- so the UI holds it for the life of the game.

    It is required, and first, for the reason `CtfPosition.layout` carries no
    default: a UI that silently fell back to some other board and army would
    measure each side's remaining strength against an army the game never
    fielded. A wrong board is worth a `TypeError` at construction; it is not
    worth a plausible-looking display.

    `input_fn` and `print_fn` default to the builtins; tests inject scripted
    replacements.
    """

    def __init__(
        self,
        setup: GameSetup,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._print = print_fn
        self._setup = setup

    def render_board(self, position: CtfPosition) -> None:
        self._print(render_game_view(position, self._setup))

    def get_next_ply(self, position: CtfPosition) -> CtfPly:
        """Prompt for a move in simple notation until a legal ply is entered.

        Malformed and illegal input each print a message and re-prompt; game
        state is untouched throughout. Input is case-insensitive.
        """
        prompt = (
            f"{position.side_to_move.name.title()} to move — "
            f"enter move (e.g. A2A3): "
        )
        while True:
            text = self._input(prompt).strip().upper()
            try:
                ply = parse_ply(text)
            except ValueError as error:
                self._print(str(error))
                continue
            if ply in position.legal_plies:
                return ply
            self._print(_illegal_reason(position, ply))


def _illegal_reason(position: CtfPosition, ply: CtfPly) -> str:
    """Why `ply` was refused, naming the rule that refused it where the rule is
    one a player can run into without seeing it.

    Four of the major-3 restrictions refuse plies that look perfectly ordinary
    on the board -- a diagonal onto an empty square, a diagonal whose path is
    closed, a two-square move encumbered *in that direction*, and White's first
    ply -- and each gets a message that says which rule was applied. The rest
    fall through to a generic refusal: a friendly occupant, a blocked path, an
    off-board destination and an immobile Flag are all visible in the position
    itself, so naming the rule adds nothing a player cannot already see.
    """
    occupant = position.board.get(ply.source)
    if occupant is None:
        return f"Illegal move: no piece on {ply.source}."
    side, piece = occupant
    if side is not position.side_to_move:
        return f"Illegal move: the piece on {ply.source} is not yours."
    detail = _refused_rule(position, ply, side) or (
        f"cannot move to {ply.destination}."
    )
    return f"Illegal move: your {piece.piece_name} on {ply.source} {detail}"


def _refused_rule(position: CtfPosition, ply: CtfPly, side: Side) -> str | None:
    """The clause explaining `ply`, or `None` to fall back to the generic one.

    Selected by the *shape* of the ply rather than by asking the generator why
    it declined: the shape is what picks out the restriction a player has run
    into, and every other shape is refused for a reason already on the board.
    """
    dc = ply.destination.column - ply.source.column
    dr = ply.destination.row - ply.source.row
    if abs(dc) == 1 and abs(dr) == 1:
        return _diagonal_refusal(position, ply, side, (dc, dr))
    if {abs(dc), abs(dr)} == {0, 2}:
        return _two_square_refusal(position, ply, side, (dc, dr))
    return None


def _diagonal_refusal(
    position: CtfPosition, ply: CtfPly, side: Side, direction: tuple[int, int]
) -> str | None:
    occupant = position.board.get(ply.destination)
    if occupant is None:
        return (
            f"can only move diagonally to attack, and {ply.destination} is "
            f"empty (Section 4.4)."
        )
    if occupant[0] is side:
        return None
    if not diagonal_path_is_open(position, ply.source, direction):
        flank_a, flank_b = diagonal_flank_squares(ply.source, direction)
        return (
            f"cannot attack {ply.destination} diagonally: the path is closed — "
            f"a diagonal attack needs {flank_a} or {flank_b} empty, and both "
            f"are occupied (Section 4.4)."
        )
    return None


def _two_square_refusal(
    position: CtfPosition, ply: CtfPly, side: Side, direction: tuple[int, int]
) -> str | None:
    if position.ply_count == 0:
        return (
            f"cannot move two squares to {ply.destination}: White's first move "
            f"of the game is limited to one square (Section 4.1)."
        )
    # Exactly one of the two deltas is +/-2 and the other 0, so halving gives
    # the unit direction of travel.
    dc, dr = direction
    if is_encumbered_in_direction(position, ply.source, side, (dc // 2, dr // 2)):
        return (
            f"cannot move two squares to {ply.destination}: it is encumbered in "
            f"that direction — an enemy piece stands ahead of or beside it on "
            f"one of the five squares that direction is measured over "
            f"(Section 4.2). Its other directions are unaffected."
        )
    return None

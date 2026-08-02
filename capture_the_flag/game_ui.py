"""`game-engine-core`'s `GameUI` implementation for Capture the Flag.

Interactive display and input only; game-record rendering (`text_board`,
`ply_annotation`) lives in `CtfGameLogging` since v0.1.1 split the two.
"""

from collections.abc import Callable

from game_engine_core.protocols.game_ui import GameUI

from .game_setup import GameSetup
from .game_view import render_game_view
from .ply import CtfPly, parse_ply
from .position import CtfPosition


class CtfGameUI(GameUI[CtfPly, CtfPosition]):
    """Interactive board display and human move entry for a `CtfPosition`.

    `setup` is the board and army being played. The `GameUI` protocol hands
    `render_board` a position and nothing else, and the captured-piece tally
    needs the army that started on the board, which a position does not carry --
    so the UI holds it for the life of the game.

    It is required, and first, for the reason `CtfPosition.layout` carries no
    default: a UI that fell back to Battle would not fail on a Skirmish game, it
    would tally the captures against the wrong army and report ranks the game
    never fielded as missing. A wrong board is worth a `TypeError` at
    construction; it is not worth a plausible-looking display.

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
    occupant = position.board.get(ply.source)
    if occupant is None:
        return f"Illegal move: no piece on {ply.source}."
    side, piece = occupant
    if side is not position.side_to_move:
        return f"Illegal move: the piece on {ply.source} is not yours."
    return (
        f"Illegal move: your {piece.piece_name} on {ply.source} "
        f"cannot move to {ply.destination}."
    )

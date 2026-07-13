"""`game-engine-core`'s `GameUI` implementation for Capture the Flag.

Interactive display and input only; game-record rendering (`text_board`,
`ply_annotation`) lives in `CtfGameLogging` since v0.1.1 split the two.
"""

from game_engine_core.protocols.game_ui import GameUI

from .ply import CtfPly
from .position import CtfPosition
from .rendering import render_position_block


class CtfGameUI(GameUI[CtfPly, CtfPosition]):
    """Interactive board display for a `CtfPosition`. Human ply input
    (`get_next_ply`) is deferred to the text-UI story (00000005)."""

    def render_board(self, position: CtfPosition) -> None:
        print(render_position_block(position.board))

    def get_next_ply(self, position: CtfPosition) -> CtfPly:
        raise NotImplementedError(
            "Human ply input is implemented in the text-UI story (00000005)."
        )

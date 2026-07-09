"""`game-engine-core`'s `GameUI` implementation for Capture the Flag."""

from game_engine_core.protocols.game_ui import GameUI

from .ply import CtfPly
from .position import CtfPosition
from .rendering import render_position_block


class CtfGameUI(GameUI[CtfPly, CtfPosition]):
    """Text rendering for a `CtfPosition`. Human ply input (`get_next_ply`)
    is deferred to the text-UI story (00000005)."""

    def text_board(self, position: CtfPosition) -> str:
        return render_position_block(position)

    def render_board(self, position: CtfPosition) -> None:
        print(self.text_board(position))

    def get_next_ply(self, position: CtfPosition) -> CtfPly:
        raise NotImplementedError(
            "Human ply input is implemented in the text-UI story (00000005)."
        )

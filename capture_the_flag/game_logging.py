"""`game-engine-core`'s `GameLogging` implementation for Capture the Flag.

v0.1.1 split game-record rendering (`text_board`, `ply_annotation`) out of the
interactive `GameUI` so headless play needs no UI. `text_board` moves here from
the old `CtfGameUI`; `ply_annotation` is the string logged for an executed ply.

The annotation is a placeholder (`str(ply)`, the plain source-destination form)
until Step 4 replaces it with the combat notation from `rules.md` Section 4.4.
The plain form remains the ply's identity (`CtfPly.__str__`) regardless.
"""

from game_engine_core.protocols.game_logging import GameLogging

from .ply import CtfPly
from .position import CtfPosition
from .rendering import render_position_block


class CtfGameLogging(GameLogging[CtfPly, CtfPosition]):
    """Game-record rendering for a `CtfPosition`."""

    def text_board(self, position: CtfPosition) -> str:
        return render_position_block(position.board)

    def ply_annotation(
        self,
        from_position: CtfPosition,
        ply: CtfPly,
        to_position: CtfPosition,
    ) -> str:
        # Placeholder: combat notation (rules.md Section 4.4) lands in Step 4.
        return str(ply)

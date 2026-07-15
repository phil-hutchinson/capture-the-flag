"""`game-engine-core`'s `GameLogging` implementation for Capture the Flag.

v0.1.1 split game-record rendering (`text_board`, `ply_annotation`) out of the
interactive `GameUI` so headless play needs no UI. `text_board` moves here from
the old `CtfGameUI`; `ply_annotation` is the string logged for an executed ply.

`ply_annotation` renders the combat notation from `rules.md` Section 4.4 (the
`-`/`x` form). The plain source-destination form remains the ply's identity
(`CtfPly.__str__`) regardless; only the logged/record string differs.
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
        """Combat notation for an executed ply (`rules.md` Section 4.4).

        The extended form always separates the squares with `-`, with an `x`
        immediately after a square when the piece that stood there did not
        survive the ply:

        - `A4-A5`  — a move with no attack
        - `A4-A5x` — the attacker wins (defender removed)
        - `A4x-A5` — the attacker loses (complete sacrifice)
        - `A4x-A5x` — mutual loss (a trade)

        Survival is read straight off the resulting board, so every combat
        nuance (equal-rank trades, the formation bonus, tower destruction, …) is
        reflected without re-deriving the combat result here.
        """
        source, destination = ply.source, ply.destination
        mover_side = from_position.side_to_move
        defender = from_position.board.get(destination)

        # No enemy on the destination square: a plain move, not an attack. (A
        # legal ply never lands on a friendly piece, but guard for it anyway.)
        if defender is None or defender[0] is mover_side:
            return f"{source}-{destination}"

        # An attack: mark whichever pieces are gone from the resulting board.
        after = to_position.board.get(destination)
        attacker_mark = "" if after is not None and after[0] is mover_side else "x"
        defender_mark = "" if after is not None and after[0] is not mover_side else "x"
        return f"{source}{attacker_mark}-{destination}{defender_mark}"

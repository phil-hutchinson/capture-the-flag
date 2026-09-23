"""`game-engine-core`'s `GameLogging` implementation for Capture the Flag.

v0.1.1 split game-record rendering (`text_board`, `ply_annotation`) out of the
interactive `GameUI` so headless play needs no UI. `text_board` moves here from
the old `CtfGameUI`; `ply_annotation` is the string logged for an executed ply.

`ply_annotation` renders the move notation from `rules.md` Section 4.5. The
plain source-destination form (`CtfPly.__str__`) is input-only -- it cannot
carry the marks below, so it is never used to record a game.
"""

from game_engine_core.protocols.game_logging import GameLogging

from .pieces import PieceType
from .ply import CtfPly
from .position import CtfPosition
from .rendering import render_position_block


class CtfGameLogging(GameLogging[CtfPly, CtfPosition]):
    """Game-record rendering for a `CtfPosition`."""

    def text_board(self, position: CtfPosition) -> str:
        return render_position_block(position.board, position.layout)

    def ply_annotation(
        self,
        from_position: CtfPosition,
        ply: CtfPly,
        to_position: CtfPosition,
    ) -> str:
        """Move notation for an executed ply (`rules.md` Section 4.5).

        The two squares are separated by `-`. In combat, each square carries
        exactly one mark describing the piece that stood there when the move
        began -- `x` if it did not survive, `=N` if it survived as rank `N` --
        except a Flag capture, which marks only the destination (`x`); the
        Flag does not fight, so the attacker is never marked:

        - `A4-A5`     — a move with no attack
        - `A4=3-A5x`  — the attacker won and is reduced to rank 3
        - `A4x-A5=2`  — the attacker lost; the defender is reduced to rank 2
        - `A4x-A5x`   — mutual loss (a trade)
        - `A4-A5x`    — the Flag on A5 was captured

        Survival and the reduced rank are read straight off the resulting
        board, so every combat nuance (equal-rank trades, the formation
        bonus, …) is reflected without re-deriving the combat result here.
        """
        source, destination = ply.source, ply.destination
        mover_side = from_position.side_to_move
        defender = from_position.board.get(destination)

        # No enemy on the destination square: a plain move, not an attack. (A
        # legal ply never lands on a friendly piece, but guard for it anyway.)
        if defender is None or defender[0] is mover_side:
            return f"{source}-{destination}"

        # Capturing the Flag is not combat: the attacker is never marked, and
        # always survives at the destination unreduced (rules.md Section 4.5).
        if defender[1] is PieceType.FLAG:
            return f"{source}-{destination}x"

        # Ordinary combat: whichever side is still standing at the destination
        # survived, reduced to the rank now recorded there; the other side's
        # piece is gone.
        after = to_position.board.get(destination)
        if after is not None and after[0] is mover_side:
            return f"{source}={after[1].rank}-{destination}x"
        if after is not None and after[0] is not mover_side:
            return f"{source}x-{destination}={after[1].rank}"
        return f"{source}x-{destination}x"

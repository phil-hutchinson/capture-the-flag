"""Immutable game-state container for Capture the Flag.

`CtfPosition` fully implements `game-engine-core`'s `GamePosition` protocol:
board occupancy, side to move, the single inactivity counter (rules.md Section
5.3), plus `legal_plies`, `apply_ply`, `outcome`, and `outcome_reason`, which are
computed from that state.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .board import Square
from .moves import legal_plies as _legal_plies
from .outcome import compute_outcome as _compute_outcome
from .outcome import compute_outcome_reason as _compute_outcome_reason
from .pieces import PieceType
from .ply import CtfPly
from .side import Side


@dataclass(frozen=True)
class CtfPosition:
    """A single, immutable point-in-time game state.

    `board` maps an occupied square to the `(Side, PieceType)` standing on it; a
    square absent from `board` is empty. `inactivity_counter` is the single
    shared clock (rules.md Section 5.3): it rises by 1 on every non-capturing ply
    and resets to 0 on any attack that removes a piece.
    """

    board: Mapping[Square, tuple[Side, PieceType]]
    side_to_move: Side
    inactivity_counter: int

    @property
    def active_player_id(self) -> Literal[1, -1]:
        """`game-engine-core`'s `active_player_id`: 1 for White, -1 for Black."""
        return 1 if self.side_to_move is Side.WHITE else -1

    @property
    def legal_plies(self) -> tuple[CtfPly, ...]:
        """Every legal ply for the side to move (rules.md Section 4.2)."""
        return _legal_plies(self)

    def apply_ply(self, ply: CtfPly) -> "CtfPosition":
        """The successor position after applying `ply` (rules.md Sections
        4.3, 5.3)."""
        from .transitions import apply_ply as _apply_ply

        return _apply_ply(self, ply)

    @property
    def outcome(self) -> Literal[1, 0, -1] | None:
        """Current-player-relative outcome (rules.md Section 5)."""
        return _compute_outcome(self)

    @property
    def outcome_reason(self) -> str | None:
        """Why the game ended (rules.md Section 5): a short label once `outcome`
        is non-`None`, else `None`. Recorded as `ResultReason` in game records."""
        return _compute_outcome_reason(self)

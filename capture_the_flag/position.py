"""Immutable game-state container for Capture the Flag.

`CtfPosition` fully implements `game-engine-core`'s `GamePosition` protocol:
board occupancy, side to move, the three clocks (Sections 6.4-6.5), and the
cached Unbreachable Flag data (Section 6.2), plus `legal_plies`,
`apply_ply`, and `outcome`, which are computed from that state.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .board import Square
from .breachability import BreachabilityCache
from .moves import legal_plies as _legal_plies
from .outcome import compute_outcome as _compute_outcome
from .pieces import PieceType
from .ply import CtfPly
from .side import Side


@dataclass(frozen=True)
class CtfPosition:
    """A single, immutable point-in-time game state.

    `board` maps an occupied square to the `(Side, PieceType)` standing on
    it; a square absent from `board` is empty. `breachability` is `None`
    until a later story populates and maintains it.
    """

    board: Mapping[Square, tuple[Side, PieceType]]
    side_to_move: Side
    white_inactivity_counter: int
    black_inactivity_counter: int
    progress_counter: int
    breachability: BreachabilityCache | None = None

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
        4.3, 6.4, 6.5)."""
        from .transitions import apply_ply as _apply_ply

        return _apply_ply(self, ply)

    @property
    def outcome(self) -> Literal[1, 0, -1] | None:
        """Current-player-relative outcome (rules.md Section 6)."""
        return _compute_outcome(self)

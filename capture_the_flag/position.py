"""Immutable game-state container for Capture the Flag.

`CtfPosition` will implement `game-engine-core`'s `GamePosition` protocol once
move generation (`legal_plies`), combat and transitions (`apply_ply`), and
endings (`outcome`) land in later stories. This module carries the state
itself: board occupancy, side to move, the three clocks (Sections 6.4-6.5),
and a slot for the cached Unbreachable Flag data (Section 6.2) that a later
story computes and maintains.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, NamedTuple

from .board import Square
from .pieces import PieceType
from .side import Side


class BreachabilityCache(NamedTuple):
    """Cached Unbreachable Flag (rules.md Section 6.2) inputs for both sides.

    `<side>_flag_enclosed` is whether that side's Flag is walled off by its
    own intact Towers (and the board edge). `<side>_sappers_available` is
    whether that side has at least one Sapper currently able to reach an
    enemy Tower. A side wins when its own flag is enclosed and the opponent's
    Sappers are all unavailable.
    """

    white_flag_enclosed: bool
    black_flag_enclosed: bool
    white_sappers_available: bool
    black_sappers_available: bool


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

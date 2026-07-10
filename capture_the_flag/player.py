"""The `CtfPlayer` seam (phase-1 placement + phase-2 play) and a random
player implementation."""

import random
from typing import Protocol

from game_engine_core.engines.random_engine import RandomEngine
from game_engine_core.protocols.player import Player

from .placement import Placement, random_placement
from .ply import CtfPly
from .position import CtfPosition
from .side import Side


class CtfPlayer(Player[CtfPly, CtfPosition], Protocol):
    """A `Player` that can also produce a phase-1 placement.

    A match wrapper calls `get_placement` for each side before phase 2
    begins, then hands the resulting `CtfPosition` to the library's
    `StandardGame`, which drives `select_ply` as usual.
    """

    def get_placement(self, side: Side) -> Placement:
        """This player's phase-1 home-zone placement for `side`."""
        ...


class RandomCtfPlayer:
    """A `CtfPlayer` that places uniformly at random and moves uniformly at
    random."""

    def __init__(
        self,
        name: str,
        rng: random.Random | None = None,
        render_before_ply: bool = False,
    ) -> None:
        self._name = name
        self._rng = rng if rng is not None else random.Random()
        self._render_before_ply = render_before_ply
        self._engine: RandomEngine[CtfPly, CtfPosition] = RandomEngine()

    @property
    def name(self) -> str:
        return self._name

    @property
    def render_before_ply(self) -> bool:
        return self._render_before_ply

    def get_placement(self, side: Side) -> Placement:
        return random_placement(side, self._rng)

    def select_ply(self, position: CtfPosition) -> CtfPly:
        return self._engine.select_ply(position)

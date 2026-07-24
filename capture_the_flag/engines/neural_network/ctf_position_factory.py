from random import Random

from ...placement import assemble_position, random_placement
from ...position import CtfPosition
from ...side import Side


class CtfPositionFactory:
    """Zero-arg starting-position factory for self-play: a fresh random placement
    per side, assembled into a phase-2 start position.

    `rng` is injectable so a seeded run draws reproducible placements; it defaults
    to an unseeded `Random`. The instance is held across calls, so a seeded rng
    produces a deterministic *sequence* of placements (self-play games still
    diverge) rather than the same board every game.
    """

    def __init__(self, rng: Random | None = None) -> None:
        self._rng = rng if rng is not None else Random()

    def __call__(self) -> CtfPosition:
        white_placement = random_placement(Side.WHITE, self._rng)
        black_placement = random_placement(Side.BLACK, self._rng)
        return assemble_position(white_placement, black_placement)

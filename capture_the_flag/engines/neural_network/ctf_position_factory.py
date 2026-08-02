from random import Random

from ...board import STANDARD_144, BoardLayout
from ...instrumentation.timing import region
from ...placement import assemble_position, random_placement
from ...position import CtfPosition
from ...side import Side
from ...timing_regions import STARTING_POSITION


class CtfPositionFactory:
    """Zero-arg starting-position factory for self-play: a fresh random placement
    per side, assembled into a phase-2 start position.

    `rng` is injectable so a seeded run draws reproducible placements; it defaults
    to an unseeded `Random`. The instance is held across calls, so a seeded rng
    produces a deterministic *sequence* of placements (self-play games still
    diverge) rather than the same board every game.

    `layout` is the board every position this factory builds is played on. It is
    held on the instance because the library's `position_factory` contract is
    zero-arg, so there is nowhere else to put it. It still defaults to Battle,
    which is the last board assumption in the self-play path and is removed when
    the run-time configuration reaches here.
    """

    def __init__(
        self, rng: Random | None = None, layout: BoardLayout = STANDARD_144
    ) -> None:
        self._rng = rng if rng is not None else Random()
        self._layout = layout

    def __call__(self) -> CtfPosition:
        with region(STARTING_POSITION):
            white_placement = random_placement(Side.WHITE, self._layout, self._rng)
            black_placement = random_placement(Side.BLACK, self._layout, self._rng)
            return assemble_position(
                white_placement, black_placement, self._layout
            )

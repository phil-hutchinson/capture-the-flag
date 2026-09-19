from random import Random

from ...game_setup import GameSetup
from ...instrumentation.timing import region
from ...position import CtfPosition
from ...start_position import generate_start_position
from ...timing_regions import STARTING_POSITION


class CtfPositionFactory:
    """Zero-arg starting-position factory for self-play: a fresh
    `start_position.generate_start_position` draw for `setup` on every call.

    `setup` is the board and army every position this factory builds is played
    under. It is held on the instance because the library's `position_factory`
    contract is zero-arg, so there is nowhere else to put it, and it is required
    rather than defaulted: a self-play game played on a different board from the
    one its network encodes is the failure this whole seam exists to prevent.

    `rng` is the factory's own draw stream, so a caller seeding it (a training
    run resuming reproducibly) gets the same sequence of starting positions each
    time; defaults to a fresh `random.Random()` otherwise.
    """

    def __init__(self, rng: Random | None = None, *, setup: GameSetup) -> None:
        self._rng = rng if rng is not None else Random()
        self._setup = setup

    def __call__(self) -> CtfPosition:
        with region(STARTING_POSITION):
            return generate_start_position(self._setup, self._rng)

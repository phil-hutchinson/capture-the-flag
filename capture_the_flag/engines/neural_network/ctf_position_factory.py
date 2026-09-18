from random import Random

from ...game_setup import GameSetup
from ...instrumentation.timing import region
from ...match import stub_start_position
from ...position import CtfPosition
from ...timing_regions import STARTING_POSITION


class CtfPositionFactory:
    """Zero-arg starting-position factory for self-play: hands back the fixed
    stub starting position (`match.stub_start_position`) for `setup` on every
    call.

    `rng` is accepted, but currently unused, purely for interface stability: the
    stub is deterministic, but stories 00000049 steps 7-8 replace it with real
    generation, which is again where a seeded draw happens.

    `setup` is the board and army every position this factory builds is played
    under. It is held on the instance because the library's `position_factory`
    contract is zero-arg, so there is nowhere else to put it, and it is required
    rather than defaulted: a self-play game played on a different board from the
    one its network encodes is the failure this whole seam exists to prevent.
    """

    def __init__(self, rng: Random | None = None, *, setup: GameSetup) -> None:
        self._rng = rng if rng is not None else Random()
        self._setup = setup

    def __call__(self) -> CtfPosition:
        with region(STARTING_POSITION):
            return stub_start_position(self._setup)

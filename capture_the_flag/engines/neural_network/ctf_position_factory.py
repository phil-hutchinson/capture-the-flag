from random import Random

from ...placement import assemble_position, random_placement
from ...position import CtfPosition
from ...side import Side


class CtfPositionFactory:
    def __call__(self) -> CtfPosition:
        rng = Random()
        white_placement = random_placement(Side.WHITE, rng)
        black_placement = random_placement(Side.BLACK, rng)
        position = assemble_position(white_placement, black_placement)
        return position
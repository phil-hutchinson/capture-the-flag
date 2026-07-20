import random

from game_engine_core.players.ai_player import AIPlayer

from ...placement import Placement, random_placement
from ...player import CtfPlayer
from ...ply import CtfPly
from ...position import CtfPosition
from ...side import Side


class AICtfPlayer(AIPlayer[CtfPly, CtfPosition], CtfPlayer):
    def get_placement(self, side: Side) -> Placement:
        """Begin with random placement. This will be built out to use AI in the future."""
        return random_placement(side, random.Random(1234)) # use consistent seed for repeatability. (This is only temprorary anyway.)

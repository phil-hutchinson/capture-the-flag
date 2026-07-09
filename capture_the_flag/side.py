"""Player sides for Capture the Flag.

White moves first, Black second — regardless of the colour tokens are
rendered as in a UI (see `.local/game-notation-suggestion.md`). `Side.value`
doubles as the `game-engine-core` `active_player_id` (1 for White, -1 for
Black).
"""

from enum import Enum


class Side(Enum):
    WHITE = 1
    BLACK = -1

"""The Unbreachable Flag cache shape (rules.md Section 6.2).

Split out from `position.py` so that both the state container and the
reachability computation (`reachability.py`) can depend on the shape without
depending on each other.
"""

from typing import NamedTuple


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

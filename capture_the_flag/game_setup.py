"""The resolved board and army a game is played with.

`BoardLayout` and `ArmyComposition` are independent values — they are two
separate rule flags (`rules.md` Appendix A) and either can change without the
other — but nothing plays a game with one and not the other. Placement needs the
home zone *and* the roster; a record states both. Pairing them keeps that from
becoming a parameter carried twice through every signature between the runner
and the placement seam.

`GameSetup` is also the only place the two flags meet, which makes it the only
place their **invalid combinations** can be caught: an army must fit its home
zone, one piece per square, so `standard_battle` on `standard_64` asks 25 pieces
to occupy 24 squares and is not a valid setting for play. That constrains
*playing*, not reading — a record carries the board it was played on and may
begin from a mid-game position that never had a placement phase to be valid or
invalid, which is why the check lives here rather than in the notation.

This grows into the run-time configuration: the edition and flag values a run
stamps its artifacts with resolve *to* a setup, and the flags that do not affect
board or army (the Tower placement rule) join it here.
"""

from dataclasses import dataclass

from .board import STANDARD_144, BoardLayout
from .pieces import STANDARD_BATTLE, ArmyComposition


@dataclass(frozen=True)
class GameSetup:
    """A board and an army that can actually be played together."""

    layout: BoardLayout
    composition: ArmyComposition

    def __post_init__(self) -> None:
        home_squares = len(self.layout.white_home_squares)
        if self.composition.size > home_squares:
            raise ValueError(
                f"{self.composition.composition_id} does not fit "
                f"{self.layout.layout_id}: {self.composition.size} pieces into "
                f"{home_squares} home squares, one piece per square"
            )


BATTLE_SETUP = GameSetup(layout=STANDARD_144, composition=STANDARD_BATTLE)
"""The 12 x 12 board and 25-piece army — what `2-0:BATTLE` resolves to."""

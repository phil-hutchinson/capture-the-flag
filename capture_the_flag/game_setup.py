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

from .board import BOARD_LAYOUTS, BoardLayout
from .pieces import ARMY_COMPOSITIONS, ArmyComposition
from .record import (
    RulesetConfiguration,
    active_configuration,
    edition_for_ruleset,
    resolve_flag,
    unsupported_aspects,
)


@dataclass(frozen=True)
class GameSetup:
    """A board and an army that can actually be played together, and — when one
    names it — the configuration they were resolved from.

    `configuration` is what every artifact this setup produces is stamped with:
    the record's `Ruleset` tag, the checkpoint's `ruleset` key, the run config.
    It is optional because **not every playable pairing is a published one**. A
    board and an army are independent flags, so a valid pairing can exist that no
    edition names — the rules say as much where they introduce the two flags —
    and such a setup is playable but not stampable. `resolve_setup` always fills
    it; a hand-built `GameSetup` leaves it `None`, and `stamp` is what turns
    trying to record one into a named error rather than a silent mislabel.
    """

    layout: BoardLayout
    composition: ArmyComposition
    configuration: RulesetConfiguration | None = None

    @property
    def stamp(self) -> RulesetConfiguration:
        """The configuration to record this setup as, or a named error."""
        if self.configuration is None:
            raise ValueError(
                f"this {self.layout.layout_id} / "
                f"{self.composition.composition_id} setup was not resolved from a "
                "published configuration, so there is nothing to stamp it as"
            )
        return self.configuration

    def __post_init__(self) -> None:
        home_squares = len(self.layout.white_home_squares)
        if self.composition.size > home_squares:
            raise ValueError(
                f"{self.composition.composition_id} does not fit "
                f"{self.layout.layout_id}: {self.composition.size} pieces into "
                f"{home_squares} home squares, one piece per square"
            )


def setup_for_ruleset(ruleset: str) -> GameSetup:
    """The setup for a live ruleset name — the runners' entry point.

    A name rather than an edition id because that is what a person types and what
    stays true across a minor bump; the edition it resolves to is what gets
    stamped.
    """
    return resolve_setup(active_configuration(edition_for_ruleset(ruleset)))


def resolve_setup(configuration: RulesetConfiguration) -> GameSetup:
    """The board and army `configuration` selects.

    This is the one place a stamped configuration becomes something the engine
    can set a game up with: `BOARD_LAYOUT` and `ARMY_COMPOSITION` resolve through
    the edition and flag registry (`record.resolve_flag`), and their value labels
    are looked up in the tables of what this build can actually play.

    Raises `ValueError` naming everything wrong at once when the configuration is
    beyond this build — an edition it does not implement, a flag it does not
    carry, a value label it does not know. Reporting the whole list rather than
    the first problem is what makes a stamp from a different build diagnosable in
    one read.
    """
    aspects = unsupported_aspects(configuration)
    if aspects:
        raise ValueError(
            f"cannot set up {configuration.render()!r}: " + "; ".join(aspects)
        )

    layout_id = resolve_flag(configuration, "BOARD_LAYOUT")
    composition_id = resolve_flag(configuration, "ARMY_COMPOSITION")
    missing = [
        f"{flag_id} {label!r}"
        for flag_id, label, table in (
            ("BOARD_LAYOUT", layout_id, BOARD_LAYOUTS),
            ("ARMY_COMPOSITION", composition_id, ARMY_COMPOSITIONS),
        )
        if label not in table
    ]
    if missing:
        # A published label this build has no implementation for. Distinct from
        # an *unknown* label, which `unsupported_aspects` has already rejected:
        # this one is real and named in Appendix A, just not built here yet.
        raise ValueError(
            f"cannot set up {configuration.render()!r}: this build implements no "
            + " or ".join(missing)
        )

    return GameSetup(
        layout=BOARD_LAYOUTS[layout_id],
        composition=ARMY_COMPOSITIONS[composition_id],
        configuration=configuration,
    )


BATTLE_SETUP = setup_for_ruleset("BATTLE")
"""The 12 x 12 board and 25-piece army — what `2-0:BATTLE` resolves to.

The default a runner plays when it is not told which ruleset to use, and not an
arbitrary pick: both published flags default to Battle's values, so Battle is
what the rules resolve to in the absence of a choice."""

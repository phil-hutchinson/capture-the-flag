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

from .board import BOARD_LAYOUTS, BoardLayout, Square
from .pieces import ARMY_COMPOSITIONS, ArmyComposition
from .record import (
    RulesetConfiguration,
    active_configuration,
    edition_for_ruleset,
    resolve_flag,
    unsupported_aspects,
)
from .side import Side

SPACING_ONLY = "spacing_only"
"""`TOWER_PLACEMENT` at its default: the published Tower spacing rule and nothing
more (`rules.md` Section 3)."""

SPACING_AND_LANES = "spacing_and_lanes"
"""`TOWER_PLACEMENT` with the lane restriction as well: no Tower on a square
orthogonally adjacent to a lane square.

The labels live here rather than beside the registry entry in `record.py` because
this is where the flag is *interpreted* — `record.py` publishes value labels but
never acts on them, exactly as it publishes `standard_144` without knowing what a
board is."""

TOWER_PLACEMENTS: frozenset[str] = frozenset({SPACING_ONLY, SPACING_AND_LANES})
"""Every `TOWER_PLACEMENT` value this build can actually apply.

Membership is *implementability*, not publication — the same distinction
`board.BOARD_LAYOUTS` and `pieces.ARMY_COMPOSITIONS` draw, and it matters for the
same reason. A flag resolving to behavior rather than to an object has no lookup
table to fail against, so without this a published label this code had never
heard of would fall through to "not `spacing_and_lanes`" and quietly play the
default."""


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

    When it *is* named it must resolve to the other fields — a setup carrying a
    configuration that describes some other board, army, or Tower rule is
    rejected at construction (`_check_configuration_describes_this_setup`), since
    it would stamp every record and checkpoint it produced with rules the game
    was not played under.
    """

    layout: BoardLayout
    composition: ArmyComposition
    configuration: RulesetConfiguration | None = None
    tower_placement: str = SPACING_ONLY
    """The resolved `TOWER_PLACEMENT` value — the first flag here that resolves to
    behavior rather than to an object.

    It belongs on the setup for the reason the board and the army do: placement is
    the one thing that reads it, and placement already takes a setup. It defaults
    to `SPACING_ONLY` so a hand-built `GameSetup` plays the published Tower rule
    and nothing more, which is what the flag's own default says."""

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
        if self.tower_placement not in TOWER_PLACEMENTS:
            raise ValueError(
                f"this build applies no TOWER_PLACEMENT {self.tower_placement!r}; "
                f"it implements {', '.join(sorted(repr(v) for v in TOWER_PLACEMENTS))}"
            )
        self._check_configuration_describes_this_setup()

    def _check_configuration_describes_this_setup(self) -> None:
        """A named `configuration` must resolve to exactly these fields.

        `stamp` guards the setup that has *no* configuration to record itself as;
        this guards the setup that has the wrong one. Both are the same failure —
        an artifact whose stamp does not describe the game that produced it — and
        without this the second is silent, because a stamp is only ever compared
        against another stamp and never against the board and army actually
        played. `resolve_setup` derives every field from the configuration, so it
        satisfies this by construction; what it catches is a setup assembled
        field-by-field (or `dataclasses.replace`d) that then keeps a stamp
        describing something else.

        Mismatches are reported together rather than one at a time, for the
        reason `resolve_setup` reports its own list whole: a setup built from the
        wrong configuration usually disagrees about more than one flag, and
        fixing them one error at a time reveals that slowly.
        """
        if self.configuration is None:
            return
        mismatches = [
            f"{flag_id} resolves to {resolved!r}, but this setup has {actual!r}"
            for flag_id, actual in (
                ("BOARD_LAYOUT", self.layout.layout_id),
                ("ARMY_COMPOSITION", self.composition.composition_id),
                ("TOWER_PLACEMENT", self.tower_placement),
            )
            if (resolved := resolve_flag(self.configuration, flag_id)) != actual
        ]
        if mismatches:
            raise ValueError(
                f"this setup cannot be stamped {self.configuration.render()!r}: "
                + "; ".join(mismatches)
            )

    def forbidden_tower_squares(self, side: Side) -> frozenset[Square]:
        """Home squares of `side` where `TOWER_PLACEMENT` forbids a Tower.

        Empty under `spacing_only`, and — because the set is derived from the
        board rather than listed — empty on any layout whose home zones do not
        touch the lake rows, which is what makes the flag inert on Battle without
        Battle being a special case. The spacing rule itself is not expressed here:
        it constrains Towers relative to *each other* rather than to squares, so it
        lives with the placement check that can see them all at once.
        """
        if self.tower_placement != SPACING_AND_LANES:
            return frozenset()
        return self.layout.home_squares(side) & self.layout.lane_adjacent_squares


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
    can set a game up with: every flag resolves through the edition and flag
    registry (`record.resolve_flag`), and its value label is then checked against
    what this build can actually play. `BOARD_LAYOUT` and `ARMY_COMPOSITION` are
    checked against the tables they resolve to; `TOWER_PLACEMENT` resolves to
    behavior rather than to an object, so it is checked against the set of labels
    this code has an implementation for.

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
    tower_placement = resolve_flag(configuration, "TOWER_PLACEMENT")
    missing = [
        f"{flag_id} {label!r}"
        for flag_id, label, table in (
            ("BOARD_LAYOUT", layout_id, BOARD_LAYOUTS),
            ("ARMY_COMPOSITION", composition_id, ARMY_COMPOSITIONS),
            ("TOWER_PLACEMENT", tower_placement, TOWER_PLACEMENTS),
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
        tower_placement=tower_placement,
    )


BATTLE_SETUP = setup_for_ruleset("BATTLE")
"""The 12 x 12 board and 25-piece army — what `2-0:BATTLE` resolves to.

The default a runner plays when it is not told which ruleset to use, and not an
arbitrary pick: both published flags default to Battle's values, so Battle is
what the rules resolve to in the absence of a choice."""

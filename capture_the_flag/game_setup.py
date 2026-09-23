"""The resolved board and army a game is played with.

Since major 3, `BoardLayout` and `ArmyComposition` are no longer independent
rule flags — the board and the army each collapse to the single value
`rules.md` §2 fixes directly, so there is nothing left to *resolve* between
them. `GameSetup` survives as the pairing anyway: a record states both, and the
one place they meet is still the one place an invalid pairing (an army that
does not exactly fill its home zone) can be caught.

This grows into the run-time configuration: the edition a run stamps its
artifacts with resolves *to* a setup.
"""

from dataclasses import dataclass

from .board import SIMPLE_64, BoardLayout
from .pieces import STANDARD_ARMY, ArmyComposition
from .record import (
    RulesetConfiguration,
    active_configuration,
    edition_for_ruleset,
    unsupported_aspects,
)


@dataclass(frozen=True)
class GameSetup:
    """A board and an army that can actually be played together, and — when one
    names it — the configuration they were resolved from.

    `configuration` is what every artifact this setup produces is stamped with:
    the record's `Ruleset` tag, the checkpoint's `ruleset` key, the run config.
    It is optional because **not every playable pairing is a published one** —
    `resolve_setup` always fills it; a hand-built `GameSetup` leaves it `None`,
    and `stamp` is what turns trying to record one into a named error rather
    than a silent mislabel.

    When it *is* named it must resolve to the other fields — a setup carrying a
    configuration that describes some other board or army is rejected at
    construction (`_check_configuration_describes_this_setup`), since it would
    stamp every record and checkpoint it produced with rules the game was not
    played under.
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
        if self.composition.size != home_squares:
            raise ValueError(
                f"{self.composition.composition_id} does not fill "
                f"{self.layout.layout_id}: {self.composition.size} pieces for "
                f"{home_squares} home squares; the army must fill the home zone "
                "exactly, one piece per square (rules.md Section 2)"
            )
        self._check_configuration_describes_this_setup()

    def _check_configuration_describes_this_setup(self) -> None:
        """A named `configuration` must resolve to exactly this board and army.

        There are no flags left to check field by field (major 3 publishes
        none — see `record.RULE_FLAGS`): the board and army are each a single
        value, so this only has one thing left to verify, that they are the
        one value the named edition means. Compared directly against the
        published pairing rather than through `resolve_setup`, so a hand-built
        setup cannot recurse back into the constructor that is checking it.
        """
        if self.configuration is None:
            return
        if unsupported_aspects(self.configuration):
            raise ValueError(
                f"this setup cannot be stamped {self.configuration.render()!r}: "
                "this build cannot resolve that configuration at all"
            )
        if self.layout is not SIMPLE_64 or self.composition is not STANDARD_ARMY:
            raise ValueError(
                f"this setup cannot be stamped {self.configuration.render()!r}: "
                f"that configuration resolves to {SIMPLE_64.layout_id} / "
                f"{STANDARD_ARMY.composition_id}, not "
                f"{self.layout.layout_id} / {self.composition.composition_id}"
            )


def setup_for_ruleset(ruleset: str) -> GameSetup:
    """The setup for a live ruleset name — the runners' entry point.

    A name rather than an edition id because that is what a person types and
    what stays true across a minor bump; the edition it resolves to is what
    gets stamped.
    """
    return resolve_setup(active_configuration(edition_for_ruleset(ruleset)))


def resolve_setup(configuration: RulesetConfiguration) -> GameSetup:
    """The board and army `configuration` selects.

    Raises `ValueError` naming everything wrong at once when the configuration
    is beyond this build — an edition it does not implement, or a flag it does
    not carry (major 3 carries none, so any flag at all is one of these).

    There is exactly one board and one army to resolve to: since neither is a
    published flag at major 3 (`doc/ruleset/CLAUDE.md`), there is no label to
    look up and no table to look it up in. Code that assumes a second board or
    army exists today is premature, not a bug, until major 3 actually grows
    one.
    """
    aspects = unsupported_aspects(configuration)
    if aspects:
        raise ValueError(
            f"cannot set up {configuration.render()!r}: " + "; ".join(aspects)
        )
    return GameSetup(
        layout=SIMPLE_64, composition=STANDARD_ARMY, configuration=configuration
    )


PRE_RELEASE_SETUP = setup_for_ruleset("PRE-RELEASE")
"""The 8 x 8 board and 16-piece army — what `3-0:PRE-RELEASE` resolves to.

The only Active edition, and so the only setup a runner can currently reach
without naming a ruleset this build does not implement."""

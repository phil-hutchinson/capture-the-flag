"""Game-record file writer, and the ruleset identifiers a record is stamped with
(see `doc/ruleset/technical-notes.md`, "Record file format").

Assembles a complete record file from a finished `GameResult`: PGN-style
header tags, the setup position block, and the move sequence built from
`StandardGame`'s game log. A `GameResult` is what both `play_match` (via
`MatchResult.game_result`) and the shared `Tournament` (`GameRecord.result`)
produce, so the writer serves either path.

Alongside the writer, this module holds the **edition table** and **flag
registry** (`EDITIONS`, `RULE_FLAGS`) and the resolved-configuration type every
stamped artifact uses — records here, and checkpoints via `ctf_checkpoint`. They
live with the writer because a record's `Ruleset` tag is the reason the
identifiers exist: every record must state the rules it was played under
precisely enough that they are recoverable from the record alone.

This repository only ever *writes* records; nothing here reads, parses, or
replays one. That is deliberate — the separate front-end player application
consumes these records, and the relationship is one-way — so the whole
obligation of this module is to stamp accurately what was actually played, not
to interpret anything stamped by anyone else.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

from game_engine_core.models.game_result import GameResult

_RESULT_TAGS = {1: "1-0", -1: "0-1", 0: "1/2-1/2"}


@dataclass(frozen=True)
class RuleFlag:
    """One point of rule variation: an enum-valued parameter with a default.

    Enum-valued even when currently binary (`on | off`), so a third value can be
    added later without a type change. `default` is always the behavior that
    predated the flag, which is what makes introducing a flag a no-op for every
    existing edition and every existing record.

    `flag_id` and every label in `values` are permanent once published: they are
    never reused for different behavior and never redefined (see `rules.md`
    Appendix A). New behavior gets a new label.
    """

    flag_id: str
    values: tuple[str, ...]
    default: str


RULE_FLAGS: dict[str, RuleFlag] = {
    flag.flag_id: flag
    for flag in (
        RuleFlag(
            flag_id="BOARD_LAYOUT",
            values=("standard_144", "standard_64"),
            default="standard_144",
        ),
        RuleFlag(
            flag_id="ARMY_COMPOSITION",
            values=("standard_battle", "standard_skirmish"),
            default="standard_battle",
        ),
        RuleFlag(
            flag_id="TOWER_PLACEMENT",
            values=("spacing_only", "spacing_and_lanes"),
            default="spacing_only",
        ),
    )
}
"""The published flag registry, keyed by flag id.

Flags are created lazily — standard behavior stays unflagged until someone wants
to test a variant of it — so this grows one entry at a time as variants graduate
from `doc/ruleset/proposed-variants.md`.

The document appendices are the source of truth for what is published (see
`doc/ruleset/rules.md` Appendix A); this is the engine's own copy of the part it
must act on. Every default reproduces what `1-2:PRE-RELEASE` played, which is what
made introducing each one a no-op for every edition and record that predates it —
`TOWER_PLACEMENT` included, since no published edition sets it away from
`spacing_only` at the point it is registered.

A value label appearing here is a claim about what is *published*, not about what
this build can set up: `board.BOARD_LAYOUTS` and `pieces.ARMY_COMPOSITIONS` say
which labels resolve to something playable, and `unsupported_aspects` reports the
difference.
"""


@dataclass(frozen=True)
class Edition:
    """An immutable ruleset edition: `<major>-<minor>:<Ruleset>` resolving to a
    major baseline plus a complete set of flag values.

    **This table is a copy, not the definition.** An edition is defined by
    `doc/ruleset/rules.md` Appendix B, whose row for it is the published,
    authoritative statement of what it means. This is the engine's own copy of
    the part it must act on, and if the two ever disagree the document governs
    and the code is wrong.

    **The army is a flag value, not a field.** Before major 2 an edition carried
    a piece distribution of its own alongside its flag values, which gave two
    things a claim on the army and needed a rule to arbitrate between them. It is
    now the resolved `ARMY_COMPOSITION` value like anything else, so flags are the
    only thing an edition is made of. Immutability survives the move because a
    published value *label* is permanent: `standard_battle` names one army
    forever (`rules.md` Appendix A), so an edition naming it means the same army
    forever, without this table restating what that army is.

    `flag_values` holds the values *this edition* sets, which is not the same as
    the flags' own defaults: a later edition may set a flag whose registry
    default differs. An edition that predates a flag entirely simply has no entry
    for it (see `resolve_flag`).
    """

    edition_id: str
    flag_values: Mapping[str, str]

    def __hash__(self) -> int:
        """Hash the mapping field by content, since the generated `__hash__` a
        frozen dataclass would supply raises on a `dict` field.

        `frozenset` rather than a sorted tuple because the keys are not required
        to be orderable, and equality of two mappings is exactly equality of
        their item sets.
        """
        return hash((self.edition_id, frozenset(self.flag_values.items())))


ACTIVE_EDITIONS: frozenset[str] = frozenset({"2-0:BATTLE", "2-0:SKIRMISH"})
"""The editions this build implements, and therefore the ones it can stamp.

**A build implements every Active edition**, not one: since major 2 two rulesets
are published in parallel and the configuration is selected at run time, so this
is a set rather than a single pointer. `2-0:SKIRMISH` joins it once the engine
can set up its board and army.

Note the dash in an edition id — it is a compound label, not a decimal, so a
minor 10 would not sort before a minor 2.
"""

DEFAULT_EDITION = "2-0:BATTLE"
"""The edition a run plays when it is not told which.

Not an arbitrary pick among the Active editions: both published flags default to
Battle's values (`standard_144`, `standard_battle`), so Battle *is* what the
rules resolve to in the absence of a choice.
"""

ACTIVE_RULESETS: dict[str, str] = {
    edition_id.split(":", 1)[1]: edition_id for edition_id in sorted(ACTIVE_EDITIONS)
}
"""Each live ruleset name and the edition it currently points at.

This is the pointer the vocabulary describes: a **ruleset** is a mutable name and
an **edition** is immutable, so `BATTLE` means whichever `<major>-<minor>:BATTLE`
is Active right now. Derived from `ACTIVE_EDITIONS` rather than written out, so
publishing a new edition of a ruleset moves its pointer with no second edit to
forget. Runners take a ruleset name from the command line and resolve it here;
every artifact they write is stamped with the *edition*, never the name, which
would only pin a pointer.
"""

DEFAULT_RULESET = DEFAULT_EDITION.split(":", 1)[1]
"""The ruleset name a runner plays when it is not told which — `DEFAULT_EDITION`
as a name, so the two cannot drift apart."""

EDITIONS: dict[str, Edition] = {
    edition.edition_id: edition
    for edition in (
        Edition(
            edition_id="2-0:BATTLE",
            flag_values={
                "BOARD_LAYOUT": "standard_144",
                "ARMY_COMPOSITION": "standard_battle",
            },
        ),
        Edition(
            edition_id="2-0:SKIRMISH",
            flag_values={
                "BOARD_LAYOUT": "standard_64",
                "ARMY_COMPOSITION": "standard_skirmish",
            },
        ),
        Edition(edition_id="1-2:PRE-RELEASE", flag_values={}),
    )
}
"""Every edition this code knows, keyed by edition id.

Editions are never removed from this table and never redefined; an edition the
active pointer has moved off is *historical*, not gone (`rules.md` Appendix B).
Retaining it is what lets a stamped artifact still name something meaningful.

Membership is therefore *not* implementability: a historical entry is a label
this code can recognise, not a ruleset it can run. `unsupported_aspects` draws
that line.

`1-2:PRE-RELEASE` sets no flag values because it predates both flags, so each
resolves to its own registry default — which is exactly the behavior it was
played under, since a flag's default is always what preceded it.
"""


@dataclass(frozen=True)
class RulesetConfiguration:
    """A fully resolved rules configuration: an edition plus only the flags that
    deviate from it.

    **Flags at their resolved value are omitted**, so a configuration of all
    edition values carries an empty `flags` and renders as the bare edition id.
    Omission is safe rather than merely tidy: because every flag default is
    behavior-preserving by construction, an absent flag can never mean "something
    happened that this code does not understand" — it means the behavior the code
    already implements. A compatibility check therefore only has to run over the
    flags explicitly listed.

    Omission is a property of the *value*, not a convention producers are trusted
    to follow: a configuration listing a flag at exactly its resolved value means
    the same thing as one omitting it, but would render differently and compare
    unequal. `canonicalize` is what removes that difference, and `from_stamp`
    applies it to everything read from an artifact this code did not write.

    **The edition is always present, even with no flags listed.** A configuration
    meaning "all edition values" and an artifact written before stamping existed
    would otherwise be indistinguishable — both carry no flag information — yet
    the two must be treated differently, and `ctf_checkpoint` rejects unstamped
    checkpoints rather than guessing.
    """

    edition: str
    flags: Mapping[str, str] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash by content, as `Edition` does and for the same reason: the
        `__hash__` a frozen dataclass generates would raise on the `dict` this
        field holds in practice, at the point of use rather than of construction.
        """
        return hash((self.edition, frozenset(self.flags.items())))

    def render(self) -> str:
        """Render for a text medium (the record's `Ruleset` tag).

        The edition id, then one `FLAG=value` token per deviating flag, space
        separated and ordered alphabetically by flag id. Deterministic ordering is
        what makes the rendering stable: two configurations that mean the same
        thing must produce the same string, which insertion order would not
        guarantee. Neither an edition id nor a flag id or label contains a space,
        so the tokens split unambiguously.
        """
        tokens = [self.edition]
        tokens += [f"{flag_id}={self.flags[flag_id]}" for flag_id in sorted(self.flags)]
        return " ".join(tokens)

    def as_stamp(self) -> dict[str, object]:
        """The nested-mapping form, for stamping into a checkpoint or run config.

        Structured rather than concatenated: comparison of two structured
        configurations is what produces a message naming the offending flag,
        where two strings could only report that they differ somewhere. It also
        follows the precedent the architecture stamp already sets.
        """
        return {"edition": self.edition, "flags": dict(self.flags)}

    @classmethod
    def from_stamp(cls, raw: object) -> "RulesetConfiguration":
        """Rebuild a configuration from its `as_stamp` form.

        Raises `ValueError` if the stamp is structurally unusable. A stamp that is
        present but unreadable is no better than an absent one and deserves the
        same named failure rather than a `KeyError` or a silently wrong
        configuration. Callers add their own context (which file) to the message.

        The result is canonical (see `canonicalize`). This is the entry point for
        artifacts this code did not write, so it is where a non-canonical listing
        — a flag written out at its resolved value — has to be normalised, before
        it can render differently from, or compare unequal to, the configuration
        that means the same thing.
        """
        if not isinstance(raw, Mapping) or "edition" not in raw or "flags" not in raw:
            raise ValueError(
                f"expected a mapping with 'edition' and 'flags', got {raw!r}"
            )
        edition, flags = raw["edition"], raw["flags"]
        if not isinstance(edition, str):
            raise ValueError(f"'edition' must be an edition id, got {edition!r}")
        if not isinstance(flags, Mapping) or not all(
            isinstance(flag_id, str) and isinstance(value, str)
            for flag_id, value in flags.items()
        ):
            raise ValueError(f"'flags' must map flag ids to value labels, got {flags!r}")
        return canonicalize(cls(edition=edition, flags=dict(flags)))


def edition_for_ruleset(ruleset: str) -> str:
    """The edition `ruleset` currently points at, matched case-insensitively.

    Raises `ValueError` naming the live rulesets, since this is the seam a
    mistyped command-line argument arrives through.
    """
    edition = ACTIVE_RULESETS.get(ruleset.upper())
    if edition is None:
        raise ValueError(
            f"unknown ruleset {ruleset!r}; this build plays "
            f"{', '.join(sorted(ACTIVE_RULESETS))}"
        )
    return edition


def active_configuration(edition: str = DEFAULT_EDITION) -> RulesetConfiguration:
    """The configuration for an Active `edition`, with no deviations.

    Both published flags are set explicitly by every Active edition, so a
    configuration naming one of them lists no deviations at all and renders as a
    bare edition id. A flag that exists, is authoritative, and never appears in
    any artifact is a well-formed outcome under this model rather than a sign
    something is wrong.
    """
    if edition not in ACTIVE_EDITIONS:
        raise ValueError(
            f"{edition!r} is not an Active edition; this build implements "
            f"{', '.join(sorted(ACTIVE_EDITIONS))}"
        )
    return RulesetConfiguration(edition=edition)


def resolve_flag(
    configuration: RulesetConfiguration,
    flag_id: str,
    *,
    rule_flags: Mapping[str, RuleFlag] | None = None,
    editions: Mapping[str, Edition] | None = None,
) -> str:
    """The value `flag_id` takes under `configuration`.

    Resolution is two-level, because **absent is not the same as flag-default**:
    a flag the configuration does not list takes *the edition's* value for it,
    falling back to the flag's own registry default only when the edition has no
    value — which is the case for an edition that predates the flag. A flag baked
    into a newer edition hits the first case; a flag introduced after an edition
    was published hits the second and reads like a one-level lookup.

    `rule_flags` and `editions` default to the published registry and table.
    They are injectable because these are pure functions of that data, and
    exercising resolution, rendering, and comparison against hypothetical flags
    is the only way to test them while the real registry is still empty.

    Raises `KeyError` for an unknown flag id or edition id.
    """
    rule_flags = RULE_FLAGS if rule_flags is None else rule_flags
    editions = EDITIONS if editions is None else editions
    if flag_id in configuration.flags:
        return configuration.flags[flag_id]
    edition = editions[configuration.edition]
    if flag_id in edition.flag_values:
        return edition.flag_values[flag_id]
    return rule_flags[flag_id].default


def canonicalize(
    configuration: RulesetConfiguration,
    *,
    rule_flags: Mapping[str, RuleFlag] | None = None,
    editions: Mapping[str, Edition] | None = None,
) -> RulesetConfiguration:
    """`configuration` with every flag listed at its resolved value dropped.

    A configuration is meant to list only deviations (see
    `RulesetConfiguration`), but a stamp is only as canonical as whatever wrote
    it. A flag written out at the value it would resolve to anyway says nothing,
    yet makes the configuration render differently from and compare unequal to
    the one that means the same thing — enough to have
    `configuration_differences` report a disagreement between two records that
    agree, and refuse a legitimate resume.

    A flag this code cannot resolve at all — unknown here, and unset by the
    edition — is kept rather than dropped, so `unsupported_aspects` still sees it
    and can name it. An unknown edition leaves the configuration untouched
    entirely: with no values to resolve against, dropping anything risks dropping
    a real deviation.

    `rule_flags` and `editions` are injectable for the reason `resolve_flag`'s
    are: the published registry is empty, so canonicality can only be exercised
    against hypothetical flags.
    """
    rule_flags = RULE_FLAGS if rule_flags is None else rule_flags
    editions = EDITIONS if editions is None else editions
    edition = editions.get(configuration.edition)
    if edition is None:
        return configuration
    deviations = {}
    for flag_id, value in configuration.flags.items():
        flag = rule_flags.get(flag_id)
        resolved = edition.flag_values.get(
            flag_id, None if flag is None else flag.default
        )
        if value != resolved:
            deviations[flag_id] = value
    return RulesetConfiguration(edition=configuration.edition, flags=deviations)


def unsupported_aspects(
    configuration: RulesetConfiguration,
    *,
    rule_flags: Mapping[str, RuleFlag] | None = None,
    editions: Mapping[str, Edition] | None = None,
    active_editions: Collection[str] = ACTIVE_EDITIONS,
) -> list[str]:
    """What about `configuration` the running code cannot implement, phrased for
    an error message; empty when it can implement all of it.

    Three ways a stamped configuration can be beyond this code: it names an
    edition this code does not implement, it lists a flag that does not exist
    here at all, or it lists a value label the flag does not have. The
    distinction matters to whoever reads the failure — "no such flag" says the
    artifact comes from a variant this build does not carry, while "no such
    value" says the variant is here but has moved on — so each is reported in its
    own words rather than as a bare inequality.

    **Implemented is not the same as known.** A build implements every edition in
    `ACTIVE_EDITIONS`; `EDITIONS` retains the ones the active pointer has moved
    off, which is what lets a stamped artifact still name something meaningful,
    but those are precisely the editions this code cannot play. A historical
    edition is rejected because it is **not Active** — the rules changed, so a run
    resuming from it would train under rules its weights never saw — and not
    because a build can hold only one edition; it holds several and refuses the
    ones it no longer plays. The message still says which case it was: naming an
    edition this build never heard of and naming one it has superseded are
    different situations for whoever has to act on the failure. Validated replay
    of a historical edition means checking out the build that implemented it (see
    `doc/ruleset/technical-notes.md`).

    Only the flags the configuration explicitly lists are checked. Everything it
    omits resolves to behavior this code implements by construction (see
    `RulesetConfiguration`), so silence there is correct rather than a gap.
    """
    rule_flags = RULE_FLAGS if rule_flags is None else rule_flags
    editions = EDITIONS if editions is None else editions
    aspects = []
    if configuration.edition not in active_editions:
        known = (
            "a historical edition"
            if configuration.edition in editions
            else "not an edition this code knows"
        )
        aspects.append(
            f"edition {configuration.edition!r} is {known}; this code implements "
            f"{', '.join(sorted(active_editions))}"
        )
    for flag_id in sorted(configuration.flags):
        value = configuration.flags[flag_id]
        flag = rule_flags.get(flag_id)
        if flag is None:
            aspects.append(
                f"flag {flag_id!r}: stamp says {value!r}, running code has no such flag"
            )
        elif value not in flag.values:
            known = ", ".join(repr(label) for label in flag.values)
            aspects.append(
                f"flag {flag_id!r}: stamp says {value!r}, running code knows only {known}"
            )
    return aspects


def configuration_differences(
    left: RulesetConfiguration,
    right: RulesetConfiguration,
    *,
    left_label: str,
    right_label: str,
) -> list[str]:
    """How two configurations differ, phrased for an error message; empty when
    they agree.

    Used where one artifact records the configuration twice and the two records
    must not disagree (a run config against its checkpoint's stamp). Unlike
    `unsupported_aspects` this asks nothing about what the running code can do —
    both sides are claims about the past, and the point is only whether they are
    the same claim. `left_label` and `right_label` name the two sources, since a
    difference is unreadable without knowing which value came from where.
    """
    differences = []
    if left.edition != right.edition:
        differences.append(
            f"edition: {left_label} says {left.edition!r}, "
            f"{right_label} says {right.edition!r}"
        )
    for flag_id in sorted(left.flags.keys() | right.flags.keys()):
        left_value = left.flags.get(flag_id)
        right_value = right.flags.get(flag_id)
        if left_value != right_value:
            differences.append(
                f"flag {flag_id!r}: {left_label} says "
                f"{'no deviation' if left_value is None else repr(left_value)}, "
                f"{right_label} says "
                f"{'no deviation' if right_value is None else repr(right_value)}"
            )
    return differences


def _escape_tag_value(value: str) -> str:
    """Escape a tag value for the `[Name "value"]` header syntax.

    Follows PGN: a literal backslash becomes `\\\\` and a double-quote becomes
    `\\"`, so a value containing either can't terminate or corrupt the tag.
    Newlines (which a single-line tag cannot carry) are collapsed to spaces so
    a stray line break can't split the header into unparseable fragments.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _build_move_sequence(game_log: Sequence[tuple[str, str]]) -> str:
    ply_strings = [ply for ply, _board_after in game_log]
    lines = []
    for round_start in range(0, len(ply_strings), 2):
        round_number = round_start // 2 + 1
        white_ply = ply_strings[round_start]
        if round_start + 1 < len(ply_strings):
            black_ply = ply_strings[round_start + 1]
            lines.append(f"{round_number}. {white_ply} {black_ply}")
        else:
            lines.append(f"{round_number}. {white_ply}")
    return "\n".join(lines)


def write_record(
    game_result: GameResult,
    *,
    configuration: RulesetConfiguration,
    white_name: str | None = None,
    black_name: str | None = None,
    event: str | None = None,
    site: str | None = None,
    date: str | None = None,
    round_number: str | None = None,
) -> str:
    """Build a complete game-record file for a finished game.

    `white_name`, `black_name`, `event`, `site`, `date`, and `round_number`
    are best-effort roster tags: each is included only if supplied, and
    omitted entirely otherwise. `Result` is derived from the game's absolute
    outcome and `ResultReason` from `game_result.result_reason` (the terminal
    position's `outcome_reason`, e.g. `Flag Captured`). `Ruleset`, `Result`,
    and `ResultReason` are always present: `Ruleset` records the rules the game
    was actually played under, as the full edition id plus any deviating flags
    (`configuration.render()`) — never a bare ruleset name, which would only name
    a moving pointer. It is passed in rather than read from a build constant:
    since major 2 a build implements several editions and the game was played
    under whichever one this run selected.

    Tag values are escaped for the `[Name "value"]` syntax (see
    `_escape_tag_value`): `\\` and `"` are backslash-escaped and newlines are
    collapsed to spaces, so an arbitrary player or event name always yields a
    well-formed, parseable header.
    """
    optional_tags = [
        ("Event", event),
        ("Site", site),
        ("Date", date),
        ("Round", round_number),
        ("White", white_name),
        ("Black", black_name),
    ]
    header_lines = [
        f'[{name} "{_escape_tag_value(value)}"]'
        for name, value in optional_tags
        if value is not None
    ]
    header_lines.append(f'[Ruleset "{_escape_tag_value(configuration.render())}"]')
    header_lines.append(f'[Result "{_RESULT_TAGS[game_result.outcome]}"]')
    header_lines.append(f'[ResultReason "{_escape_tag_value(game_result.result_reason)}"]')

    header = "\n".join(header_lines)
    move_sequence = _build_move_sequence(game_result.game_log)
    return f"{header}\n\n{game_result.opening_board}\n\n{move_sequence}\n"

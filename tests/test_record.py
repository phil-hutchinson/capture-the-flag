"""Tests for the game-record file writer, the edition table, and the resolved
ruleset configuration."""

import dataclasses
import random

import pytest

from capture_the_flag.match import play_match
from capture_the_flag.pieces import ARMY_ROSTER
from capture_the_flag.player import RandomCtfPlayer
from capture_the_flag.record import (
    ACTIVE_EDITION,
    EDITIONS,
    Edition,
    RuleFlag,
    RulesetConfiguration,
    active_configuration,
    configuration_differences,
    resolve_flag,
    unsupported_aspects,
    write_record,
)

_RESULT_TAGS = {1: "1-0", -1: "0-1", 0: "1/2-1/2"}
_RULESET_TAG = f'[Ruleset "{ACTIVE_EDITION}"]'

# Hypothetical flags and a hypothetical later edition. The published registry is
# empty (this story builds the machinery and defines no flag), so resolution,
# rendering, and comparison can only be exercised against injected data — which is
# why those functions take the registry and table as arguments.
#
# `MOVABLE_TOWERS` defaults to `off` but is set `on` by edition `1-3`, which is
# the case that makes resolution two-level: the same flag resolves differently
# under two editions with no configuration mentioning it. `DIAGONAL_ATTACK` is set
# by no edition, standing for a flag introduced after every edition here.
_MOVABLE_TOWERS = RuleFlag(flag_id="MOVABLE_TOWERS", values=("off", "on"), default="off")
_DIAGONAL_ATTACK = RuleFlag(flag_id="DIAGONAL_ATTACK", values=("no", "yes"), default="no")
_FLAGS = {flag.flag_id: flag for flag in (_MOVABLE_TOWERS, _DIAGONAL_ATTACK)}

_LATER_EDITION_ID = "1-3:PRE-RELEASE"
_TABLE = {
    **EDITIONS,
    _LATER_EDITION_ID: Edition(
        edition_id=_LATER_EDITION_ID,
        distribution=EDITIONS[ACTIVE_EDITION].distribution,
        flag_values={"MOVABLE_TOWERS": "on"},
    ),
}


def _play(seed: int):
    white = RandomCtfPlayer("Random White", random.Random(seed))
    black = RandomCtfPlayer("Random Black", random.Random(seed + 1))
    return play_match(white, black, render_final_board=False)


def test_write_record_has_the_documented_sections_in_order():
    match_result = _play(1)
    record = write_record(
        match_result.game_result,
        white_name="White",
        black_name="Black",
        event="Event",
        site="Site",
        date="2026.07.10",
        round_number="1",
    )

    header, position_block, move_sequence = record.strip("\n").split("\n\n")

    expected_result = _RESULT_TAGS[match_result.game_result.outcome]
    assert header.splitlines() == [
        '[Event "Event"]',
        '[Site "Site"]',
        '[Date "2026.07.10"]',
        '[Round "1"]',
        '[White "White"]',
        '[Black "Black"]',
        _RULESET_TAG,
        f'[Result "{expected_result}"]',
        f'[ResultReason "{match_result.game_result.result_reason}"]',
    ]

    assert position_block == match_result.game_result.opening_board
    assert len(position_block.splitlines()) == 12

    move_lines = move_sequence.splitlines()
    total_plies = len(match_result.game_result.game_log)
    assert len(move_lines) == (total_plies + 1) // 2
    assert move_lines[0].startswith("1. ")


def test_write_record_omits_unpopulated_tags():
    match_result = _play(5)
    record = write_record(match_result.game_result)
    expected_result = _RESULT_TAGS[match_result.game_result.outcome]

    header = record.strip("\n").split("\n\n")[0]
    assert header.splitlines() == [
        _RULESET_TAG,
        f'[Result "{expected_result}"]',
        f'[ResultReason "{match_result.game_result.result_reason}"]',
    ]


def test_write_record_omits_tags_individually():
    match_result = _play(5)
    record = write_record(match_result.game_result, white_name="White")
    expected_result = _RESULT_TAGS[match_result.game_result.outcome]

    header = record.strip("\n").split("\n\n")[0]
    assert header.splitlines() == [
        '[White "White"]',
        _RULESET_TAG,
        f'[Result "{expected_result}"]',
        f'[ResultReason "{match_result.game_result.result_reason}"]',
    ]


def test_write_record_always_includes_ruleset_tag():
    # The Ruleset tag is mandatory even when no roster tags are supplied, so the
    # rules a stored game was played under are recoverable from the record alone.
    match_result = _play(5)
    record = write_record(match_result.game_result)
    assert _RULESET_TAG in record
    # The full edition id, never a bare ruleset name: the name is a pointer that
    # moves, so it would not pin anything.
    assert _RULESET_TAG == '[Ruleset "1-2:PRE-RELEASE"]'


def test_write_record_result_reflects_absolute_outcome():
    match_result = _play(5)
    record = write_record(match_result.game_result)
    expected_result = _RESULT_TAGS[match_result.game_result.outcome]
    assert f'[Result "{expected_result}"]' in record


def test_write_record_result_reason_reflects_the_ending():
    # ResultReason now carries the terminal position's outcome_reason, never
    # the old "Unknown" placeholder.
    match_result = _play(5)
    reason = match_result.game_result.result_reason
    record = write_record(match_result.game_result)
    assert reason
    assert '[ResultReason "Unknown"]' not in record
    assert f'[ResultReason "{reason}"]' in record


def test_write_record_escapes_quotes_and_backslashes_in_tag_values():
    match_result = _play(5)
    record = write_record(
        match_result.game_result,
        white_name='Ann "Ace" \\ Smith',
        event="Line1\nLine2",
    )
    header = record.strip("\n").split("\n\n")[0]

    # Quotes and backslashes are backslash-escaped; the newline is collapsed to
    # a space, so every tag stays on its own well-formed line.
    assert '[White "Ann \\"Ace\\" \\\\ Smith"]' in header
    assert '[Event "Line1 Line2"]' in header
    # The header still has exactly one line per tag (no split by the newline).
    assert len(header.splitlines()) == 5  # Event, White, Ruleset, Result, ResultReason


def test_write_record_lone_final_white_ply_on_odd_length_games():
    match_result = _play(1)
    game_log = match_result.game_result.game_log
    if len(game_log) % 2 == 0:
        # Trim the log by one ply so the game ends on White's move, matching
        # the "lone final White ply" case regardless of how this particular
        # game actually ended.
        game_log = game_log[:-1]
        game_result = dataclasses.replace(match_result.game_result, game_log=game_log)
        match_result = dataclasses.replace(match_result, game_result=game_result)

    record = write_record(match_result.game_result)
    move_sequence = record.strip("\n").split("\n\n")[2]
    last_line = move_sequence.splitlines()[-1]
    # A lone final White ply: "N. <ply>" with no second ply on that line.
    assert len(last_line.split(" ")) == 2


def test_active_edition_distribution_matches_the_army_roster():
    # The edition spells its distribution out rather than reading ARMY_ROSTER, so
    # that a later roster change cannot retroactively alter what a published
    # edition (and every record stamped with it) meant. This is the check that
    # keeps the deliberate duplication honest: placement validation enforces
    # ARMY_ROSTER on every game, so a divergence would mean records stamped with
    # the active edition were played under something else.
    #
    # If this fails because the roster changed: that is a rules change, and the
    # fix is to update rules.md and publish a *new* edition, not to edit the
    # existing edition's distribution to match. See doc/ruleset/CLAUDE.md, "The
    # document leads; the code follows" — this assertion cannot tell those two
    # apart, so making it green is not evidence of having done the right one.
    assert EDITIONS[ACTIVE_EDITION].distribution == ARMY_ROSTER


def test_active_configuration_names_the_active_edition_with_no_deviations():
    configuration = active_configuration()
    assert configuration.edition == ACTIVE_EDITION
    # No flag exists to deviate on yet, so this is the only configuration the
    # engine currently produces.
    assert configuration.flags == {}


def test_render_is_the_bare_edition_id_when_nothing_deviates():
    assert active_configuration().render() == ACTIVE_EDITION
    assert active_configuration().render() == "1-2:PRE-RELEASE"  # dash, not dot


def test_render_orders_flags_alphabetically_whatever_the_insertion_order():
    # Two configurations that mean the same thing must render identically, or a
    # record's text form would not be stable and two identical configurations
    # would compare unequal as strings.
    one = RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on", "DIAGONAL_ATTACK": "yes"})
    other = RulesetConfiguration(ACTIVE_EDITION, {"DIAGONAL_ATTACK": "yes", "MOVABLE_TOWERS": "on"})
    assert one.render() == other.render()
    assert one.render() == f"{ACTIVE_EDITION} DIAGONAL_ATTACK=yes MOVABLE_TOWERS=on"


def test_stamp_round_trips_through_its_nested_form():
    configuration = RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on"})
    stamp = configuration.as_stamp()
    assert stamp == {"edition": ACTIVE_EDITION, "flags": {"MOVABLE_TOWERS": "on"}}
    assert RulesetConfiguration.from_stamp(stamp) == configuration


def test_stamp_of_an_all_defaults_configuration_still_names_its_edition():
    # An empty flag set is meaningful ("all edition values"); a *missing* edition
    # is not, which is why the edition is always stamped even when no flag is.
    assert active_configuration().as_stamp() == {"edition": ACTIVE_EDITION, "flags": {}}


@pytest.mark.parametrize(
    "raw",
    [
        "1-2:PRE-RELEASE",  # the rendered string, not the structured form
        {"edition": ACTIVE_EDITION},  # no flags key
        {"flags": {}},  # no edition key
        {"edition": 12, "flags": {}},  # edition is not an id
        {"edition": ACTIVE_EDITION, "flags": {"MOVABLE_TOWERS": True}},  # value not a label
        {"edition": ACTIVE_EDITION, "flags": ["MOVABLE_TOWERS"]},  # flags not a mapping
    ],
)
def test_from_stamp_rejects_a_structurally_unusable_stamp(raw):
    # A stamp that is present but unreadable is no better than an absent one: it
    # must fail by name rather than raise a KeyError or yield a wrong
    # configuration that then gets trusted.
    with pytest.raises(ValueError):
        RulesetConfiguration.from_stamp(raw)


def test_resolve_flag_prefers_the_configurations_own_deviation():
    configuration = RulesetConfiguration(_LATER_EDITION_ID, {"MOVABLE_TOWERS": "off"})
    # The edition sets `on`; the configuration deviates back to `off`.
    assert resolve_flag(configuration, "MOVABLE_TOWERS", rule_flags=_FLAGS, editions=_TABLE) == "off"


def test_resolve_flag_falls_back_to_the_editions_value_not_the_flag_default():
    # This is the case that makes resolution two-level: absent from the
    # configuration, present on the edition, and the edition's `on` must win over
    # the flag's own `off` default.
    configuration = RulesetConfiguration(_LATER_EDITION_ID)
    assert resolve_flag(configuration, "MOVABLE_TOWERS", rule_flags=_FLAGS, editions=_TABLE) == "on"


def test_resolve_flag_uses_the_flag_default_when_the_edition_predates_the_flag():
    # The active edition sets no flags at all, so a flag introduced after it
    # resolves to its own default — the second level, and the one that makes
    # retrofitting a flag a no-op for an existing edition.
    configuration = active_configuration()
    assert resolve_flag(configuration, "MOVABLE_TOWERS", rule_flags=_FLAGS, editions=_TABLE) == "off"
    assert resolve_flag(configuration, "DIAGONAL_ATTACK", rule_flags=_FLAGS, editions=_TABLE) == "no"


def test_unsupported_aspects_is_empty_for_what_this_code_plays():
    # The configuration the engine stamps must be one it can implement, or every
    # checkpoint it wrote would be rejected on load.
    assert unsupported_aspects(active_configuration()) == []


def test_unsupported_aspects_names_a_flag_this_code_does_not_have():
    # The published registry is empty, so any flag at all is unknown here — which
    # is exactly the state a checkpoint from a variant branch would arrive in.
    configuration = RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on"})
    (aspect,) = unsupported_aspects(configuration)
    assert "MOVABLE_TOWERS" in aspect
    assert "no such flag" in aspect
    # Reported as absent, not as a value mismatch: the two mean different things
    # to whoever reads the failure.
    assert "knows only" not in aspect


def test_unsupported_aspects_names_a_value_label_the_flag_does_not_have():
    configuration = RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "sideways"})
    (aspect,) = unsupported_aspects(configuration, rule_flags=_FLAGS, editions=_TABLE)
    assert "sideways" in aspect
    assert "knows only" in aspect
    assert "'off', 'on'" in aspect


def test_unsupported_aspects_names_an_unknown_edition():
    configuration = RulesetConfiguration("9-9:BERSERKER")
    (aspect,) = unsupported_aspects(configuration)
    assert "9-9:BERSERKER" in aspect


def test_unsupported_aspects_ignores_flags_the_configuration_omits():
    # Omission is safe by construction: every default is behavior-preserving, so
    # an absent flag means the behavior this code already implements. The check
    # only ever runs over what is explicitly listed.
    assert unsupported_aspects(active_configuration(), rule_flags=_FLAGS, editions=_TABLE) == []


def test_configuration_differences_is_empty_when_both_sides_agree():
    configuration = RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on"})
    assert (
        configuration_differences(
            configuration,
            RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on"}),
            left_label="run config",
            right_label="checkpoint",
        )
        == []
    )


def test_configuration_differences_reports_edition_and_flags_with_their_sources():
    differences = configuration_differences(
        RulesetConfiguration(ACTIVE_EDITION, {"MOVABLE_TOWERS": "on"}),
        RulesetConfiguration(_LATER_EDITION_ID),
        left_label="run config",
        right_label="checkpoint",
    )
    assert len(differences) == 2
    edition_difference, flag_difference = differences
    assert "run config" in edition_difference and ACTIVE_EDITION in edition_difference
    assert "checkpoint" in edition_difference and _LATER_EDITION_ID in edition_difference
    # A flag one side lists and the other omits is a difference, and must read as
    # one rather than as a missing value.
    assert "MOVABLE_TOWERS" in flag_difference
    assert "no deviation" in flag_difference

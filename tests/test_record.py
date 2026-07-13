"""Tests for the game-record file writer."""

import dataclasses
import random

from capture_the_flag.match import play_match
from capture_the_flag.player import RandomCtfPlayer
from capture_the_flag.record import RULESET_NAME, RULESET_VERSION, write_record

_RESULT_TAGS = {1: "1-0", -1: "0-1", 0: "1/2-1/2"}
_RULESET_TAG = f'[Ruleset "{RULESET_NAME}:{RULESET_VERSION}"]'


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
    # The Ruleset tag is mandatory even when no roster tags are supplied, so a
    # reader can always tell which ruleset (variant and version) a game was
    # played under.
    match_result = _play(5)
    record = write_record(match_result.game_result)
    assert _RULESET_TAG in record
    assert _RULESET_TAG == '[Ruleset "PRIMARY:1.1"]'  # current variant:version


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

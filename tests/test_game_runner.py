"""Tests for the single-game runner: result announcement and end-to-end wiring."""

import pytest
from game_engine_core.models.game_result import GameResult

from capture_the_flag import game_runner
from capture_the_flag.game_runner import announce_result

_LOG_ENTRY = ("A4-A5", "<board>")


@pytest.mark.parametrize(
    ("outcome", "reason", "log_length", "expected"),
    [
        (1, "Flag Captured", 3, "Alice (White) wins — Flag Captured, after 3 plies."),
        (-1, "Inactivity", 2, "Bob (Black) wins — Inactivity, after 2 plies."),
        (0, "No Progress", 4, "Draw — No Progress, after 4 plies."),
    ],
)
def test_announce_result_names_winner_reason_and_length(
    outcome, reason, log_length, expected
):
    result = GameResult(
        outcome=outcome,
        result_reason=reason,
        opening_board="<board>",
        game_log=[_LOG_ENTRY] * log_length,
    )
    assert announce_result(result, "Alice", "Bob") == expected


def test_main_plays_machine_vs_machine_and_announces(capsys):
    # Random-vs-random needs no input, so main() runs to completion headlessly
    # (aside from the rendered board it prints). The seed keeps it reproducible.
    game_runner.main(["--white", "random", "--black", "random", "--seed", "7"])
    out = capsys.readouterr().out
    assert (" wins — " in out) or ("Draw — " in out)

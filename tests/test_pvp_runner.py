"""Tests for the PvP runner's result announcement."""

import pytest
from game_engine_core.models.game_result import GameResult

from capture_the_flag.pvp_runner import announce_result

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

"""Tests for the headless batch runner."""

import random

import pytest

from capture_the_flag.batch_runner import run_batch
from capture_the_flag.outcome import (
    REASON_FLAG_CAPTURED,
    REASON_INACTIVITY,
    REASON_NO_LEGAL_MOVE,
)

_KNOWN_REASONS = frozenset(
    {
        REASON_FLAG_CAPTURED,
        REASON_INACTIVITY,
        REASON_NO_LEGAL_MOVE,
    }
)


def test_run_batch_writes_one_record_per_game_and_tallies_outcomes(tmp_path):
    summary = run_batch(5, tmp_path, rng=random.Random(1))

    record_files = sorted(tmp_path.glob("*.ctfgame"))
    assert len(record_files) == 5
    assert [f.name for f in record_files] == [
        "game_1.ctfgame",
        "game_2.ctfgame",
        "game_3.ctfgame",
        "game_4.ctfgame",
        "game_5.ctfgame",
    ]

    for record_file in record_files:
        text = record_file.read_text(encoding="utf-8")
        assert '[Result "' in text
        assert '[ResultReason "Unknown"]' not in text

    assert summary.games_played == 5
    assert summary.white_wins + summary.black_wins + summary.draws == 5
    assert summary.min_plies <= summary.mean_plies <= summary.max_plies
    assert summary.min_plies > 0


def test_run_batch_summary_breaks_down_endings_by_reason(tmp_path):
    summary = run_batch(8, tmp_path, rng=random.Random(3))

    # Every reported reason is from the game's vocabulary, and the breakdown
    # accounts for exactly the games played.
    assert set(summary.reason_counts) <= _KNOWN_REASONS
    assert sum(summary.reason_counts.values()) == summary.games_played == 8
    # The reason line renders and names each counted ending.
    endings_line = next(
        line for line in summary.format().splitlines() if line.startswith("Endings:")
    )
    for reason in summary.reason_counts:
        assert reason in endings_line


def test_run_batch_zero_pads_filenames_to_batch_width(tmp_path):
    run_batch(12, tmp_path, rng=random.Random(2))

    record_files = sorted(tmp_path.glob("*.ctfgame"))
    assert [f.name for f in record_files][:2] == ["game_01.ctfgame", "game_02.ctfgame"]
    assert record_files[-1].name == "game_12.ctfgame"


def test_run_batch_is_reproducible_with_a_seeded_rng(tmp_path):
    # select_ply's RandomEngine draws from the process-global `random`
    # module, so full reproducibility needs both it and the injected rng
    # (which seeds placement only) seeded identically before each run.
    random.seed(42)
    summary_a = run_batch(4, tmp_path / "a", rng=random.Random(42))
    random.seed(42)
    summary_b = run_batch(4, tmp_path / "b", rng=random.Random(42))

    assert summary_a == summary_b
    for file_a, file_b in zip(
        sorted((tmp_path / "a").glob("*.ctfgame")),
        sorted((tmp_path / "b").glob("*.ctfgame")),
        strict=True,
    ):
        assert file_a.read_text() == file_b.read_text()


def test_run_batch_rejects_non_positive_game_counts(tmp_path):
    with pytest.raises(ValueError):
        run_batch(0, tmp_path)

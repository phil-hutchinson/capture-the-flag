"""The readable companion file.

`timings.json` is what a comparison is computed from; `timings.txt` is what a
person reads. The properties worth pinning down are that the two describe the
same measurement, that the text is what the run actually printed, and that a run
directory accumulating several measurements keeps each pair together.
"""

import json
from pathlib import Path

import pytest

from capture_the_flag.batch_runner import run_batch
from capture_the_flag.timing_record import (
    TIMING_RECORD_FILENAME,
    TIMING_RECORD_STEM,
    TIMING_TEXT_FILENAME,
)


def test_the_text_record_holds_the_breakdown_the_run_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_batch(2, tmp_path, seed=11, timing=True)

    printed = capsys.readouterr().out
    text = (tmp_path / TIMING_TEXT_FILENAME).read_text(encoding="utf-8")

    breakdown = text.split("region", 1)[1]
    assert breakdown.rstrip() in printed, "the file and the terminal disagree"


def test_the_text_record_matches_the_json_it_accompanies(tmp_path: Path) -> None:
    """Rendering the JSON's tree reproduces the text file's breakdown — the two
    files are one measurement in two forms, not two measurements."""
    run_batch(2, tmp_path, seed=11, timing=True)

    record = json.loads(
        (tmp_path / TIMING_RECORD_FILENAME).read_text(encoding="utf-8")
    )
    text = (tmp_path / TIMING_TEXT_FILENAME).read_text(encoding="utf-8")

    root_line = next(
        line for line in text.splitlines() if line.startswith(record["timings"]["name"])
    )
    assert f"{record['timings']['calls']:,}" in root_line
    assert "%root" in text  # the aligned tree's header, not a bare dump


def test_the_batch_summary_heads_the_text_record(tmp_path: Path) -> None:
    """A run's own report of itself goes above the tree, so the file stands on
    its own without the terminal it came from."""
    summary = run_batch(2, tmp_path, seed=11, timing=True)

    text = (tmp_path / TIMING_TEXT_FILENAME).read_text(encoding="utf-8")

    assert text.startswith(summary.format().splitlines()[0])
    assert "Games played: 2" in text
    assert text.index("Games played") < text.index("region")


def test_both_companions_are_absent_when_a_run_is_not_measured(tmp_path: Path) -> None:
    run_batch(2, tmp_path, seed=11, timing=False)

    assert not (tmp_path / TIMING_RECORD_FILENAME).exists()
    assert not (tmp_path / TIMING_TEXT_FILENAME).exists()


def test_the_companions_share_a_stem(tmp_path: Path) -> None:
    run_batch(2, tmp_path, seed=11, timing=True)

    written = {path.name for path in tmp_path.glob(f"{TIMING_RECORD_STEM}.*")}
    assert written == {TIMING_RECORD_FILENAME, TIMING_TEXT_FILENAME}


def test_nesting_survives_as_indentation(tmp_path: Path) -> None:
    """The text form's whole value is that the tree is readable, so the depth of
    a region has to show as indentation rather than being flattened away."""
    run_batch(2, tmp_path, seed=11, timing=True)

    text = (tmp_path / TIMING_TEXT_FILENAME).read_text(encoding="utf-8")

    assert "\nplay-games" not in text  # not at the root's depth
    assert "\n  play-games" in text
    assert "\n    starting-position" in text

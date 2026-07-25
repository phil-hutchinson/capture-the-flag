"""Instrumentation must not change what it measures.

Two guarantees the story rests on, enforced here rather than assumed:

- A measured run plays the *same games* an unmeasured one does. If timing could
  perturb play, every number it produced would describe a run nobody else could
  reproduce.
- Two identically seeded measured runs record the *same call counts*. Seconds
  are noise-prone and never compared for equality; counts are exact, which is
  what makes "this change halved the ply generations" a claim worth making even
  on a noisy machine.

Marked `slow`: these play real games, including with the learned engine.
"""

import json
from pathlib import Path

import pytest

from capture_the_flag.batch_runner import run_batch
from capture_the_flag.timing_record import TIMING_RECORD_FILENAME

SEED = 424242
SEARCH_ITERATIONS = 3
"""A learned seat at its cheapest — enough to exercise the search boundary and
everything under it, not enough to make the test expensive."""


def game_records(directory: Path) -> list[str]:
    return [
        path.read_text(encoding="utf-8") for path in sorted(directory.glob("*.ctfgame"))
    ]


def call_counts(directory: Path) -> list[tuple[str, int]]:
    """Every region in the record as `(path, calls)`, depth-first.

    Compared as a list so a difference in tree *shape* — a region reached on one
    run and not the other — fails as loudly as a difference in counts.
    """
    record = json.loads(
        (directory / TIMING_RECORD_FILENAME).read_text(encoding="utf-8")
    )

    def walk(node: dict, prefix: str) -> list[tuple[str, int]]:
        path = f"{prefix}/{node['name']}"
        counts = [(path, node["calls"])]
        for child in node["children"]:
            counts.extend(walk(child, path))
        return counts

    return walk(record["timings"], "")


@pytest.mark.slow
def test_measuring_does_not_change_the_games_played(tmp_path: Path) -> None:
    timed, untimed = tmp_path / "timed", tmp_path / "untimed"

    run_batch(
        2,
        timed,
        seed=SEED,
        white_kind="neural",
        black_kind="neural",
        iterations=SEARCH_ITERATIONS,
        timing=True,
    )
    run_batch(
        2,
        untimed,
        seed=SEED,
        white_kind="neural",
        black_kind="neural",
        iterations=SEARCH_ITERATIONS,
        timing=False,
    )

    assert game_records(timed) == game_records(untimed)
    assert game_records(timed), "the comparison is only meaningful if games were played"


@pytest.mark.slow
def test_identically_seeded_runs_record_identical_call_counts(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"

    for directory in (first, second):
        run_batch(
            2,
            directory,
            seed=SEED,
            white_kind="neural",
            black_kind="neural",
            iterations=SEARCH_ITERATIONS,
            timing=True,
        )

    counts = call_counts(first)
    assert call_counts(second) == counts
    # A run that recorded nothing would satisfy the equality trivially.
    assert any(calls > 100 for _, calls in counts)


@pytest.mark.slow
def test_random_play_is_unaffected_too(tmp_path: Path) -> None:
    """The learned engine is the interesting case, but the mechanics regions are
    instrumented for every seat, so the guarantee has to hold without a network
    in the picture."""
    timed, untimed = tmp_path / "timed", tmp_path / "untimed"

    run_batch(4, timed, seed=SEED, timing=True)
    run_batch(4, untimed, seed=SEED, timing=False)

    assert game_records(timed) == game_records(untimed)

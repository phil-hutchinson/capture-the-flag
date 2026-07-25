"""The batch runner's timing switch and the record it leaves behind.

Random seats only: this covers the record's shape and the switch, not the
learned engine's cost, so it stays fast enough for the default suite.
"""

import json
from pathlib import Path

from capture_the_flag.batch_runner import run_batch
from capture_the_flag.timing_record import TIMING_RECORD_FILENAME
from capture_the_flag.timing_regions import PLAY_GAMES, ROOT_BATCH


def timing_record(directory: Path) -> dict:
    return json.loads((directory / TIMING_RECORD_FILENAME).read_text(encoding="utf-8"))


def test_a_timed_batch_writes_a_record_beside_its_games(tmp_path: Path) -> None:
    run_batch(2, tmp_path, seed=11, timing=True)

    record = timing_record(tmp_path)
    assert record["kind"] == ROOT_BATCH
    assert record["settings"]["games"] == 2
    assert record["settings"]["seed"] == 11
    assert record["environment"]["versions"]["python"]
    assert record["environment"]["machine"]["cpu_count"]


def test_the_record_holds_the_whole_tree_under_one_root(tmp_path: Path) -> None:
    run_batch(2, tmp_path, seed=11, timing=True)

    timings = timing_record(tmp_path)["timings"]
    assert timings["name"] == ROOT_BATCH
    assert timings["percent_of_root"] == 100.0

    play_games = next(
        child for child in timings["children"] if child["name"] == PLAY_GAMES
    )
    # Two games, so the placement callback ran twice inside the shared runner.
    starting = next(
        child for child in play_games["children"] if child["name"] == "starting-position"
    )
    assert starting["calls"] == 2


def test_children_never_claim_more_than_their_parent(tmp_path: Path) -> None:
    """The reconciliation property: a parent's time covers its children plus a
    non-negative remainder, at every level."""
    run_batch(2, tmp_path, seed=11, timing=True)

    def check(node: dict) -> None:
        children_total = sum(child["seconds"] for child in node["children"])
        assert children_total <= node["seconds"] + 1e-6
        assert node["unattributed_seconds"] >= -1e-6
        for child in node["children"]:
            check(child)

    check(timing_record(tmp_path)["timings"])


def test_an_untimed_batch_writes_no_record(tmp_path: Path) -> None:
    run_batch(2, tmp_path, seed=11, timing=False)

    assert not (tmp_path / TIMING_RECORD_FILENAME).exists()
    assert list(tmp_path.glob("*.ctfgame"))  # the games themselves still happened

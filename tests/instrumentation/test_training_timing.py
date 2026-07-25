"""What a measured training run leaves behind.

Marked `slow`, like the other tests that run real self-play and gradient
descent: even at a tiny search budget a generation is far too expensive for the
default suite.
"""

import json
from pathlib import Path

import pytest

from capture_the_flag.engines.neural_network.ctf_training_run import (
    TIMING_RESUME_STEM_TEMPLATE,
    TrainingConfig,
    resume_generations,
    train_generations,
)
from capture_the_flag.timing_record import (
    TIMING_RECORD_FILENAME,
    TIMING_TEXT_FILENAME,
)
from capture_the_flag.timing_regions import (
    GENERATION,
    ROOT_TRAINING,
    SAVE_CHECKPOINT,
    SELF_PLAY,
    TRAIN,
)
from tests.engines.neural_network.small_networks import (
    SMALL_FEATURE_COUNT,
    SMALL_RESIDUAL_BLOCK_COUNT,
)

TINY_RUN = TrainingConfig(
    generations=2,
    games_per_generation=1,
    self_play_iterations=6,
    epochs_per_generation=1,
    batch_size=8,
    feature_count=SMALL_FEATURE_COUNT,
    residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
    seed=0,
)


def node(timings: dict, *path: str) -> dict:
    current = timings
    for name in path:
        matches = [child for child in current["children"] if child["name"] == name]
        assert matches, f"no {name!r} under {current['name']!r}"
        current = matches[0]
    return current


def read_record(run_dir: Path, filename: str = TIMING_RECORD_FILENAME) -> dict:
    return json.loads((run_dir / filename).read_text(encoding="utf-8"))


@pytest.mark.slow
def test_a_measured_run_records_its_generations_and_their_halves(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=True)

    record = read_record(run_dir)
    assert record["kind"] == ROOT_TRAINING
    # The hyperparameters travel with the timings, not only in run-config.json.
    assert record["settings"]["self_play_iterations"] == 6
    assert record["settings"]["generations"] == 2

    timings = record["timings"]
    assert timings["name"] == ROOT_TRAINING

    generation = node(timings, GENERATION)
    assert generation["calls"] == 2  # cumulative across the run's generations
    self_play = node(generation, SELF_PLAY)
    training = node(generation, TRAIN)
    assert node(generation, SAVE_CHECKPOINT)["calls"] == 2
    # Producing the data costs more than learning from it — the split the story
    # exists to confirm rather than assume.
    assert self_play["seconds"] > training["seconds"]


@pytest.mark.slow
def test_the_search_boundary_is_visible_inside_self_play(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=True)

    self_play = node(read_record(run_dir)["timings"], GENERATION, SELF_PLAY)
    search = node(self_play, "search-with-policy")
    # Our instrumented work sits under the search call; what is left over is the
    # pinned engine's own internals.
    assert node(search, "evaluate-position")["calls"] > 0
    assert search["unattributed_seconds"] > 0


@pytest.mark.slow
def test_the_text_record_carries_the_runs_generation_lines(tmp_path) -> None:
    """A training run's text companion reads as the whole story of the run: what
    each generation's loss did, then where the time went."""
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=True)

    text = (run_dir / TIMING_TEXT_FILENAME).read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0].startswith("generation   1: total loss")
    assert lines[1].startswith("generation   2: total loss")
    assert text.index("generation   1") < text.index("region")
    # The breakdown is there too, with the run's own regions in it.
    assert f"\n  {GENERATION}" in text
    assert f"\n    {SELF_PLAY}" in text


@pytest.mark.slow
def test_every_checkpoint_leaves_a_readable_record(tmp_path) -> None:
    """A record exists from the first checkpoint onward, so a run that is killed
    part-way through still accounts for the generations it finished. Inspected
    from the progress callback, which is the only vantage point *inside* a run."""
    seen: list[dict] = []

    def inspect(_generation: int, _history: list) -> None:
        run_dir = next(path for path in tmp_path.iterdir() if path.is_dir())
        seen.append(read_record(run_dir)["timings"])
        assert (run_dir / TIMING_TEXT_FILENAME).exists(), "no readable companion"

    run_dir = train_generations(
        TINY_RUN, base_dir=tmp_path, progress=inspect, timing=True
    )

    # One record per generation, each covering the generations finished so far.
    assert [node(timings, GENERATION)["calls"] for timings in seen] == [1, 2]
    # The root is still open at that point; a snapshot that did not credit it
    # would report the whole run as zero seconds, and every share with it.
    assert all(timings["seconds"] > 0 for timings in seen)
    assert all(timings["percent_of_root"] == 100.0 for timings in seen)
    # The final write replaces the last interim one rather than adding a file.
    assert sorted(path.name for path in run_dir.glob("timings*")) == [
        TIMING_RECORD_FILENAME,
        TIMING_TEXT_FILENAME,
    ]
    assert node(read_record(run_dir)["timings"], GENERATION)["calls"] == 2


@pytest.mark.slow
def test_a_resume_writes_its_own_record_and_leaves_the_original(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=True)
    original = read_record(run_dir)

    resume_generations(1, base_dir=tmp_path, timing=True)

    assert read_record(run_dir) == original, "the baseline record was overwritten"
    resumed = read_record(run_dir, f"{TIMING_RESUME_STEM_TEMPLATE.format(index=1)}.json")
    assert resumed["settings"]["resumed_from_checkpoint"] == 2
    assert node(resumed["timings"], GENERATION)["calls"] == 1

    # Both companions, under the resume's own stem, beside the untouched originals.
    stem = TIMING_RESUME_STEM_TEMPLATE.format(index=1)
    assert (run_dir / f"{stem}.txt").read_text(encoding="utf-8").startswith(
        "generation   3: total loss"
    )
    assert (run_dir / TIMING_TEXT_FILENAME).exists()


@pytest.mark.slow
def test_an_unmeasured_run_writes_no_record(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=False)

    assert not (run_dir / TIMING_RECORD_FILENAME).exists()
    assert not (run_dir / TIMING_TEXT_FILENAME).exists()
    assert (run_dir / "run-config.json").exists()

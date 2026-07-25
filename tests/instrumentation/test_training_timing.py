"""What a measured training run leaves behind.

Marked `slow`, like the other tests that run real self-play and gradient
descent: even at a tiny search budget a generation is far too expensive for the
default suite.
"""

import json
from pathlib import Path

import pytest

from capture_the_flag.engines.neural_network.ctf_training_run import (
    TIMING_RESUME_FILENAME_TEMPLATE,
    TrainingConfig,
    resume_generations,
    train_generations,
)
from capture_the_flag.timing_record import TIMING_RECORD_FILENAME
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
def test_a_resume_writes_its_own_record_and_leaves_the_original(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=True)
    original = read_record(run_dir)

    resume_generations(1, base_dir=tmp_path, timing=True)

    assert read_record(run_dir) == original, "the baseline record was overwritten"
    resumed = read_record(run_dir, TIMING_RESUME_FILENAME_TEMPLATE.format(index=1))
    assert resumed["settings"]["resumed_from_checkpoint"] == 2
    assert node(resumed["timings"], GENERATION)["calls"] == 1


@pytest.mark.slow
def test_an_unmeasured_run_writes_no_record(tmp_path) -> None:
    run_dir = train_generations(TINY_RUN, base_dir=tmp_path, timing=False)

    assert not (run_dir / TIMING_RECORD_FILENAME).exists()
    assert (run_dir / "run-config.json").exists()

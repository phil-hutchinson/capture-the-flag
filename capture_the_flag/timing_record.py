"""The per-run timing record: settings, environment, and the breakdown, in one
file.

A timing table on its own is uninterpretable a month later — it does not say
what search budget produced it, on what machine, at what commit. So every run
that measures itself writes all three together, and the file is the unit that
gets compared against a future run.

The record is written next to whatever the run already produces (the batch's
game records, the training run's checkpoints), so a run directory holds its own
evidence rather than pointing at a separate log. A long run rewrites it as it
goes — see `report_timings`' `echo` — so that a run which never reaches its own
ending still accounts for the work it did finish.
"""

import json
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .device import ResolvedDevice
from .instrumentation.report import (
    RegionReport,
    build_report,
    format_report,
    report_to_dict,
)
from .instrumentation.timing import TimingSession, timing_session
from .run_environment import environment_facts

TIMING_RECORD_STEM = "timings"
"""The base name of a run's record pair.

Two files, one measurement: `<stem>.json` is what a later comparison computes
from, `<stem>.txt` is the same breakdown in the aligned tree a person actually
reads. Sharing a stem keeps the pair identifiable when a directory accumulates
more than one (a resumed training run).
"""

TIMING_RECORD_FILENAME = f"{TIMING_RECORD_STEM}.json"
TIMING_TEXT_FILENAME = f"{TIMING_RECORD_STEM}.txt"

TIMING_ON_BY_DEFAULT = True
"""Whether entry points measure themselves unless told otherwise.

On, because measuring proved to cost about 0.2% of a run — small enough that
requiring a flag would mostly produce interesting runs nobody thought to
measure. `--no-timing` on either runner opts out, leaving the always-installed
wrappers at roughly 0.06%.

The evidence, the recipe that produced it, and the conditions that would call
for revisiting it are in
`doc/plan/00000029-measure-speed-during-training/measurement-recipe.md`.
"""


@contextmanager
def timing_run(root_name: str, *, enabled: bool) -> Generator[TimingSession | None]:
    """Open a run's all-inclusive root region, or yield None when disabled.

    Yielding None rather than a dummy session keeps the disabled path honest:
    there is no session, nothing is recorded, and a caller that wants to write a
    record has to check.
    """
    if not enabled:
        yield None
        return
    with timing_session(root_name) as session:
        yield session


def report_timings(
    session: TimingSession,
    *,
    directory: Path,
    kind: str,
    settings: Mapping[str, object],
    resolved_device: ResolvedDevice,
    stem: str = TIMING_RECORD_STEM,
    preamble: Sequence[str] = (),
    echo: bool = True,
    overwrite: bool = True,
) -> tuple[Path, Path]:
    """Write a run's breakdown as both companion files, and print it.

    Returns `(json path, text path)`. One snapshot of the session feeds the JSON,
    the text, and the printed tree, so the three cannot disagree — which matters
    most mid-run, where the session is still open and every snapshot differs
    from the last.

    `settings` is whatever the entry point was asked to do — the batch's game
    count and search budget, the training run's hyperparameters — recorded
    verbatim so the numbers below it can be read in context.

    `resolved_device` is the device this run actually used (see `device.py`),
    recorded in the environment facts rather than re-derived from what the
    machine merely has available.

    `stem` names the pair. Callers override it where one directory accumulates
    more than one measurement (a resumed training run adds to a run directory
    that already holds the original run's record, which must not be overwritten
    — it is the baseline).

    `preamble` is whatever else the run has to say for itself — a training run's
    per-generation loss lines, a batch's outcome tallies — written above the tree
    so the text file stands on its own without the terminal it came from. It is
    not re-printed: a caller supplying it has either printed it live already or
    prints it after.

    `echo=False` writes without printing: what a run in progress does at each
    checkpoint, where a whole tree on the console every generation would be
    noise rather than a report.

    `overwrite=False` steps aside to `<stem>-2`, `<stem>-3`, ... when a record
    is already there, for callers whose output directory is routinely reused (a
    batch's `--output-dir`, where the record left over from last time may be a
    baseline someone is keeping). Callers that rewrite one measurement as it
    proceeds — a training run, at every checkpoint — need the default.
    """
    report = build_report(session.snapshot())
    breakdown = format_report(report)

    if not overwrite:
        stem = _free_stem(directory, stem)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{stem}.json"
    json_path.write_text(
        json.dumps(
            _record(report, kind=kind, settings=settings, resolved_device=resolved_device),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    text_path = directory / f"{stem}.txt"
    text = "\n\n".join(["\n".join(preamble), breakdown]) if preamble else breakdown
    text_path.write_text(text + "\n", encoding="utf-8")

    if echo:
        print(f"\n{breakdown}\n\nTimings written to {json_path} and {text_path.name}")
    return json_path, text_path


def _free_stem(directory: Path, stem: str) -> str:
    """`stem` if neither companion is already there, else the first numbered
    variant that is free. Both files are checked, so a half-written pair does
    not get half-overwritten."""
    if not _stem_taken(directory, stem):
        return stem
    index = 2
    while _stem_taken(directory, f"{stem}-{index}"):
        index += 1
    return f"{stem}-{index}"


def _stem_taken(directory: Path, stem: str) -> bool:
    return (directory / f"{stem}.json").exists() or (directory / f"{stem}.txt").exists()


def _record(
    report: RegionReport,
    *,
    kind: str,
    settings: Mapping[str, object],
    resolved_device: ResolvedDevice,
) -> dict[str, object]:
    """The machine-readable record: what was run, where, and what it cost."""
    return {
        "created": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "settings": dict(settings),
        "environment": environment_facts(resolved_device),
        "timings": report_to_dict(report),
    }

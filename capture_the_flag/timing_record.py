"""The per-run timing record: settings, environment, and the breakdown, in one
file.

A timing table on its own is uninterpretable a month later — it does not say
what search budget produced it, on what machine, at what commit. So every run
that measures itself writes all three together, and the file is the unit that
gets compared against a future run.

The record is written next to whatever the run already produces (the batch's
game records, the training run's checkpoints), so a run directory holds its own
evidence rather than pointing at a separate log.
"""

import json
from collections.abc import Generator, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .instrumentation.report import build_report, format_report, report_to_dict
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
    stem: str = TIMING_RECORD_STEM,
    preamble: Sequence[str] = (),
) -> tuple[Path, Path]:
    """Print a finished run's breakdown and write both companion files.

    Returns `(json path, text path)`. The printed breakdown and the one written
    to `<stem>.txt` are the same string, rendered once — the readable file cannot
    drift from what the run reported.

    `preamble` is whatever else the run has to say for itself — a training run's
    per-generation loss lines, a batch's outcome tallies — written above the tree
    so the text file stands on its own without the terminal it came from. It is
    not re-printed: a caller supplying it has either printed it live already or
    prints it after.
    """
    breakdown = format_timing_summary(session)
    json_path = write_timing_record(
        session,
        directory=directory,
        kind=kind,
        settings=settings,
        filename=f"{stem}.json",
    )
    text_path = directory / f"{stem}.txt"
    text = "\n\n".join(["\n".join(preamble), breakdown]) if preamble else breakdown
    text_path.write_text(text + "\n", encoding="utf-8")

    print(f"\n{breakdown}\n\nTimings written to {json_path} and {text_path.name}")
    return json_path, text_path


def write_timing_record(
    session: TimingSession,
    *,
    directory: Path,
    kind: str,
    settings: Mapping[str, object],
    filename: str | None = None,
) -> Path:
    """Write a finished session's machine-readable record and return its path.

    `settings` is whatever the entry point was asked to do — the batch's game
    count and search budget, the training run's hyperparameters — recorded
    verbatim so the numbers below it can be read in context.

    `filename` defaults to `timings.json`; callers override it where one
    directory accumulates more than one measurement (a resumed training run adds
    to a run directory that already holds the original run's record, which must
    not be overwritten — it is the baseline).
    """
    record = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "settings": dict(settings),
        "environment": environment_facts(),
        "timings": report_to_dict(build_report(session.root)),
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (filename or TIMING_RECORD_FILENAME)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def format_timing_summary(session: TimingSession) -> str:
    """The console form of a finished session's breakdown."""
    return format_report(build_report(session.root))

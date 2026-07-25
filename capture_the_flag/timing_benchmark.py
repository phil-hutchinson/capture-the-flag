"""The measurement recipe: a fixed workload, run with and without timing.

Runnable as a module: `python -m capture_the_flag.timing_benchmark [options]`.

Two jobs, one workload:

- **What does the instrumentation cost?** The same seeded games are played with
  timing on and off, several times each, and the wall-clock difference is the
  overhead — the number that decides whether measuring can stay switched on
  permanently.
- **What is the baseline?** With `--record-dir`, the timed run's `timings.json`
  is kept. That file is the "before" a later optimization gets compared against,
  which is why the workload is fixed and seeded rather than whatever the
  developer happened to run.

The defaults *are* the recipe. Changing them produces numbers that cannot be
compared with previously recorded ones, so change them only deliberately (and
record that you did) — the point of a recipe is that two people running it a
year apart measure the same thing.

Guarding the comparison:

- The first repetition of anything in a fresh process pays one-time costs
  (torch's lazy initialization, import-time work), so a discarded warm-up runs
  first.
- Timed and untimed repetitions alternate, so a machine that gets slower or
  faster partway through (thermal throttling, a noisy neighbour) biases both
  arms equally instead of only the one that happened to run second.
- Both the mean and the minimum are reported. The minimum is the least
  noise-contaminated estimate of what the work actually costs; a mean that
  disagrees with it by much says the machine was busy and the run should be
  repeated on a quieter one.
"""

import argparse
import contextlib
import io
import statistics
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .batch_runner import run_batch
from .run_environment import environment_facts

BENCHMARK_SEED = 20260724
BENCHMARK_GAMES = 2
BENCHMARK_ITERATIONS = 25
BENCHMARK_REPEATS = 3
"""The recipe: two seeded learned-engine games at 25 search iterations per ply,
on the default network architecture, three times per arm. Small enough to run
routinely (a couple of minutes), real enough that search dominates it the way it
dominates a training run."""


@dataclass(frozen=True)
class ArmResult:
    """One arm of the comparison: the same workload run several times."""

    label: str
    seconds: list[float]

    @property
    def mean(self) -> float:
        return statistics.fmean(self.seconds)

    @property
    def fastest(self) -> float:
        return min(self.seconds)

    @property
    def spread_percent(self) -> float:
        """Slowest over fastest, as a percentage — how noisy the machine was."""
        return 100.0 * (max(self.seconds) / self.fastest - 1.0)

    def format(self) -> str:
        runs = ", ".join(f"{seconds:.2f}s" for seconds in self.seconds)
        return (
            f"{self.label:<12} {runs}   mean {self.mean:.2f}s   "
            f"fastest {self.fastest:.2f}s   spread {self.spread_percent:.1f}%"
        )


def run_workload(*, timing: bool, output_dir: Path, games: int, iterations: int) -> float:
    """Play the benchmark's games once and return the wall clock they took.

    Measured in-process rather than around the interpreter: torch's import cost
    is a constant that would dilute the overhead percentage without telling us
    anything about the instrumentation. The batch's own output is swallowed —
    the breakdown it prints is not what this command is reporting.

    The stopwatch covers the whole of `run_batch`, so on the timed arm it also
    covers emitting the record: rendering the tree, reading the environment
    (which shells out to git), and writing two files. That is deliberate — it is
    part of what having timing on costs — but it is a fixed cost per run rather
    than a per-region one, so it does not scale with the workload the way the
    region entries do. On the recipe's two-game workload it is milliseconds
    against ~20 seconds; on a workload small enough for it to matter, this
    comparison is measuring the wrong thing anyway.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        started = time.perf_counter()
        run_batch(
            games,
            output_dir,
            seed=BENCHMARK_SEED,
            white_kind="neural",
            black_kind="neural",
            iterations=iterations,
            timing=timing,
        )
        return time.perf_counter() - started


def measure(
    *, repeats: int, games: int, iterations: int, record_dir: Path | None
) -> tuple[ArmResult, ArmResult]:
    """Run both arms, alternating, and return `(untimed, timed)`."""
    untimed: list[float] = []
    timed: list[float] = []

    with tempfile.TemporaryDirectory() as scratch:
        scratch_dir = Path(scratch)
        print("warming up (discarded) ...", flush=True)
        run_workload(
            timing=False, output_dir=scratch_dir, games=games, iterations=iterations
        )

        for repeat in range(1, repeats + 1):
            print(f"repetition {repeat} of {repeats} ...", flush=True)
            untimed.append(
                run_workload(
                    timing=False,
                    output_dir=scratch_dir,
                    games=games,
                    iterations=iterations,
                )
            )
            # The last timed repetition writes where the record is wanted, so the
            # kept baseline comes from a measured run rather than an extra one.
            destination = (
                record_dir if record_dir is not None and repeat == repeats else scratch_dir
            )
            timed.append(
                run_workload(
                    timing=True,
                    output_dir=destination,
                    games=games,
                    iterations=iterations,
                )
            )

    return ArmResult("timing off", untimed), ArmResult("timing on", timed)


def format_comparison(untimed: ArmResult, timed: ArmResult) -> str:
    """The verdict: both arms, the overhead, and the noise it has to beat."""
    by_mean = 100.0 * (timed.mean / untimed.mean - 1.0)
    by_fastest = 100.0 * (timed.fastest / untimed.fastest - 1.0)
    noise = max(untimed.spread_percent, timed.spread_percent)
    lines = [
        untimed.format(),
        timed.format(),
        "",
        f"overhead: {by_mean:+.1f}% by mean, {by_fastest:+.1f}% by fastest run",
        f"machine noise (worst spread within an arm): {noise:.1f}%",
    ]
    if noise > abs(by_mean):
        lines.append(
            "note: the run-to-run spread is larger than the measured overhead, "
            "so treat the figure as an upper bound and repeat on a quieter machine "
            "if a tighter number is needed."
        )
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure what the timing instrumentation costs, on a fixed "
        "seeded workload.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=BENCHMARK_REPEATS,
        help=f"repetitions per arm (default: {BENCHMARK_REPEATS})",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=BENCHMARK_GAMES,
        help=f"games per repetition (default: {BENCHMARK_GAMES}; changing it "
        "makes the result incomparable with recorded baselines)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=BENCHMARK_ITERATIONS,
        help=f"search iterations per ply (default: {BENCHMARK_ITERATIONS}; "
        "changing it makes the result incomparable with recorded baselines)",
    )
    parser.add_argument(
        "--record-dir",
        type=Path,
        default=None,
        help="keep the last timed repetition's timings.json here, as the "
        "baseline a later optimization is compared against",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.repeats < 1:
        raise ValueError(f"repeats must be at least 1, got {args.repeats}")

    machine = environment_facts()["machine"]
    print(
        f"workload: {args.games} neural-vs-neural games, {args.iterations} "
        f"search iterations/ply, seed {BENCHMARK_SEED}\n"
        f"machine: {machine}\n"
    )
    untimed, timed = measure(
        repeats=args.repeats,
        games=args.games,
        iterations=args.iterations,
        record_dir=args.record_dir,
    )
    print(f"\n{format_comparison(untimed, timed)}")
    if args.record_dir is not None:
        print(f"\nBaseline record kept in {args.record_dir}")


if __name__ == "__main__":
    main()

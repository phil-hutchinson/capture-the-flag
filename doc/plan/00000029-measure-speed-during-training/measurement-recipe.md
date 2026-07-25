# The measurement recipe, and what instrumentation costs

Companion to [story.md](story.md) (see also
[implementation-plan.md](implementation-plan.md), Step 8). Two things live here:
the fixed procedure for taking a timing measurement, and the result of pointing
that procedure at the instrumentation itself.

## The recipe

```bash
python -m capture_the_flag.timing_benchmark --record-dir <where-to-keep-it>
```

The defaults **are** the recipe: two learned-engine-vs-itself games at 25 search
iterations per ply, on the default network architecture, seeded at 20260724,
three repetitions per arm. It runs in a couple of minutes.

Changing `--games` or `--iterations` produces numbers that cannot be compared
against anything recorded earlier. Change them only deliberately, and say so
wherever the result is written down.

What the command does:

1. Plays the workload once and discards it — a fresh process pays one-time costs
   (torch's lazy initialization in particular) that belong to no measurement.
2. Alternates untimed and timed repetitions, so a machine that drifts partway
   through biases both arms equally.
3. Reports both arms' mean and fastest run, the overhead between them, and the
   worst within-arm spread — the noise the overhead figure has to beat to mean
   anything.
4. With `--record-dir`, keeps the last timed repetition's `timings.json`. That
   file is the "before" for any later optimization: it carries the settings, the
   environment, and the full breakdown, so a comparison made months later is
   still interpretable.

### Comparing a later run against a baseline

Run the same command on the changed code, then compare the two `timings.json`
files region by region. Two cautions, both learned from the numbers below:

- **Check the environments match** before believing a difference. The record
  carries commit, torch version, device, thread counts, and CPU model precisely
  because a thread-count change moves wall clock more than most optimizations
  will.
- **Compare call counts, not just seconds.** Counts are exact and reproducible
  under the seed; seconds are not. A change that halves a region's call count
  has done something real even if the machine was too noisy to show it in
  seconds that day.

## What the instrumentation costs

Measured 2026-07-24, at commit `c21e86b`, on:

| | |
| --- | --- |
| CPU | 11th Gen Intel Core i7-11800H @ 2.30GHz, 16 logical cores |
| Platform | Linux 5.15 (WSL2), glibc 2.36 |
| torch | 2.13.0+cpu, 8 compute threads, 8 interop threads |

### The wall-clock comparison

```
timing off   19.03s, 19.15s, 20.02s   mean 19.40s   fastest 19.03s   spread 5.2%
timing on    18.27s, 18.53s, 20.03s   mean 18.94s   fastest 18.27s   spread 9.6%

overhead: -2.4% by mean, -4.0% by fastest run
machine noise (worst spread within an arm): 9.6%
```

The overhead measures *negative*, which is not a claim that instrumentation
makes the engine faster — it is what "smaller than the noise" looks like. This
machine's own run-to-run spread is up to 9.6%, so the honest reading is: the
cost of measuring is somewhere below the noise floor of a WSL2 laptop, and this
comparison cannot resolve it more finely than that.

### The sharper bound

Since the wall-clock comparison can only put a ceiling on the cost, the same
question was asked a way that noise cannot swamp — measure one region entry, and
multiply by how many a run actually performs:

```python
import timeit
from capture_the_flag.instrumentation.timing import region, timing_session

REPS = 2_000_000
baseline = timeit.timeit("pass", number=REPS)
inactive = timeit.timeit("with region('x'): pass", globals={"region": region}, number=REPS)
with timing_session("bench"):
    active = timeit.timeit("with region('x'): pass", globals={"region": region}, number=REPS)
```

| | per region entry + exit |
| --- | --- |
| No session active (the always-installed cost) | ~324 ns |
| Session active (recording) | ~816 ns |

The benchmark workload performs **39,412 region entries in 20.0 seconds** — the
count is in the baseline record, being the sum of every node's `calls`. At 816 ns
each that is **33 ms, or 0.165% of the run**; with timing switched off the
always-installed wrapper costs about 12 ms, or 0.06%.

That ratio is not luck, it is the instrumentation rule from the plan: regions
wrap *calls*, never inner loops. The cheapest thing measured here — one legal-ply
generation — costs ~230,000 ns, some 280 times a region entry. Instrumenting
inside move generation's per-square loops would invert that ratio, which is
exactly why nothing does.

### The decision

**Timing is on by default** (`TIMING_ON_BY_DEFAULT = True` in
`capture_the_flag/timing_record.py`). At ~0.2% of a run, with an unmeasurably
small effect on wall clock, the case for making developers remember a flag does
not survive: a run that turns out to be interesting has already recorded why.
Both entry points still take `--no-timing`, which restores the pre-story cost to
within ~0.06%.

Re-run the recipe after any change that adds instrumented regions in the hot
path, or on a materially different machine. The figure to watch is region
entries per second of work: if a future change pushed that toward the millions,
this conclusion would need revisiting.

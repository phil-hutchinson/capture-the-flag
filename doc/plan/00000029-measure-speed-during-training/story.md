# Story: Where the time goes — cumulative timing for self-play and training

## Summary

Make the cost of a run visible. Today we know only the headline number — a
meaningful self-play game takes on the order of 15 minutes — and nothing about
*which* part of the pipeline that 15 minutes is spent in. This story adds
cumulative timing across the self-play and training pipeline: for each
instrumented section of code, the total time spent in it over the whole run, how
many times it ran, and what share of the run it accounts for. The deliverable is
a run that, when it finishes, leaves behind a machine-readable record holding
both the settings the run used and the timing breakdown it produced, plus a
readable summary at the end of the run.

This story **measures only**. No code is made faster in it, no hyperparameter is
retuned, no throughput target is claimed. Its output is the evidence that tells a
later story *what* to optimize — and the yardstick that lets that later story
prove it worked.

## Motivation

Throughput is the gate on the rest of the epic. The deferred phase-2
strength-measurement work is explicitly blocked on it: at ~15 minutes a game you
cannot train to a visible strength or play a tournament with enough games per
pairing for the result to be signal. Story 00000009 anticipated rules-engine
performance work as "its own conversation," and that conversation cannot start
usefully without an answer to a simple question: **when we spend fifteen
minutes, what are we spending it on?**

Three things make guessing a bad strategy here:

- **The expensive work is diffuse and repetitive.** Nothing in this pipeline is
  slow once. Legal-ply generation, ply application, and position evaluation each
  run on the order of hundreds of thousands of times per game, each too fast to
  notice individually. Only the *cumulative* figure — this section ran 480,000
  times and consumed 6 minutes — is actionable, which is why a stopwatch that
  accumulates is the right instrument rather than a one-off timing of a single
  call.
- **The plausible culprits are genuinely competing.** Search does the network
  forward pass, encodes positions, generates legal plies, and applies plies, all
  interleaved. Reasonable engineers would rank those differently, and the ranking
  probably shifts with the settings (search budget per ply, network width and
  depth, board occupancy as pieces come off). Measurement settles it; intuition
  does not.
- **Optimization needs a before.** Every later performance claim is a comparison.
  If the measurement apparatus arrives *with* the first optimization, there is no
  trustworthy baseline to compare against. It should arrive first, and be stable
  enough that a number taken today is comparable to one taken in six months.

## What we want

### A cumulative breakdown, per section of code

For every instrumented section: **total time spent in it across the run**, **how
many times it ran**, the mean per call, and its share of the run. Aggregated over
the whole run — not a trace of individual calls, and not a per-ply time series.

Sections are hierarchical (evaluating a position happens inside a search, which
happens inside a game, which happens inside a generation), so the report must be
readable as a nesting rather than a flat list of overlapping numbers, and must
not double-count time that a section spends inside its own children.

### Coverage: the places worth suspecting

The breakdown should be able to answer, for a given run:

- **Self-play versus learning.** How the generation splits between producing
  games and training on them (expected to be lopsided; worth confirming rather
  than assuming), plus what checkpoint writing costs.
- **Inside self-play** — the per-ply search as a whole, and within it the work
  this repository owns: evaluating a position with the network (separating the
  encoding of the position from the network's forward pass from the decoding of
  its output), generating legal plies, applying a ply, deciding whether a
  position is terminal, and capturing the training sample.
- **Inside training** — the network's forward pass and the loss computation.
  Batch assembly, the backward pass, and the optimizer step run inside the
  shared training loop, so the rule below applies to them as it does to search:
  they are reported as that region's unattributed remainder rather than reached
  into.

Granularity is a judgment call and belongs in the implementation plan, but the
governing rule is: instrument at the seams *between* meaningful units of work,
never inside the innermost loops. Timing a per-square loop would cost more than
the work it measures and would answer a question this story is not asking.

### An honest account of what we cannot see

The search itself — node selection, expansion, backpropagation — lives in
`game-engine-core`, consumed as a pinned third-party dependency. This story does
**not** change that dependency. So the pipeline can be timed at every seam this
repository owns, and the time inside search that none of those seams explains
must be reported as an explicit **unattributed remainder**, not silently folded
into a neighbouring number or quietly dropped.

If that remainder turns out to be small, we have our answer and the optimization
targets are all local. If it turns out to dominate, *that is the finding* — and
instrumenting or optimizing the shared engine becomes its own conversation, with
this story's numbers as the argument for having it. Either outcome is a
successful outcome for this story; what would not be acceptable is a report whose
percentages quietly fail to add up.

### One artifact per run: settings and cost together

A run should leave behind a single machine-readable record containing:

- **The settings that produced these numbers** — the run's training parameters,
  as already captured for reproducibility. A timing table without the settings
  beside it is uninterpretable a month later.
- **Enough environment to make runs comparable** — the commit, the library
  versions, and the machine-level facts that move timings around (compute device,
  thread counts, CPU). Comparing today's numbers with a later optimization's
  numbers is the whole point, and that comparison is worthless if the two ran
  under conditions we did not record.
- **The breakdown itself**, in the form described above.

Plus a human-readable summary printed when the run ends, so the common case
("run something, look at where the time went") needs no tooling.

### Usable outside training, at various settings

Training runs are the primary consumer, but the interesting question — *how does
the cost profile change as I turn the knobs?* — is often cheaper to ask by
playing a batch of games at a chosen search budget, network size, or engine
matchup than by launching a full training run. The same timing facility and the
same report should be available from game-playing entry points, not welded to the
training orchestrator.

### A repeatable measurement recipe

Because these numbers exist to be compared against future numbers, the story
should leave behind a documented way to take the measurement: a specific seeded
invocation, small enough to run often, that produces a comparable report. Under a
fixed seed the *call counts* should reproduce exactly (times will not — that is
noise, and the recipe should say roughly how much noise to expect).

### Permanent if it is free enough; otherwise switchable

The preference is for this to be always on, so that any run — including runs
nobody planned to profile — leaves a usable record. That is only acceptable if
the instrumentation's own cost is negligible, and "negligible" should be measured
rather than asserted: compare a seeded run with instrumentation active against
the same run without it.

The decision rule, rather than a guess made in advance:

- **Within budget** (proposed: a few percent of wall clock, to be confirmed when
  the implementation plan sizes it) — on by default, permanently.
- **Over budget** — kept in the codebase, tested, and enabled on demand via a
  single switch, defaulting off. Not deleted, not left as throwaway scaffolding:
  we will want to re-measure every time we optimize.

Either way, timing must never change behaviour — an instrumented run and an
uninstrumented run at the same seed must play the same games.

### Built to be shareable

Nothing about accumulating time by named section is specific to this game, and
the natural long-term home for it is the shared library — where it could
eventually time the search internals this story cannot reach. So the timing
mechanism should be kept clearly delineated from the game-specific code that
uses it, on the standard "build here, migrate later" path.

## Noted ideas (optional, not acceptance criteria)

- **Sampling or deterministic profilers as a complement.** A profiler run is the
  right tool for a one-off "which function inside this section is hot" dive, and
  costs nothing to keep as a documented option. It is not the deliverable here:
  profilers distort the timings they report and are impractical to leave running
  across a multi-hour training run, which is exactly the case this story needs to
  cover.
- **Timing by settings, tabulated.** Once the report exists, sweeping a knob
  (search iterations, network width) and tabulating how the profile shifts is
  a natural follow-on — useful, but analysis rather than apparatus.

## Out of scope

- **Any optimization.** No code is made faster, no algorithm changed, no
  hyperparameter retuned in this story. Findings are written down, not acted on.
- **Throughput targets.** Deciding what game wall-clock makes the tuned training
  run practical stays with the strength-measurement work.
- **Changes to `game-engine-core`**, including instrumenting the search
  internals. The unattributed remainder is reported, not chased.
- **Parallelism**, across games, seats, or anything else.
- **Memory, allocation, and GPU-kernel-level profiling.** Wall clock only.
- **Per-call traces, time series, and visualisation.** Cumulative totals in a
  file and on the console; charts are not part of this.

## Acceptance criteria

- A training run produces a cumulative breakdown covering the self-play half, the
  learning half, and the sections named above — with, for each section, total
  time, call count, mean, and share of the run.
- The breakdown reflects nesting and does not double-count; time inside search
  that this repository's seams do not explain appears as an explicit
  unattributed remainder, and the reported figures reconcile with total run wall
  clock.
- The run leaves a machine-readable record in the run's own directory holding the
  breakdown together with the run's parameters and the environment facts needed
  to compare it against a later run; a readable summary is also printed when the
  run finishes.
- The same breakdown can be produced for a batch of games outside a training run,
  at a chosen search budget and engine configuration.
- The instrumentation's own overhead is measured and reported (seeded run, with
  versus without), and the outcome drives the documented default: always on if
  within budget, otherwise off behind a single switch. The measurement and the
  resulting decision are written down.
- Instrumentation does not alter behaviour: at a fixed seed, an instrumented run
  and an uninstrumented run play identical games, and repeated seeded runs
  reproduce identical call counts.
- A documented measurement recipe exists — a specific seeded invocation whose
  report is intended to be compared against future runs — with a note on expected
  run-to-run variation.
- The timing mechanism carries no game-specific knowledge and is separated from
  its game-specific usage, so it can migrate to the shared library later.

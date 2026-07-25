# Implementation Plan: Where the time goes — cumulative timing for self-play and training

See [story.md](story.md) for full context. This plan builds a nested,
cumulative-by-region timer, instruments the seams this repository owns, and
surfaces the result as a per-run record holding the run's settings alongside its
timing breakdown.

## Approach

Three decisions shape every step below.

**Regions nest by call path, not by name.** A region is entered and exited around
a unit of work; whichever regions are already open when it is entered become its
ancestors. So the same instrumented function accumulates separately under each
distinct path that reaches it — legal-ply generation reached from inside search
is a different line in the report from legal-ply generation reached from the
game loop. The report is emitted as a **tree** (nested objects in the record
file, an indented tree on the console), not as flattened `A -> B` strings.

**The boundary into the shared engine is itself a region.** Calls *into*
`MCTSEngine` are wrapped and timed, and every callback the engine makes back into
our code (position evaluation, legal plies, ply application, outcome) is timed
too — and, by the call-path rule, lands *underneath* the engine region. The gap
between the engine region's own elapsed time and the sum of its children is
therefore the true unattributed cost of search internals, and cannot be polluted
by time spent in our code anywhere else in the process. That gap is the number
the story cares about most.

**Everything nests under one all-inclusive root.** Each run opens a single root
region covering the whole run, so no measured time is ever parentless and the
root's own unattributed remainder catches anything the instrumentation missed
entirely. Every node in the report carries: call count, inclusive time,
unattributed remainder (inclusive minus the sum of its children), and share of
both its parent and the root.

Two known facts about the code shape the expectations, and neither is acted on in
this story: `CtfPosition.outcome` internally consults `legal_plies` (so
legal-ply generation will appear nested under outcome as well as directly under
search), and both properties recompute on every access. The report is expected to
make that visible; making it cheaper is a later story.

## Step 1 — The timing core

Add a game-agnostic timing module: a session object holding the all-inclusive
root region and a stack of currently-open regions, a context-manager (and
decorator) entry point for opening a named region, and accumulation of call
count and elapsed time per node of the call-path tree. Time is taken from a
monotonic nanosecond counter and accumulated as integers, converted to seconds
only at report time. When no session is active, entering a region does nothing
measurable — this is the always-installed no-op path, not a separate code path
callers have to choose. The clock is injectable so tests are deterministic. The
session is documented as single-threaded (all instrumented work runs on one
thread); re-entering a region already on the stack simply deepens the tree rather
than being specially handled.

Nothing in this module may import from the game package — it is a shared-library
migration candidate (see CLAUDE.md's shared-asset convention), so it lives in its
own subpackage with its own mirrored test directory.

Depends on: nothing (first step). Every later step records into this.

Verification (automated): unit tests with an injected fake clock — sibling
regions accumulate independently; a nested region's time is included in its
parent's inclusive time and excluded from the parent's remainder; the same region
name entered under two different parents produces two distinct tree nodes; call
counts accumulate across repeated entries; with no active session, entering
regions records nothing and raises nothing.

## Step 2 — Report rendering

Turn a finished session into its two output forms: a nested, machine-readable
structure suitable for JSON serialisation, and a human-readable indented tree for
the console. Both carry, per node, the call count, inclusive seconds, the
unattributed remainder, and percentage of parent and of root; children are
ordered by inclusive time descending so the expensive path reads top-down. The
console form is the one a developer looks at after a run, so it must fit a
terminal and lead with the largest costs.

Depends on: Step 1 (the tree being rendered).

Verification (automated + manual): unit tests over a hand-built session assert
the emitted structure's shape, the computed remainders, and that percentages
reconcile against the root; then eyeball the rendered console tree from a test
fixture to confirm it is actually readable.

## Step 3 — Instrument the game mechanics

Wrap timing regions around the position-level operations that dominate search:
legal-ply generation, ply application, outcome determination (and its reason),
and starting-position generation in the self-play position factory. These are
call-level seams only — nothing inside the per-square loops of move generation
gets instrumented.

Depends on: Step 1. Comes before the engine and evaluator wiring because these
are the leaf regions that later steps' parent regions are meant to contain.

Verification (automated): with a session active, apply a known sequence of plies
to a constructed position and assert the expected region names appear with exactly
the expected call counts, including legal-ply generation appearing nested under
outcome determination (the duplicate-work path noted in the Approach section).

## Step 4 — Instrument the neural evaluation path

Add regions around the learned evaluator's work: a thin override of the shared
base class's `evaluate_position` that opens one region and delegates, with
distinct child regions for position encoding, the network's forward pass, and
policy decoding. The forward-pass region belongs to `CtfCrn`, so it is entered
during training's batched passes too — the call-path rule keeps single-position
search evaluations and batched training passes on separate branches of the tree
automatically.

Depends on: Step 1 (regions), Step 3 (policy decoding consults legal plies, whose
region should already exist so the nesting is visible in this step's
verification).

Verification (automated): evaluate a handful of positions under an active session
and assert encoding, forward pass, and decoding are recorded as children of the
evaluation region with the expected counts, and that the evaluation region
retains a non-zero unattributed remainder of its own.

## Step 5 — Time the boundary into the shared search engine

Introduce a timing wrapper that stands in front of a `GameEngine`, opening a
region around each call into it (ply selection, ply-with-policy selection,
observation, reset) and delegating unchanged. Wire it into the two places engines
are constructed — the self-play engine factory and the learned player's builder —
so both self-play and ordinary play measure the same boundary. Like Step 1's
module, this wrapper carries no game-specific knowledge and belongs with the
shareable code.

Depends on: Steps 3 and 4 (the callbacks that must appear underneath this region
already have to be instrumented for this step's verification to mean anything).

Verification (automated): play a few plies with a small-network learned engine
under an active session; assert the search region exists, that position
evaluation and legal-ply generation appear as its descendants rather than as
siblings, and that its unattributed remainder is positive and equals its
inclusive time minus its children — the search-internals figure the story asks
for.

## Step 6 — Timed game batches, and the run record

Wire timing into the headless batch runner: open the all-inclusive root region
around the batch, add regions for the outer per-game and per-batch structure, and
on completion print the console tree and write a record file into the batch's
output directory. The record holds three sections — the settings the batch ran
with, the environment facts needed to compare it against a future run (repository
commit, library and torch versions, compute device, thread counts, CPU
identification), and the timing tree. Timing is controlled by a single switch on
the command line, backed by one module-level default constant that Step 8 may
flip.

Depends on: Steps 2 (rendering) and 5 (the engine boundary). This is the first
end-to-end consumer, and deliberately the cheap one — a batch of games at chosen
settings is the fastest way to ask "where does the time go at this search
budget?", which is the story's "various settings" requirement.

Verification (manual): run a short random-vs-random batch and a short
neural-vs-neural batch with timing enabled; confirm the console tree appears,
that the neural batch shows search dominating with evaluation nested beneath it,
and that the written record contains the settings, environment, and tree with
percentages that reconcile to the root.

## Step 7 — Timed training runs

Wire the same apparatus into the training orchestrator: the all-inclusive root
around the whole run, a region per generation, and within a generation the split
between self-play collection, training, and checkpoint saving. Add regions for
the training-side work this repository owns — the policy-loss computation and the
capture-time policy transform — accepting that batch assembly, backward pass, and
optimizer step sit inside the shared training loop and will therefore land in
that region's unattributed remainder (the story's stance: report the gap, do not
chase it). The run's timing record is written into the run directory alongside
`run-config.json`, and because the run's parameters are already captured there,
the timing record carries them too rather than requiring the two files to be read
together. A resumed run writes its own record without overwriting the original's.

Depends on: Step 6 (record format, environment capture, and the enable switch are
reused, not re-invented).

Verification (manual): run one generation with a couple of games at a low search
budget and a small network; confirm the printed summary and the record file in
the run directory show the generation split, that self-play dwarfs training, and
that the file names the hyperparameters that produced it. Then resume for one
more generation and confirm a second record is written and the first is intact.

## Step 8 — Benchmark recipe, overhead measurement, and the default

Write down the measurement recipe — one specific seeded invocation, small enough
to run routinely, that produces a comparable report — and use it to measure the
instrumentation's own cost: the same seeded invocation with timing enabled and
disabled, several repetitions each, comparing total wall clock. Record the
numbers, the machine they were taken on, and the observed run-to-run variation in
the story folder, then set the default from the result: on by default if the
overhead is within the story's few-percent budget, otherwise off with the switch
documented. This is also where the "before" baseline for future optimization work
is captured.

Depends on: Steps 6 and 7 (both entry points must be instrumented for the
overhead figure to be representative).

Verification (manual): run the documented recipe with and without timing,
several times each, and confirm the overhead figure is stable enough to support
the default decision; the written record of the measurement is the step's
artifact.

## Step 9 — Behaviour-identity check

Confirm instrumentation changes nothing: at a fixed seed, a run with timing
enabled and one with it disabled produce identical game records, and two
identically seeded timed runs produce identical call counts (times will differ —
that is noise, not a failure). Add this as a marked slow test so the guarantee is
enforced rather than merely observed once.

Depends on: Steps 6 and 7 (needs both entry points, and Step 8's recipe supplies
the seeded invocation to use).

Verification (automated): the new slow test passes — the two seeded runs' records
match byte for byte and their region call counts are identical.

## Step 10 — README check

Review `README.md` against the change: timing switches on both runners, the new
record file in run and batch output directories, and the measurement recipe are
all developer-facing surfaces the README may need to mention. Run
`/update-readme` and apply what it warrants, or confirm no update is needed.

Depends on: all prior steps (the surfaces being documented must exist).

Verification (manual): read the resulting `README.md` diff (or the "no change
needed" conclusion) and confirm it matches what the branch actually added.

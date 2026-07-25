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

Introduce a timed `MCTSEngine` subclass that opens a region around each call
into the engine (ply selection, ply-with-policy selection, observation, reset)
and delegates unchanged. Wire it into the two places engines are constructed —
the self-play engine factory and the learned player's builder — so both self-play
and ordinary play measure the same boundary. Like Step 1's module, it carries no
game-specific knowledge and belongs with the shareable code.

A subclass rather than a wrapper standing in front of the `GameEngine` protocol:
the shared self-play collector asks for an `MCTSEngine` by name, so a wrapper
would not satisfy it. The coupling is the point at which this timing would move
upstream — if it ever does, it belongs in `MCTSEngine` itself and the subclass
disappears.

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

## Step 11 — The readable companion file (added after Step 10)

Write the console breakdown to disk as well, as a `timings.txt` beside each
`timings.json`. The JSON is what a later comparison is computed from; the text
is what a person reads, and the aligned tree already printed at the end of a run
turns out to be the form that reads best — so it should not be something a
developer has to scroll back through a terminal to recover.

The two files are companions with one stem, so a resumed training run's pair
stays as identifiable as its JSON already is. The text file carries whatever the
run reported about itself alongside the tree — a training run's per-generation
loss lines, a batch's outcome summary — so the file stands on its own without
the terminal it came from. Formatting is not duplicated: the text written and
the text printed come from one rendering, so they cannot drift.

Depends on: Steps 6 and 7 (both entry points write records; this adds a second
file to each). Sequenced after the README step because it was requested after
it — the README's description of the record needs a matching touch-up.

Verification (manual): run a short timed batch and a short timed training run,
and confirm each output directory holds a `timings.txt` whose contents match
what the run printed, with the training file also carrying its generation loss
lines; confirm a resume writes its own `.txt` alongside its own `.json` and
leaves both originals intact.

## Steps 12–14 — Closing the unattributed gaps (added after the first full-scale run)

The first run at realistic settings — 5 generations x 5 games, 700 search
iterations per ply, a 128-feature 12-block trunk, 2h57m, recorded in
`training-runs/20260724-191645/` — does its job: it says where the time goes, and
what it says loudest is that too much of the run has no name. Three unattributed
remainders together account for about a sixth of it:

| remainder inside | share of root | per call | whose code |
| --- | --- | --- | --- |
| `decode-policy` | 9.4% | 924us x 1,082,691 | ours |
| `evaluate-position` | 5.7% | 562us x 1,082,691 | shared base class, around calls into ours |
| `search-with-policy` | 1.1% | 72ms x 1,594, i.e. ~103us per search iteration | the pinned dependency's |

A remainder is a ceiling on optimization: nothing inside it can be targeted,
because nothing inside it is named. At a sixth of the run these three cap what
any later optimization can claim. These steps subdivide the first two — the 15%
that is reachable from this repository. They make nothing faster (the story's
stance holds), but they turn the next story's targets from suspicions into line
items.

**The search remainder is left as an aggregate, deliberately.** Everything of ours
that the engine calls back into is already attributed and already appears beneath
the search region, so those 114 seconds are `game-engine-core`'s own work: the
PUCT comparison over children, the expansion shuffle and node construction, the
policy-dict copy, the backprop walk. Subdividing it would need overrides of the
engine's private per-phase methods, and would produce a finding this repository
cannot act on — the argument for an upstream story, which the aggregate figure
already makes. The story's out-of-scope line ("the unattributed remainder is
reported, not chased") therefore stands as written. Two conditions would reopen it:
the share growing as the reachable 15% is optimized away, or a decision to work in
the dependency, at which point the timing belongs in `MCTSEngine` itself rather
than in a subclass reaching through it. A one-off profiler run on a single search
— already listed in the story's noted ideas — is the cheap way to answer "which
phase" if the question becomes pressing before then.

Two smaller remainders are also left alone: `outcome`'s 52.5s (0.5% of root,
being the termination checks around its legal-ply call) and `train`'s 31.2s, which
is the shared training loop's batch assembly, backward pass, and optimizer step —
upstream, and already the story's declared stance.

A throwaway probe at the run's architecture (one starting position, 44 legal
plies, no timing active) was used to choose where the new region boundaries fall.
Its figures are indicative, not findings — producing the real ones is the point
of the steps:

- Inside `decode-policy`: mask construction ~167us and probability extraction
  ~179us, both dominated by per-ply torch element access; ply-to-slot mapping
  ~30us; the softmax itself ~8us.
- Inside `evaluate-position`: `model.eval()` ~335us, and every other line of the
  base class's body at ~2us or less. Torch implements the mode switch as a
  recursive walk over every submodule, and the shared evaluator performs it on
  each of the million single-position evaluations.

### Step 12 — Subdivide policy decoding

Add a region per phase of the learned evaluator's `decode_policy`: mapping the
position's legal plies to their action-space slots, building the masked-logit
tensor, the softmax over it, and extracting the per-ply probabilities into the
returned dict. Names join the vocabulary in `timing_regions.py` with the rest.

One region per phase per call — the loops over legal plies *within* each phase
stay uninstrumented. That is the Step 1 rule still applying rather than being
waived: a whole phase at ~170us is 200 region entries' worth of work, while a
region per ply would be entered some 50 million times in a run to time
operations only a few times its own cost.

Depends on: Step 4 (the `decode-policy` region these subdivide, and its existing
`legal-plies` child, which stays a sibling of the new phases).

Verification (automated): extend `tests/instrumentation/test_evaluator_regions.py`
— decode a policy for a constructed position under an active session, assert each
new phase region appears as a child of `decode-policy` with one call per decode
alongside the existing legal-ply child, and assert what is left unattributed is a
small fraction of `decode-policy`'s inclusive time rather than the majority of it.

### Step 13 — Attribute the evaluation gap to the mode switch

The `evaluate-position` remainder sits in the shared base class's body, which this
repository does not own — but the expensive line in that body is a call into a
network it does. Add a region around `CtfCrn`'s train/eval mode switch. Because
the switch is entered from inside the base body, the call-path rule files it under
`evaluate-position` without changing the delegation, and the same region will
separately record the training loop's own mode switches on the training branch of
the tree — which is worth seeing too.

What survives is the base body's tensor plumbing: the batch wrap, the no-grad
context, the value unwrap. The probe puts that at a few microseconds a call, and
the step stops there deliberately — naming those pieces would mean copying the
upstream body into this repository to earn a fraction of a percent, and a
remainder that small is an honest residue rather than a blind spot.

Depends on: Step 4 (the `evaluate-position` and `network-forward` regions this
step's new region sits between).

Verification (automated + manual): a unit test asserts the mode-switch region is
recorded under `evaluate-position` once per evaluation, and that a run of
evaluations leaves `evaluate-position` with a remainder that is a minority of its
inclusive time. Then, because a small test network makes the walk cheap and the
effect is a large-network one, run a short timed batch at the full-scale
architecture and confirm in `timings.txt` that the region carries what used to be
the gap.

### Step 14 — Re-measure what the instrumentation costs

The two steps above put new regions in the hottest path there is: five more
entries per position evaluation, on top of the 11.0 million the 2026-07-24 run
already performed — call it 16 million, half again as many. At the ~816ns per
entry measured in Step 8 the arithmetic says a tenth of a percent, but "region
entries per second of work" is the figure `measurement-recipe.md` names as the one
to watch, and it has now moved. Re-run the recipe's timed-versus-untimed
comparison, recompute the entry count, and confirm or revise the on-by-default
decision — then record the new figures in `measurement-recipe.md` beside the
existing ones, so the two are readable as a before and after rather than one
overwriting the other.

The old baseline record needs no replacing: these steps only add children to
existing regions, so every node in it keeps its identity and remains comparable to
whatever a later full-scale run produces. Taking such a run is worth doing — it is
what makes the new sub-regions' real shares known — but it is hours of wall clock
and no code depends on it, so it stays outside the plan.

No developer-facing surface changes here — no new flags, no new files — so Step
10's README review still stands.

Depends on: Steps 12 and 13 (one overhead measurement covers both).

Verification (manual): run the recipe with and without timing several times and
confirm the overhead still sits under the story's budget at the higher entry count,
with the recorded numbers as the step's artifact.

## Step 15 — Write up what the numbers say

The story's deliverable is the apparatus, but its *purpose* is the evidence — "the
output is the evidence that tells a later story what to optimize." That evidence
is a document, not a JSON file: a reader six months from now needs to know which
figures are findings, which are this machine's, and which are guesses recorded as
guesses. Take a full-scale run at the architecture and search budget the baseline
used, and write up what it shows in `findings.md` beside the story — each item
naming what was measured, what it means, and what it does *not* establish.

Nothing here is acted on: the story's "findings are written down, not acted on"
holds, and any fix suggested by an item is described rather than made.

Depends on: Steps 12–14 (the run to write up should be one whose remainders have
already been closed, or the findings are mostly "we do not know").

Verification (manual): the document exists, every figure in it is traceable to a
region in the run's record, and the run it came from is named.

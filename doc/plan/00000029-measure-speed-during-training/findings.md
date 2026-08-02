# Findings: where a training run's time actually goes

Companion to [story.md](story.md). The story's deliverable is the apparatus, not
the optimization — "findings are written down, not acted on" — so this is the
writing down. Nothing here has been acted on; each item names what was measured,
what it means, and what it does *not* establish.

## The run these come from

A full-scale training run at the architecture and search budget the 2026-07-24
baseline used (`training-runs/20260724-191645/` is that predecessor), re-taken
after the gap-closing regions of plan Steps 12–13 were added:

> **Later note (story 00000037, 2026-08-02).** The run directories named here no
> longer exist. `training-runs/` is gitignored, so they were only ever present on
> the machine that produced them; story 37 deleted them because their checkpoints
> became unloadable — trained under the eight-movement action space `ENG_NN_3`
> superseded, and under rules no longer Active. The figures below were taken from
> those runs and are unaffected; only the raw `timings.json` behind them is gone.

| | |
| --- | --- |
| total | 11,138.6s (3h 05m) |
| structure | 5 generations x 5 games, 1,355 plies, 700 search iterations per ply |
| position evaluations | 915,209 |
| machine | 11th Gen Intel Core i7-11800H, 8 torch threads, WSL2, CPU only |

**The report now names 96.9% of the run.** Total unattributed time fell from
17.0% to 3.1% between the two runs, and 1.1 of the 3.1 points that remain are the
shared engine's search internals, which this repository deliberately does not
instrument. That is what makes the rest of this document possible: before, a sixth
of the run was a ceiling on any claim anyone could make about it.

## 1. Half a percent of the mode switches do anything — 527s, 4.7%

`network-mode-switch` records **915,209 calls, 526.9s**, one per position
evaluation. The genuine transitions in the whole run number **five** — visible as
the five calls on the `train` branch, one per generation.

The mechanism, confirmed rather than inferred:

- The shared `NeuralNetworkEvaluator.evaluate_position` calls `self._model.eval()`
  unconditionally on every evaluation. Upstream documents why: `TrainingLoop`
  switches the shared model to train mode and never restores it, so the evaluator
  re-asserts eval mode rather than trusting the caller.
- `Module.train()` has no early-out. Its body sets `self.training` and recurses
  into every child, whatever the current state.
- A 128-feature, 12-block trunk has **93 submodules**, so one switch is 93 writes:
  ~372us idle, ~576us in-run.
- The cost is the write, not the recursion. Setting `.training` on all 93 through
  `nn.Module.__setattr__` costs ~227us; writing the same values straight into
  `__dict__` costs ~11us. Torch's `__setattr__` checks `_parameters`, `_buffers`,
  and `_modules` and runs isinstance tests before falling through.

**This is useless work, not amortized setup.** Nothing is deferred to it: zero of
the 93 submodules change state on a repeat `eval()`, no cache is populated, and
the only observable — the `training` flag — already holds the value being written.
Of the nine module kinds in the trunk, none overrides `train()` except `CtfCrn`
itself (for timing); `BatchNorm2d` *reads* `self.training` at forward time, so the
flag matters while re-writing it does not. For contrast, the same report does
contain real amortization: `build-optimizer`, 1.196s across 5 calls, the first
paying torch's lazy initialization.

The guard is necessary; the walk is not. Five state changes per run are defended
against by 915,204 re-assertions.

Two shapes a fix could take, neither taken here: an early-out in `CtfCrn.train`
when `self.training` already equals `mode`, or — cleaner, and upstream —
the shared evaluator asserting eval mode once instead of per call. The early-out
is sound *because* the walk is recursive: the root's flag implies its children's,
the only two mode-switch call sites in the system are both on the root
(`TrainingLoop.train` and `evaluate_position`), and nothing anywhere sets a
submodule's mode directly.

Caveat on the size: the per-call mean moved 335us idle to 576us on a loaded
machine, so 4.7% is this machine's figure, not a constant.

## 2. Policy decoding walks the legal plies an element at a time — 881s, 7.9%

`decode-policy` costs 1,434.9s (12.9%), and two of its five phases are 61.5% of
that:

| phase | total | mean | of decode |
| --- | --- | --- | --- |
| `build-policy-mask` | 444.4s | 485.6us | 31.0% |
| `read-ply-probabilities` | 437.0s | 477.5us | 30.5% |
| `legal-plies` | 364.3s | 398.1us | 25.4% |
| `map-ply-slots` | 113.7s | 124.3us | 7.9% |
| `policy-softmax` | 49.2s | 53.8us | 3.4% |

The two expensive phases are the two that touch the tensor once per legal ply — a
Python loop writing `0.0` into masked slots, and a dict comprehension calling
`.item()` per ply. The one phase that hands a whole tensor to torch in a single
call, the softmax, is 3.4%. Roughly 40–50 legal plies per position and ~4us per
element access is the whole story.

What this does not establish: that a vectorized formulation is available at the
same numerical result. That is the optimization story's problem, not a measured
fact.

## 3. Legal plies are generated 2.84 million times — 1,057s, 9.5%

Aggregated across every path that reaches it:

| reached from | calls | total |
| --- | --- | --- |
| `outcome` (inside search) | 1,847,761 | 666.9s |
| `decode-policy` | 915,209 | 364.3s |
| search directly (expansion) | 73,860 | 25.0s |
| the game loop's own outcome check | 1,355 | 0.5s |

`outcome` costs 723.3s, of which 92.2% *is* legal-ply generation — the duplicate
work the implementation plan predicted in its Approach section, now sized. Both
`legal_plies` and `outcome` are properties on a frozen dataclass that recompute on
every access, and MCTS reuses a node's position object across iterations, so the
same position is re-analyzed many times over.

What this does not establish: how many *distinct* positions those 2.84 million
calls cover. That ratio decides what memoization would actually buy, and it was
not measured.

## 4. The forward pass is 65% — and it is the ceiling on everything else

`network-forward` is **7,269.2s, 65.3%** of the run, at 7.9ms per single-position
evaluation. Encoding adds 871.7s (7.8%) at 951us per call.

The arithmetic worth stating plainly, since it governs how ambitious a first
optimization round can be: if every non-forward second in the run were driven to
zero — every finding above, plus search internals, plus training — the run would
be **1.53x faster**. The four local targets named in this document sum to 26.4% of
the run, so eliminating all of them entirely, which no change will, is 1.36x.

An order of magnitude is not reachable by making the work around the forward pass
cheaper. It needs fewer evaluations (search budget), a cheaper network, or
evaluations that share a forward pass — batched or parallel search, which is an
architecture change in the shared engine rather than a local fix. Nothing about
that is a recommendation here; it is the shape the numbers impose on any plan.

## 5. The shared engine's own search internals — 121s, 1.1%

`search-with-policy`'s remainder is the pinned dependency's own work: PUCT
comparison over children, expansion and node construction, the policy-dict copy,
the backpropagation walk. It stays an aggregate by decision (see the plan's
Steps 12–14 preamble), and at 1.1% it is not currently worth reopening — though
it is 1.1% of a run whose other 96% is the thing being optimized, so its *share*
will grow as the rest shrinks. A one-off profiler run on a single search is the
cheap way to break it down if that day comes.

## 6. Open question: `evaluate-position` keeps 104.5s unexplained — 0.9%

Its residue is 114us per call, and the pieces it was expected to contain do not
account for it. Measured idle: no-grad enter and exit 2.1us, `unsqueeze` 1.3us,
value unwrap 1.5us, `nn.Module.__call__` dispatch 1.55us — about 6us, against a
load inflation factor of only ~1.55x observed elsewhere.

So roughly 100us per call is genuinely unaccounted for. The plausible candidates —
allocator activity and garbage collection charged to whichever region happens to
be open — are guesses, and are recorded here as guesses. At 0.9% of the run it was
not worth the instrumentation to settle; it is written down so that a future
reader does not mistake the residue for something already understood.

## What the split confirms

Self-play is **99.5%** of the run and training **0.5%** — lopsided, as the story
expected, and worth having confirmed rather than assumed. Checkpoint writing is
0.5s per generation. Optimization effort belongs in the self-play half, and within
it, in the evaluation path: `evaluate-position` and its children are 91.5% of the
whole run.

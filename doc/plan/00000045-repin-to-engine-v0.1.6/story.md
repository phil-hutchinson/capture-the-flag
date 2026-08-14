# Story 45: Repin to `game-engine-core` v0.1.6

## Summary

Move the pinned `game-engine-core` dependency from `v0.1.4` to `v0.1.6` and bring
this repository's code back to green against it.

The pin itself is one line. The work is everything v0.1.5 broke, because that
release is skipped rather than adopted separately: **the library's per-position
interfaces became per-batch interfaces.** An evaluator is now handed a sequence
of positions and returns a sequence of evaluations; a search returns a ply for
each of a fleet of positions; a capture-time policy transform re-keys a sequence
of distributions. Every one of those seams is implemented in this repository, so
every one of them changes shape here.

Three things this story deliberately does *not* do: exploit the new batching
(the seams are adopted at width 1 and nothing is vectorized), make the pipeline
device-aware, and preserve comparability with the pre-repin timing baseline.

## Why now

`v0.1.6` is the release that makes the learning package device-agnostic — the
training loop places each minibatch on the model's device, and the evaluator
reads its values back in one transfer instead of one synchronisation per
position. That is precisely the blocker `CONTRIBUTING.md` names when it explains
why the CUDA container makes a GPU reachable but nothing faster, and precisely
what `device.py` means when it says a `--device` flag "arrives with the story
that makes the pipeline device-aware." **That story is not this one**, but it
cannot start until this one lands.

## What v0.1.5 and v0.1.6 change under us

| Upstream change | What breaks here |
|---|---|
| `PositionEvaluator.evaluate_position` → `evaluate_positions(Sequence) -> Sequence` | `CtfNNEvaluator` and every test that calls it directly |
| `NeuralNetworkEvaluator.encode_position` → `encode_positions` (returns a stacked `(N, *sample_shape)`) | `CtfNNEvaluator.encode_position`, the bulk of `test_ctf_nn_evaluator.py` |
| `NeuralNetworkEvaluator.decode_policy` → `decode_policies(logits, positions) -> Sequence` | `CtfNNEvaluator.decode_policy` and its four timed phases |
| `PositionEvaluation.policy` is required, no longer `\| None` | Nothing — this evaluator always supplies one |
| Model value output must be exactly `(N, 1)`, enforced | Nothing — `CtfCrn` already emits that shape; the check is new, not the contract |
| `MCTSEngine.select_ply_with_policy` → `select_plies_for_training(positions)` | `TimedMCTSEngine`, and `test_search_regions.py` |
| `PolicyTransform` is `(Sequence[position], Sequence[policy]) -> Sequence[policy]` | `transform_policy_to_white_perspective` |
| `PolicyLossFn` gains a device contract: build the dense target on `policy_logits.device` | `ctf_policy_loss` builds it on the ambient default |
| `SelfPlayCollector.collect(n)` plays all `n` games as one fleet, one engine per collect | Nothing structurally; the *meaning* of `--games` changes (below) |
| Step records are detached at capture | Nothing — no caller here relied on a grad-tracking encoding |
| New optional `batch_ops` / `record_device` parameters | Nothing; deliberately not passed (see Out of scope) |

**The one that fails silently.** `TimedMCTSEngine.select_ply_with_policy`
overrides a method the base class no longer has. Python accepts it, pyright
accepts it, and the suite can pass — the region simply stops being recorded and
self-play timing loses its headline line. Nothing about the repin surfaces this;
it has to be looked for, which is why it gets a step of its own.

## Decisions this story makes

### The new instrumentation baseline is batch-of-one

Every timed region in this repository was written when a call was a position.
After the repin a call is a wave, and a wave is as wide as the fleet. Rather
than invent per-position accounting for a wave, **the baseline is re-taken at
fleet width 1**, where a call is a position again and every region means what it
has always meant. The measurement recipe already produces this: it plays real
games through `run_batch`, and play-time search under v0.1.6 wraps its retained
root into a one-slot fleet, so the recipe is batch-of-one without changing it.

Two consequences, stated so they are not later mistaken for findings:

- **The pre-repin numbers are not a "before."** The hardware is different, and
  so is the search — full expansion replaces partial expansion, so even the call
  counts, the one thing the recipe promises is reproducible, legitimately move.
  This is a new baseline, not a regression comparison.
- **A timing record taken from a *training* run is no longer batch-of-one**,
  because self-play collects `games_per_generation` games as one fleet. The
  recipe's record is the baseline; a training run's record is a measurement of a
  particular fleet width and must say so.
- **A region's call count is waves, not positions** — above width 1, and only
  for the regions that sit at the wave boundary. `evaluate-position`,
  `encode-position` and `decode-policy` are entered once per wave; the four
  decoding phases underneath are still entered once per position, so a report at
  width 5 shows `decode-policy` with one call and `map-ply-slots` with five
  beneath it. Story 29's instruction to compare call counts rather than seconds
  survives, but only between records taken at the same width — which is the
  second reason the baseline is taken at 1.

What the fleet actually buys, measured at widths above 1, belongs to the story
that adopts the seams.

### The region vocabulary does not move

`evaluate-position`, `encode-position` and `decode-policy` keep their names, and
so do the four decoding phases. `timing_regions.py` already sets the rule —
names describe *work*, not the function that happens to do it — and the work is
unchanged: a wave of five encodings is five encodings, however many calls it
took. Batching is an implementation detail of the caller, and a region name that
tracked it would have to change again the next time the caller does.

`search-with-policy` is the one exception, and not on plurality grounds: it is
named for a method that no longer exists. It becomes `search-for-training`,
after the work it now names.

### `--games` is now two knobs wearing one hat

`games_per_generation` has always set how many self-play games a generation
collects. It now *also* sets how many positions the engine searches per wave,
and how many step records are held in memory at once. The default of 5 stays —
this story changes no configuration — but the parameter's documentation must say
both things, because tuning it for sample count now silently tunes batch width.

### The policy loss honours the device contract

`ctf_policy_loss` builds its dense target with `torch.zeros(...)` and no device,
which upstream now explicitly names as the way a model on an accelerator meets a
host-side target. Everything here is CPU today so the bug is unreachable, but
the contract is one line to satisfy and leaving it unmet would seed the
device-awareness story with a failure it did not cause.

## Out of scope

- **Adopting `BatchPositionProcessor`.** Overriding `legal_plies`, `apply_plies`
  or `outcomes` to do real vectorized work is the point of the fleet and is a
  story of its own. Here the default scalar loop is inherited, which is exactly
  what the code does today.
- **`record_device`, and device-awareness generally.** No `--device` flag, no
  tensor placed anywhere new, no change to `device.py`. `CONTRIBUTING.md`'s
  claim about what the CUDA container does *not* do gets corrected only as far
  as naming the library-side blocker as lifted.
- **Optimizing anything the new baseline reveals.** Findings are recorded, not
  acted on — the same rule story 29 set for itself.
- **Tuning `games_per_generation`** in response to it now setting batch width.
- **Retraining, or any checkpoint compatibility question.** No tensor contract,
  action space, or ruleset moves in this story.

## Acceptance criteria

- The pin in `pyproject.toml` is `v0.1.6`, and the installed package matches
  (`direct_url.json`).
- `pytest`, `pytest -m slow`, `ruff check .` and `pyright` are all clean.
- No method in this repository overrides a base-class method that no longer
  exists — specifically, the self-play search region is recorded again and a
  test fails if it stops being.
- A new baseline `timings.json` is recorded by the standard recipe, on the
  current machine, with its environment and its batch-of-one framing written
  down.
- `CONTRIBUTING.md` no longer says device support waits on `game-engine-core`,
  and `README.md` is confirmed accurate or updated.

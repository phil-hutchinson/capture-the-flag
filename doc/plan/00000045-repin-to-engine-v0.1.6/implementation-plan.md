# Implementation Plan — Story 45: Repin to `game-engine-core` v0.1.6

The pin comes first and lands the repository red; every step after it closes one
seam, in the order the call graph needs them. The evaluator is bottom of the
stack — search and self-play both call into it — so it goes first; the policy
transform is next, because it is the last thing standing between the repin and a
self-play collect that runs end to end; the timed engine and the policy loss are
independent of both and follow; the baseline is taken only once the suite is
green, since a measurement of broken code measures nothing.

A red suite between Steps 1 and 6 is expected and is not a forward dependency:
each step's verification is scoped to the seam that step closes, and Step 6 is
where the whole suite is the claim.

## Step 1 — Bump the pin and rebuild the container

Change the single pinned `game-engine-core` ref in `pyproject.toml` from `v0.1.4`
to `v0.1.6`, and rebuild the dev container so the new version is installed rather
than merely requested (`CONTRIBUTING.md`). Keep this as a commit of its own, with
the reason for the bump in the message. No source changes in this step.

Depends on: nothing.

Verification (manual): In the rebuilt container, confirm the installed package is
the requested ref — read `direct_url.json` in the installed distribution's
`.dist-info` and check it names `v0.1.6` — and confirm the new module is
importable (`game_engine_core.game.batch_position_processor`). Then run `pyright`
and confirm the errors it reports are confined to the files
[`story.md`](story.md) tables as breaking: the evaluator, the policy transform,
and the policy loss. An error anywhere else means the change surface is wider
than the story scoped and the story needs revisiting before proceeding.

## Step 2 — The evaluator goes plural

Convert `CtfNNEvaluator` to the batch-shaped base class: encode a sequence of
positions into one stacked tensor, decode a batch of logits into one policy per
position, and time the whole call. The per-position work is unchanged — this is
the same encoding and the same decoding, driven by a loop and stacked, not
vectorized. Rename the three region constants in `timing_regions.py` to their
plural forms and keep the four decoding phases as they are. Update
`test_ctf_nn_evaluator.py`, `test_ctf_checkpoint.py` and
`test_evaluator_regions.py` to the new shapes.

The board-mismatch guard and the missing-flag guard both stay; decide explicitly
whether they fire per position or on the batch, and make the tests say which.

Depends on: Step 1.

Verification (automated): `pytest tests/engines/neural_network/test_ctf_nn_evaluator.py
tests/engines/neural_network/test_ctf_checkpoint.py tests/instrumentation/test_evaluator_regions.py`
is clean. The evaluator tests must cover a batch of more than one position —
index alignment between positions in and evaluations out is the whole content of
the new contract, and a suite that only ever passes one position would pass
against an implementation that ignored the rest.

## Step 3 — The policy transform goes plural

Convert `transform_policy_to_white_perspective` to take a sequence of positions
and a sequence of distributions and return one distribution per position, aligned
by index. The per-position rotation is unchanged. Its timing region now records
once per wave rather than once per captured step; leave the name and note the
change where the region is documented.

Depends on: Step 2 (a self-play collect reaches the transform only if the
evaluator it also calls has already been converted).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_policy_target.py
tests/engines/neural_network/test_ctf_self_play.py` is clean, including the
existing check that Black-to-move targets come back in White's frame — extended
to a mixed batch, since a transform that rotated every entry by the first
position's side would pass a single-side batch. This is the first step at which
`collector.collect(n)` runs end to end; confirm it returns samples for a fleet of
more than one game.

## Step 4 — The timed engine follows the search interface

Replace `TimedMCTSEngine`'s `select_ply_with_policy` override with one over
`select_plies_for_training`, and rename its region to `search-for-training`.
Add a guard that fails if the class ever again overrides a method the base class
does not define — the failure mode here is a silent loss of instrumentation, not
a crash, so it needs a test rather than a careful reading.

Depends on: Step 1. Independent of Steps 2–3, but its verification runs a real
search, so it is cheaper to check once those are green.

Verification (automated): `pytest tests/instrumentation/test_search_regions.py` is
clean, with the self-play search region present in the recorded tree. Then
confirm the guard bites: temporarily rename the override to a name the base class
does not have, see the guard fail, and revert.

## Step 5 — The policy loss builds its target on the logits' device

Build the dense target tensor in `ctf_policy_loss` on `policy_logits.device`
rather than on the ambient default, as `PolicyLossFn` now requires. Behaviour on
CPU is unchanged; this satisfies a contract, it does not make anything
device-aware.

Depends on: Step 1.

Verification (automated): a test in `test_ctf_policy_target.py` that asserts the
loss's target is built on the same device as the logits it is given. Where a GPU
is available (`tests/gpu.py` already gates on this), exercise it on CUDA logits;
where one is not, the assertion still holds on CPU and the CUDA case skips.

## Step 6 — The whole suite, including the slow arm

Run everything and close whatever the seam-by-seam steps left. Update the
documentation of `games_per_generation` / `--games` to say that it now sets fleet
width — the number of positions searched per wave and the number of step records
held at once — as well as the number of games collected. The default does not
move.

Depends on: Steps 2–5.

Verification (automated): `pytest`, then `pytest -m slow`, then `ruff check .`
and `pyright`, all clean. The slow arm is not optional here: self-play and
training are where the fleet actually runs, and the default suite excludes them.

## Step 7 — Take the new baseline

Run the measurement recipe unchanged
(`python -m capture_the_flag.timing_benchmark --record-dir …`, defaults intact)
and record the result as this story's baseline. Write it up alongside this plan:
the machine, torch build and thread counts, the wall-clock arms, and the region
breakdown — plus the two framings [`story.md`](story.md) fixes, that this is
batch-of-one and that it is a new baseline rather than a comparison against the
pre-repin numbers. Add a pointer from story 29's `measurement-recipe.md`, which
already carries later notes, so the recipe's readers find the current baseline.

Depends on: Step 6 (a measurement of a red tree is meaningless).

Verification (manual): The recipe completes and writes a `timings.json`. Read it
and confirm the region names are the plural ones from Step 2, that
`search-for-training` is absent (this workload plays games, it does not train),
and that the recorded environment names this machine and the `v0.1.6` commit.
Confirm the report's unattributed remainder is still a small fraction of the run
— a large one would mean the new search moved work into a region nothing here
names, which is a finding to write down rather than to fix.

## Step 8 — Documentation, and the README check

Correct `CONTRIBUTING.md`'s CUDA section: the paragraph explaining that the
pipeline cannot use a GPU because `game-engine-core`'s training loop and
evaluator take no device is no longer true of the library — the remaining
blocker is this repository. Keep the section's practical advice (opening the CUDA
container will still not make training faster) and change only the reason given.
Then run `/update-readme` to review the branch diff against `README.md` and
update it if the story touched anything it describes, or record that it did not.

Depends on: Steps 1–7.

Verification (manual): Read the changed `CONTRIBUTING.md` paragraph and confirm
it names this repository, not the library, as what stands between the CUDA
container and a faster run. Confirm `README.md` either changed or was explicitly
confirmed accurate.

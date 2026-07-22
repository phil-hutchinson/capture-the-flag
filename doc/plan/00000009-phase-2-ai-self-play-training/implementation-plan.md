# Implementation Plan: Phase 2 AI self-play training (Story 00000009)

> The developer is implementing this story (in whole or in part) for learning
> purposes. Steps stay high-level — intent and verification, no code — and the
> hyperparameter / training-shape decisions are intentionally **left open**:
> finding them is the story's own acceptance criterion ("a workable training
> recipe … finding these is part of the story"). Each open decision lists the
> constraints a good answer must satisfy, not the answer.

## Context and constraints

The deliverable is a **training run** that turns the untrained play engine from
story 00000008 into one of clearly increasing strength, with saved checkpoints,
a way to measure that strength as a number, and a recorded recipe. Everything
below builds on two established surfaces:

**What story 00000008 already provides (do not rebuild):**

- `CtfNNEvaluator` (`engines/neural_network/ctf_nn_evaluator.py`) — position
  encoding and `decode_policy`, both in the side-to-move frame, with
  `policy_logit_location_for_ply` as the single source of truth for the
  `ply → (movement index, row, column)` action-space mapping.
- `CtfCrn` — the value/policy network.
- `build_neural_player` / `NeuralCtfPlayer` — an untrained neural seat, and the
  construction seam where `torch` enters.
- `make_player(kind, …)` — the runner-facing player factory (kinds `human`,
  `random`, `neural`).
- `match.build_initial_position` — already written to the shared `Tournament`'s
  `position_factory(side_one, side_other)` contract.

**What the shared library provides (reuse, do not reimplement):**

- `game_engine_learning.self_play_collector.SelfPlayCollector` — plays self-play
  games and emits `TrainingSample`s. It already propagates the terminal outcome
  backwards with the correct alternating sign, so the value targets are correct
  as long as encoding is side-to-move relative (it is).
- `game_engine_learning.training_loop.TrainingLoop` — joint value/policy gradient
  descent. It takes a **caller-supplied `policy_loss_fn`**: aligning each
  `str(ply)` target with its logit column is the one piece of game-specific
  knowledge the loop cannot supply. `value_loss_fn` defaults to MSE (correct for
  a tanh value head).
- `game_engine_learning.checkpoints` — run-directory and checkpoint-path naming
  (`new_run_directory`, `checkpoint_path`, `discover_checkpoints`,
  `latest_run_directory`). Deliberately torch-free: it deals in paths and
  iteration numbers only, so **saving/loading the actual weights is our code.**
- `game_engine_core.evaluators.null_evaluator.NullEvaluator` — returns
  `value=0.0` with a default (uniform) policy. Wrapped in an `MCTSEngine` this is
  exactly the story's **flat-value reference engine**: pure search, no learned
  judgement.
- `game_engine_core.tournament.Tournament` — round-robin over anything
  implementing `Player`, with alternating first move and standings/cross-table
  reporting. Its `position_factory` is `match.build_initial_position`.

**Fixed points, load-bearing for the plan:**

- **The sharpest correctness constraint.** The frame math that turns a
  global-frame `str(ply)` target into a side-to-move logit column must use the
  *same* `policy_logit_location_for_ply` rotation `decode_policy` uses. A mismatch
  does not crash — it trains the policy head against transposed targets and
  silently prevents learning. This is the analogue of story 8's "policy must
  cover every legal ply."
- **Where that frame math lives — the upstream hook.** Because the action space
  is side-to-move relative, the target policy cannot be aligned to the logits
  from `str(ply)` alone; it needs the position's `active_player_id`, which the
  `PolicyLossFn(logits, policies)` seam never receives (a shuffled batch mixes
  both movers, and the encoding is colour-blind, so it cannot be closed over or
  recovered). The fix is a **capture-time `policy_transform(position, policy)`
  hook on `SelfPlayCollector`** — added to `game-engine-core` and adopted via a
  pin bump — that re-keys the visit distribution into the network frame *while
  the collector still holds the position*. Once stored targets are already
  in-frame, the loss is genuinely player-independent and the existing
  `PolicyLossFn` signature is honoured as written. Background and the general
  principle: `.local/game-engine-core-policy-loss-perspective-gap.md`. This
  reshapes Steps 1 and 3 (below).
- **Random placements are deliberate.** Every self-play game and every training
  position starts from a fresh random placement per side — the engine must learn
  to play *any* dealt position; placement learning is stories 00000010+.
- **Self-play needs exploration; play-time is greedy.** The shipped play default
  is `temperature = 0.0` (greedy). Self-play at 0.0 would make games nearly
  deterministic and starve the policy target of signal. The `MCTSEngine`'s only
  exploration lever is `temperature` (there is no root-noise knob), so the
  self-play `engine_factory` must set a non-zero temperature — how much, and
  whether it decays across a game, is an open decision.
- **Runner convention.** Runners are `python -m capture_the_flag.<name>` modules
  with an argparse `main(argv)` (see `batch_runner`, `game_runner`). New training
  and tournament entry points follow the same shape; there is no
  `[project.scripts]` block to update.
- **The value collector does no discounting.** `SelfPlayCollector` assigns
  `±final_outcome` to every ply of the game with no decay. Overriding that would
  mean not using the shared collector; the default is almost certainly the right
  starting point and any change is an open decision, not a step.

## Decisions deliberately left open (the learning content)

The plan requires *that* these exist, not *what* they are:

- **Training-loop shape.** Fresh samples every generation vs. a replay buffer
  mixing recent generations; games per generation; epochs per generation; batch
  size; optimizer and learning rate. Constraints: the run completes unattended in
  acceptable wall-clock on one workstation, and strength visibly increases across
  checkpoints.
- **Self-play exploration.** The self-play temperature (and any within-game
  schedule) — distinct from the greedy play-time default. Constraint: enough
  exploration that self-play games diverge, without so much noise that the visit
  distribution stops being a useful policy target.
- **Search budget, training vs. measurement.** Iterations per ply during
  self-play (cheap enough for volume) and iterations per ply in the strength
  tournament (must be *equal across all entrants* for a fair comparison). These
  two budgets need not match.
- **Checkpoint cadence and tournament selection.** How often to checkpoint, and
  which checkpoints enter the strength tournament (all of them, or a sampled
  ladder from early to final).
- **The run-config record.** What a reproducibility record must capture (seed,
  every hyperparameter above, the `game-engine-core` pin / git commit, dates,
  and the resulting per-checkpoint strength numbers), and where it lives in the
  story folder.

---

### Step 1 — Game-specific policy-target handling: transform + loss

Implement the two halves of one contract, so the step is a working slice rather
than a half-testable fragment:

1. **`policy_transform(position, policy)`** — the capture-time hook: re-key a
   global-frame MCTS visit distribution into the network's action-space frame,
   applying the `policy_logit_location_for_ply` rotation while the position (and
   thus `active_player_id`) is in hand. This is the game-side function the
   upstream `SelfPlayCollector` hook will call; it is a pure function, so it can
   be built and fully tested here *before* the pin bump lands.
2. **`ctf_policy_loss(logits, target_policies)`** — the `PolicyLossFn` the
   `TrainingLoop` requires, now player-independent: the targets arrive already
   in-frame (from the transform), so it maps each key to its column, masks/softmax
   as decided below, and returns the cross-entropy. Loss and decoder remain two
   directions of one mapping.

> **Sequencing with upstream.** The transform and loss are written and unit-tested
> here regardless; only *wiring the transform into the collector* needs the
> `game-engine-core` capture-time hook (see the fixed point above). Once the pin
> bump lands, the transform belongs to this step's working slice; Step 3 merely
> passes it to the collector. If the pin bump has not landed when this step is
> implemented, both functions are still delivered and verified standalone.

Depends on: story-8 tensor layout and `policy_logit_location_for_ply`; the
collector *wiring* depends on the upstream hook. Later steps depend on it: Step 3
supplies the transform to the collector; Step 4's training glue consumes the loss.

Verification (automated): unit tests that exercise a **Black-to-move** position
(where the rotation actually bites — an identity-only test would hide a frame
bug): (a) `policy_transform` re-keys that position's visit distribution onto the
rotated columns, asserted against independently hand-written expected columns —
do **not** rebuild them through `policy_logit_location_for_ply`; (b) a distribution
pushed through `policy_transform` and then scored by `ctf_policy_loss` aligns with
the columns `decode_policy` reads back (the two directions round-trip); (c) the
loss is minimised when the masked softmax equals the target and grows as they
diverge; (d) the returned scalar is a mean over the batch (the loop weights by
sample count and assumes mean reduction). Run `pytest`.

Developer note: instead of verification (b), wrote a test that made sure a converted
black position gets the same evaluation as its "matching" white position.

### Step 2 — Random-placement self-play position factory

Implement the zero-argument starting-position factory the `SelfPlayCollector`
needs: draw a fresh random placement for each side and assemble the phase-2
starting position. Reuse `placement.random_placement` and
`placement.assemble_position` — this is the self-play analogue of
`match.build_initial_position`, minus the per-player seats.

Depends on: nothing new (reuses the existing placement seam). Later steps depend
on it: Step 3 feeds it to the collector.

Verification (automated): a unit test that the factory returns a legal phase-2
start position with both sides fully placed and no piece on a lake square, and
that successive calls differ (placements are actually random). Run `pytest`.

### Step 3 — Self-play collection wiring

Compose a `SelfPlayCollector` from `CtfNNEvaluator`, an `engine_factory` that
builds an `MCTSEngine` over the (currently untrained) network at the self-play
search budget and a non-zero self-play temperature, the Step 2 factory, and the
Step 1 **`policy_transform`** passed to the collector's capture-time hook (so
stored targets are already in the network frame). Run a small collection.

Depends on: Step 2 (position factory), Step 1 (the transform), the story-8
evaluator/network, and the `game-engine-core` pin bump that adds the capture-time
hook. Later steps depend on it: Step 4 consumes its samples.

Verification (automated/script): collect a handful of games at a low iteration
count and assert every `TrainingSample` has `encoded_position` of shape
`INPUT_SHAPE`, `target_value ∈ {-1.0, 0.0, 1.0}`, and `target_policy` a valid
distribution (non-negative, sums to 1) over exactly that position's legal plies;
that the stored targets are in the network frame (spot-check a Black-to-move
step against the transform); and that consecutive plies of a single decisive game
carry alternating value signs. A `pytest` test at tiny scale is preferred; note
it as improvised if run as a throwaway script instead.

### Step 4 — Single-generation training glue

Wire the pipeline for *one* generation: build the network, an optimizer, and the
Step 1 loss into a `TrainingLoop`; collect samples (Step 3); train for several
epochs on them. This is the "does learning happen at all" checkpoint, before any
multi-generation orchestration or persistence.

Depends on: Steps 1 and 3. Later steps depend on it: Step 6 wraps it in the
generations loop.

Verification (manual/script): train several epochs on one collected batch under a
fixed seed and confirm the `EpochLoss` history trends down — the network fits its
own self-play targets (an overfit-a-batch sanity check). A flat or rising policy
loss here is the signature of a Step-1 column-mapping bug, so this step is also
the real test that the mapping is right end to end.

### Step 5 — Checkpoint save and load

Implement weight persistence on top of the shared `checkpoints` conventions: save
the `CtfCrn` state at `checkpoint_path(run_dir, iteration)`, and a loader that
rebuilds a playable neural seat (evaluator + engine + `NeuralCtfPlayer`) from a
checkpoint file. This satisfies the AC that *any* checkpoint can be loaded and
used through the same interfaces as every other engine.

Depends on: the story-8 network/player (what gets saved and reconstructed).
Later steps depend on it: Step 6 writes checkpoints, Steps 7–8 load them.

Verification (automated): a round-trip test — save a network, load it into a
fresh evaluator, and assert it produces identical value and policy to the
in-memory original on a fixed position; and that `discover_checkpoints` returns
saved files in iteration order. Run `pytest`.

### Step 6 — Training orchestrator and run record

Assemble the generations loop: for each generation, collect self-play with the
current network (Step 3), train on it (Step 4), and save a checkpoint (Step 5),
carrying the improved network into the next generation. Introduce the training
configuration (the open hyperparameters) and write a run-config record into the
run directory. Expose it as a `python -m capture_the_flag.<train>` runner.

Depends on: Steps 3–5. Later steps depend on it: Steps 7–9 consume its
checkpoints.

Verification (manual): run a deliberately tiny configuration (a few generations,
few games each, low iterations) unattended and confirm it completes without
intervention and leaves a series of checkpoints plus a reproducible config record
in one run directory. This is the AC "a training run completes end to end and
produces a series of checkpoints," exercised at toy scale before the real run.

### Step 7 — Reference and checkpoint seats

Make the two remaining tournament entrants seatable through the runner surface:
the flat-value reference engine (`NullEvaluator` in an `MCTSEngine`) as a new
player kind, and a checkpoint file loaded (via Step 5) into a neural seat. Extend
`make_player` / the runner arguments accordingly, keeping the existing kinds and
defaults intact.

Depends on: Step 5 (checkpoint loading). Step 8 depends on it (the roster it
builds).

Verification (manual): through `game_runner`, play the flat-value engine against
a checkpoint-loaded neural seat in both colours and confirm each game finishes
with a legal result and no errors — the seating mechanics work before the
tournament relies on them.

### Step 8 — Strength-measurement tournament runner

Build the strength runner: assemble a roster from selected checkpoints plus the
random and flat-value reference engines, run the shared `Tournament` with
`build_initial_position` as its `position_factory` and an equal per-entrant
search budget, and report standings and the cross-table. Expose it as a
`python -m capture_the_flag.<tournament>` runner.

Depends on: Step 7 (seats) and Step 6 (checkpoints to enter). Step 9 uses it to
read strength.

Verification (manual): run it over the toy checkpoints from Step 6 and confirm it
emits standings and a cross-table with per-pairing win/loss/draw counts. Strength
*ordering* is not asserted here (toy checkpoints need not be ordered) — that is
Step 9; this step verifies the measurement apparatus produces numbers.

### Step 9 — The training run, recipe, and its record

Run training at real settings, iterating on the open hyperparameters until the
strength tournament (Step 8) shows genuine improvement, and record what was tried
and the outcome in the story folder. This is the story's headline deliverable.

Depends on: Steps 6 and 8 (the apparatus). Nothing depends on it.

Verification (manual): the Step-8 tournament shows later checkpoints beating
earlier ones, the final checkpoint beating the random engine overwhelmingly and
performing credibly against (ideally beating) the flat-value reference; and the
winning configuration plus the strength numbers are recorded well enough to
reproduce the run. This satisfies the remaining acceptance criteria.

### Step 10 — (Optional) Flag-relative-location input planes

Only if baseline training is working and there is appetite: add the four
flag-offset input planes described in the story's "Noted ideas" (signed
own/enemy-flag horizontal and vertical offsets, computed in the side-to-move
frame), which changes the encoder's `INPUT_SHAPE`. Retrain under an equal budget
and compare strength to a baseline checkpoint via the Step-8 tournament.

Depends on: Step 9 (a baseline to compare against). Explicitly **optional and not
an acceptance criterion.**

Verification (manual): a head-to-head tournament between a baseline-trained and a
flag-plane-trained checkpoint of equal training budget shows whether the extra
planes help.

### Step 11 — README check

Confirm `README.md` still describes the project accurately now that training and
tournament runners, a flat-value engine kind, and checkpoint seating exist —
updating it or confirming no change is needed.

Depends on: Steps 7–9 (the user-visible surface is final by then).

Verification (manual): run `/update-readme` (reviews the branch diff and updates
`README.md` if warranted); confirm the player roster and usage examples match the
shipped behaviour.

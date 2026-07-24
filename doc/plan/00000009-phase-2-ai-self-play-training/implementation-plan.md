# Implementation Plan: Phase 2 AI self-play training (Story 00000009)

> The developer is implementing this story (in whole or in part) for learning
> purposes. Steps stay high-level — intent and verification, no code. The
> hyperparameter / training-shape decisions are left to the developer's
> judgement: this re-scoped story asks for **sensible starting points that are
> chosen and recorded**, not values tuned until strength demonstrably improves
> (that tuning, and the tournament that would measure it, are deferred — see
> "Deferred to follow-up work"). Each open decision lists the constraints a good
> starting point must satisfy.
>
> **Status:** Steps 1–4 are implemented (commits through "Single-generation
> training"). This revision re-scopes Steps 5 onward and drops the tournament /
> strength-measurement and flag-plane steps from the story.

## Context and constraints

The deliverable is the **training machinery**: a self-play → train → checkpoint
loop that turns the untrained play engine from story 00000008 into a saved model
you can play against or resume training from, wired correctly and runnable
end-to-end on one workstation, with sensible starting hyperparameters and a
run-config record. Turning that machinery into a *demonstrated, measured*
strength gain is deferred to a follow-up (see "Deferred to follow-up work") — it
is gated on self-play throughput this story does not yet have. Everything below
builds on two established surfaces:

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
(The flat-value reference engine `NullEvaluator` and
`game_engine_core.tournament.Tournament` belong to the deferred
strength-measurement work, not this story.)

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

## Decisions to pick a sensible starting point for (the learning content)

The plan requires *that* these exist and are **recorded**, not that they are
tuned until strength improves (that is deferred). For each, choose a defensible
starting value and capture it in the run-config record:

- **Training-loop shape.** Fresh samples every generation vs. a replay buffer
  mixing recent generations; games per generation; epochs per generation; batch
  size; optimizer and learning rate. Constraint: the run completes unattended in
  acceptable wall-clock on one workstation.
- **Self-play exploration.** The self-play temperature (and any within-game
  schedule) — distinct from the greedy play-time default. Constraint: enough
  exploration that self-play games diverge, without so much noise that the visit
  distribution stops being a useful policy target.
- **Self-play search budget.** Iterations per ply during self-play — cheap
  enough for volume at this stage.
- **Checkpoint cadence.** How often to write a checkpoint. A single resumable
  latest checkpoint is sufficient here; a strength ladder is deferred.
- **The run-config record.** What a reproducibility record must capture (seed,
  every hyperparameter above, the `game-engine-core` pin / git commit, dates)
  and where it lives in the story folder. Per-checkpoint strength numbers are
  deferred with the tournament.

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

### Step 5 — Checkpoint save and load (resumable)

Implement weight persistence on top of the shared `checkpoints` conventions: save
the `CtfCrn` state at `checkpoint_path(run_dir, iteration)`, and a loader that
(a) rebuilds a playable neural seat (evaluator + engine + `NeuralCtfPlayer`) from
a checkpoint file, and (b) rehydrates the network into an in-memory `CtfCrn` so
training can continue from it. Numbered checkpoints come free from the shared
convention; there is no strength-ladder or selection logic here — a single
resumable latest is the target. Optimizer state is deliberately **not** persisted
yet (weights only); resuming re-initialises the optimizer, which is acceptable at
this scale and noted so the gap is a known one.

Depends on: the story-8 network/player (what gets saved and reconstructed) and
the shared `checkpoints` path/iteration conventions. Later steps depend on it:
Step 6 writes checkpoints, Step 7 loads the latest to resume.

Verification (automated): a round-trip test — save a network, load it into a
fresh evaluator, and assert it produces identical value and policy to the
in-memory original on a fixed position; and that `discover_checkpoints` returns
saved files in iteration order. Run `pytest`.

### Step 6 — Training orchestrator, config, and runner

Assemble the generations loop: for each generation, collect self-play with the
current network (Step 3), train on it (Step 4), and save a checkpoint (Step 5),
carrying the improved network into the next generation. Introduce the training
configuration holding the chosen starting hyperparameters (see "Decisions to pick
a sensible starting point for"), and write a run-config record into the run
directory. Expose it as a `python -m capture_the_flag.<train>` runner with an
argparse `main(argv)`, in the same shape as `batch_runner` / `game_runner`.

Depends on: Steps 3–5. Later steps depend on it: Step 7 resumes one of its runs.

Verification (manual): run a modest configuration (a few generations, few games
each, low iterations) unattended and confirm it completes without intervention,
leaves a checkpoint series plus a reproducible config record in one run
directory, and that the per-generation loss trend is downward — the machinery
learns from its own self-play. This is the AC "the loop runs end to end and
produces a saved model," exercised at modest scale.

### Step 7 — Resume training from the latest checkpoint

Extend the runner so a run can be *resumed*: on startup, discover the latest run
directory and checkpoint (via the shared conventions and Step 5's loader),
rehydrate the network, and continue collecting/training/checkpointing from the
next generation rather than starting fresh. This is the developer-facing "stop
now, keep the model to play against, resume training later" capability that
motivated the re-scope.

Depends on: Step 5 (load) and Step 6 (the loop and run directory). Nothing
depends on it.

Verification (manual): run Step 6's modest configuration, stop it, then re-invoke
in resume mode and confirm training continues — generation numbering picks up
where it left off and new checkpoints are appended to the same run — and that the
resumed network is the saved one, not a fresh re-initialisation (e.g. its
evaluation on a fixed position matches the last checkpoint before more training).

### Step 8 — README check

Confirm `README.md` still describes the project accurately now that a training
runner and resumable checkpoints exist — updating it or confirming no change is
needed.

Depends on: Steps 6–7 (the user-visible surface is final by then).

Verification (manual): run `/update-readme` (reviews the branch diff and updates
`README.md` if warranted); confirm the described runners and usage examples match
the shipped behaviour.

---

## Deferred to follow-up work

These were in the original, larger story and are intentionally out of scope here.
Each depends on the machinery this story delivers, so nothing above blocks on
them:

- **Strength-measurement tournament** (original Steps 7–8): the flat-value
  reference seat (`NullEvaluator` in an `MCTSEngine`) and checkpoint seats as
  runner player kinds, plus a `Tournament`-based strength runner reporting
  standings and a cross-table at an *equal per-entrant* search budget. This is
  how strength becomes a number rather than an impression.
- **The tuned training run to demonstrated improvement** (original Step 9):
  iterating the hyperparameters until later checkpoints measurably beat earlier
  ones and the random / flat-value references. **Gated on self-play throughput** —
  a meaningful game currently takes on the order of 15 minutes, so a
  strength-bearing run is not yet practical; rules-engine performance work may
  need to come first.
- **Flag-relative-location input planes** (original Step 10): the four flag-offset
  input planes change the encoder's `INPUT_SHAPE` and are their own story.

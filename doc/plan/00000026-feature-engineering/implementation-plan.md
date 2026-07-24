# Implementation Plan: Input feature engineering — flag-relative distance and army strength

See [story.md](story.md) for full context. This plan takes the game from the
18-plane `ENG_NN_1` encoding to the 34-plane `ENG_NN_2` encoding described
there.

## Step 1 — Widen the tensor layout (scaffolding only)

Add feature-plane index constants for the four flag-offset planes and twelve
army-strength planes to `tensor_layout.py`, at the indices the story assigns
(18–21 for flag offsets, 22–33 for army strength), and bump `TOTAL_FP_COUNT`
/ `INPUT_SHAPE` from 18 / `(18, 12, 12)` to 34 / `(34, 12, 12)`. Leave
`encode_position` untouched — the new planes exist as named indices but stay
zero-filled, since `encode_position` already zero-initializes the whole
tensor before populating it.

Depends on: nothing (first step). Everything downstream — encoder logic,
network, tests, spec doc — needs the widened shape and named constants to
exist first; this step is the pure scaffolding the plan-guide asks to keep
separate from behavior.

Verification (automated): the existing suite (`test_ctf_nn_evaluator.py`,
`test_ctf_crn.py`) still passes with `INPUT_SHAPE` now `(34, 12, 12)` —
existing-plane assertions are unaffected — and a quick check that
`encode_position(...)` now returns a `(34, 12, 12)` tensor with planes 18–33
all zero.

## Step 2 — Flag-relative distance planes

Implement the four offset planes in `encode_position`: locate each side's
flag square, re-base both the flag square and the reference square into
tensor coordinates via `tensor_position` (so the offset is expressed in the
mover's frame), and fill the row/column offset planes with the signed,
board-extent-normalized fraction per the story's formula.

Depends on: Step 1 (plane constants and shape). Independent of the
army-strength feature family, so it is implemented and verified as its own
slice before that family is added.

Verification (automated): construct positions with known flag placements and
assert sampled-square values match hand-computed signed offsets for both
flags; then the sharpest test the story calls out — a Black-to-move position
and its 180°-rotated White-to-move equivalent must encode to identical
tensors on these four planes.

## Step 3 — Army-strength planes

Implement the twelve broadcast constant planes: for each side and each
mobile rank, count remaining pieces of that rank on the board and fill the
corresponding plane with `remaining / 3`, following the same our/their
relabeling by side-to-move the piece planes already use.

Depends on: Step 1 (plane constants). Independent of Step 2's geometry work
— split out as its own verifiable slice per the one-verification-point rule.

Verification (automated): a full-army position encodes `1.0` in every rank
plane; a position with known attrition (e.g., one side missing a Knight)
encodes exactly `2/3` in that rank's plane; rotating a position swaps which
side's planes are "our" vs. "their," matching the rotation-invariance pattern
the existing piece-plane tests already use.

## Step 4 — Stack-wide shape agreement, end to end

With both new plane families implemented and `INPUT_SHAPE` at
`(34, 12, 12)`, confirm the whole stack agrees on the wider input with no
leftover hardcoding: grep-verify `CtfCrn` (and anything else that touches
plane counts) derives its channel count only from `TOTAL_FP_COUNT` /
`INPUT_SHAPE`, and run a full game through the existing engine wiring with an
untrained network.

Depends on: Steps 1–3 (the real, non-zero-filled 34-plane tensor). This is
the acceptance criterion that the network plays complete legal games
end-to-end at the new width, not just that `encode_position` runs in
isolation.

Verification (manual): run the game runner with a neural seat, e.g.
`python -m capture_the_flag.game_runner --white neural --black random`, and
confirm a complete game plays out with no shape errors. (Automated:
`test_ctf_crn.py`'s forward-pass test already exercises the widened stem
convolution once `INPUT_SHAPE` changes.)

## Step 5 — Checkpoint spec-compatibility stamping

Change the checkpoint format so a saved checkpoint records which engine spec
(`ENG_NN_2`) it was produced against, alongside its weights. Loading a
checkpoint validates that stamp against the code's current spec and fails
with a clear, spec-naming error — rather than a cryptic tensor-shape
mismatch — when they disagree.

Depends on: Step 4 (the finalized `INPUT_SHAPE` the stamp will name). This is
the checkpoint-incompatibility handling the story asks this branch to own.

Verification (automated): saving then loading a checkpoint under current
code round-trips correctly; a constructed old-shape/old-spec checkpoint
fixture fails to load with a clear error identifying the spec mismatch,
rather than an opaque size-mismatch traceback.

## Step 6 — Mint `ENG_NN_2` and close out cross-references

Write `doc/neuralnetwork/eng-nn-2.md`, documenting the full `(34, 12, 12)`
input contract (all 34 planes, normalization, perspective/coordinate
conventions) with the unchanged output section carried over verbatim from
`ENG_NN_1`. Leave `eng-nn-1.md` untouched. Update the two "noted idea"
cross-references in story 00000009 (`story.md` and
`implementation-plan.md`) to point at story 00000026 now that it is
promoted, and record the deferred scalar side-input pathway as a named
follow-up (not just an out-of-scope bullet in this story) alongside the
existing deferred-work notes in `.local/`.

Depends on: the encoder (Steps 2–3) and the checkpoint stamp (Step 5) being
final — the spec must describe exactly what the code does and name the same
spec string the checkpoint stamps.

Verification (manual): read `eng-nn-2.md` side by side with
`tensor_layout.py` / `encode_position` and confirm every plane index, value,
and convention matches exactly; grep confirms the story-00000009
cross-references now name story 00000026.

## Step 7 — Configurable network architecture, stamped in checkpoints

The architecture-stack review the story's "Architecture-stack accommodation"
section asks for found one thing that does need changing beyond the stem's
wider input convolution: `CtfCrn`'s trunk width and residual-block count are
fixed class constants, and at 32 features they are narrower than the 34 input
planes now feeding them. Make both constructor parameters instead, and raise
the defaults from 32 features / 6 blocks to a scale closer to what the engine
will actually be trained at (64 / 10 as the working default) so throughput
measured in later work reflects a realistic stack. Because the defaults get
more expensive, tests that only need *a* network should construct small ones
explicitly rather than pay the new default's forward cost.

Record the architecture alongside the engine-spec stamp in every saved
checkpoint, and have `load_network` build the network from the recorded values
rather than from current defaults. Note the deliberate asymmetry between the
two stamps: an engine-spec mismatch means the input contract changed and the
weights are meaningless, so it is rejected (as Step 5 established); an
architecture difference means the weights are valid and only the container
shape differs, so it is *reconstructed*, not rejected. That is what lets
checkpoints trained at different widths coexist under one code version — the
precondition for any later width comparison.

Depends on: Step 5 (the checkpoint format and spec stamp this extends) and
Step 4 (the finalized input width the stem is sized against).

Verification (automated): a checkpoint saved from a network built at
non-default width and depth round-trips through `save_checkpoint` /
`load_network`, coming back at those same sizes with matching weights; a
default-built checkpoint still round-trips; the existing spec-mismatch and
missing-stamp rejection tests still pass.

## Step 8 — Architecture as training-run parameters

Expose the two architecture values as training hyperparameters: fields on
`TrainingConfig`, flags on the training runner, and entries in the runner's
ignored-on-resume table, so a resume rebuilds the network from the values
recorded in the run's `run-config.json` and warns that freshly-supplied flags
are ignored — the same treatment every other non-resumable hyperparameter
already gets. A resumed run then has two independent records of its
architecture, the run config and the checkpoint stamp, which must agree.

Depends on: Step 7 (the constructor parameters these values feed, and the
checkpoint stamp they are checked against).

Verification (manual): start a short run with non-default architecture flags
and confirm `run-config.json` records them; resume that run with architecture
flags supplied again and confirm the runner warns they are ignored and that
the resumed network is built at the recorded size rather than the default.

## Step 9 — Record the architecture rationale in the spec

Add a short design-rationale section to `doc/neuralnetwork/eng-nn-2.md`
covering the two architecture decisions this story made but has not written
down anywhere durable: why army strength is carried as broadcast constant
planes rather than through a scalar side-input pathway, and what that deferred
alternative would actually involve. Be precise about the merge point — a
scalar side input merged into the value head's flattened representation is
*not* equivalent to what was built, because it leaves the policy head with
nothing; the equivalent merge is a per-channel bias applied after the stem,
which differs from a broadcast plane only by the zero-padding attenuation at
the board edge. Name the side-input pathway as a live follow-up gated on the
strength-measurement apparatus, so the story's "captured as a named follow-up"
criterion is met in version control rather than in scratch notes.

Depends on: Steps 7–8 (the architecture is in its final, configurable form, so
the rationale describes what actually shipped).

Verification (manual): read the new section against `ctf_crn.py` and confirm
it describes the network as built; confirm the deferred side-input pathway is
named somewhere version-controlled.

## Step 10 — README check

Review `README.md` against everything this story changed (input shape, spec
name, checkpoint format, configurable architecture) and update it if it
describes any of these, or confirm no update is needed.

Depends on: all prior steps being final, so there is nothing left to
describe.

Verification (manual): review README's neural-network-related sections (or
run `/update-readme`) and confirm accuracy against the finished branch.

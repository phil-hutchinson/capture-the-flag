# Story: Input feature engineering — flag-relative distance and army strength

> Working draft, parked in `.local/` while the current branch is unrelated.
> Promote into `doc/plan/00000026-feature-engineering/` when it becomes the
> active story. Story number 26 (`00000026`).

## Summary

Enrich the play engine's position encoding with two rule-derived feature
families that the network currently has to reconstruct for itself from the raw
piece planes:

- **Flag-relative distance planes** — every square's signed offset (as a
  fraction of board size) to the own and enemy flag, horizontally and
  vertically. Four new planes.
- **Army-strength planes** — for each mobile rank (Master-of-Arms through
  Militia), the fraction of that rank still on the board, for both sides.
  Twelve new planes.

Both are added as input planes to the existing encoder, taking `INPUT_SHAPE`
from `(18, 12, 12)` to `(34, 12, 12)`. Because that changes the game↔network
tensor contract, the story also **mints a new engine I/O spec, `ENG_NN_2`**,
leaving the current `ENG_NN_1` immutable. The deliverable is an encoder that emits
these planes correctly (in the side-to-move frame, like every existing plane), a
network that consumes the wider input, the new spec documenting the contract, and
test coverage proving the new planes carry the values they claim. Whether the features *help* is a strength question,
measurable only once the strength-measurement apparatus and self-play throughput
exist — so this story delivers the features and their correctness, not a strength
claim.

## Motivation

Two facts about a position are cheap to state but expensive for a convolutional
trunk to derive:

- **Where the flags are, relative to here.** The flags never move after
  placement. Under the receptive-field math, a square far from a flag needs many
  conv layers before that flag enters its field of view at all — on a 12×12
  board, corner-to-corner influence takes ~11 conv layers to propagate once.
  Baking a signed offset-to-flag into every square hands that knowledge to layer
  zero, potentially lowering the depth the network needs to reason about attack
  and defence geometry.
- **How much army each side has left.** Piece attrition is a first-order feature
  of who is winning, but recovering "how many rank-3 pieces do I have left" from
  the board requires the network to count across the whole 12×12 image — again
  something a local convolution does not do naturally. A per-rank remaining-count
  scalar states it directly.

Both are **rule-derived facts with no judgment attached** — a distance and a
count, not an evaluation of whether either is good — so they stay within the
epic's pure-discovery constraint (the same framing under which the inactivity
clock was admitted in story 00000008). We are giving the network better-posed
inputs, not hand-coded heuristics.

## What we want

### Flag-relative distance planes (4 planes)

For each square, its **signed** offset to a flag, along each axis, normalized to
`(-1, 1)`:

```
offset = (flag_coord - square_coord) / board_extent_along_that_axis
```

Four planes, in the side-to-move frame:

| plane | meaning                                    |
| ----- | ------------------------------------------ |
| 1     | signed row offset to **own** flag          |
| 2     | signed column offset to **own** flag       |
| 3     | signed row offset to **enemy** flag        |
| 4     | signed column offset to **enemy** flag     |

Signed: the sign tells the network which side of the flag a square sits on (in 
front of vs. behind, left vs. right), which absolute distance discards. In
perfect-information phase 2 both flag locations are known, so both are always 
encodable; a flag is only ever removed by being captured, which ends the game, 
so a flag is always present during play.

**Supersedes** the "flag-relative-location input planes" noted idea carried in
story 00000009 and cross-referenced in
`.local/deferred-phase2-strength-measurement.md` — this story is that idea, now
scoped and specified. Those references should point here once this is promoted.

### Army-strength planes (12 planes)

For each of the six mobile ranks and each side, the fraction of that rank still
on the board:

```
strength = count_remaining_of_rank / roster_count_of_rank      (roster = 3)
```

Twelve planes: `{our, their} × {R1, R2, R3, R4, R5, R6}`. Denominator is 3 for
every rank (the army roster is 3 of each mobile rank). A value of `1.0` means the
rank is intact; `0.0` means it has been wiped out.

**Scope decisions (resolved):**

- **Ranks only — no Tower, no Flag.** Twelve features. The Flag count is always 1
  during play (its capture ends the game), so it carries no information. The Tower 
  is excluded from this story's core set; it can be revisited as an optional 
  thirteenth/fourteenth feature if strength results ever motivate it, but it is not
  part of the deliverable.
- These are **per-position scalars**, identical across every square. They are
  encoded as **broadcast constant planes**, exactly as the inactivity clock
  already is (`FP_INACTIVITY_COUNT` fills its plane with one ratio). See the
  architecture section for why this is the chosen path and what the alternative
  would cost.

### Perspective frame

Every new plane is computed in the **side-to-move frame**, like all existing
planes. When Black is to move the board is rotated 180° and ownership relabelled
(`tensor_position` / `rotate_square` in `ctf_nn_evaluator.py`):

- Flag offsets must be computed **after** re-basing both the flag square and the
  reference square into tensor coordinates, so the offset is expressed in the
  mover's frame and "own" vs. "enemy" flag track the mover, not the colour.
- Army-strength "our" vs. "their" follows the same side-to-move relabelling the
  piece planes already use.

Encoding a Black-to-move position and its White-to-move 180°-rotation of the same
board must produce identical tensors — this is the sharpest correctness test for
the new planes.

### Architecture-stack accommodation

- Review current architecture and determine what adjustments are needed to handle
  the new feature planes (besides the feature planes themselves).
- Ensure the existing 18 feature planes is not hardcoded anywhere - e.g. `ctf_crn.py`
- **Checkpoint compatibility.** A wider input layer makes existing checkpoints
  shape-incompatible. This story owns deciding and implementing the handling —
  including how metadata (or similar approach) can be added to describe what engine
  spec the checkpoints correspond to (see next section). Alternatively, the 
  existing data could be deleted.
- Review **broadcast planes** vs. **scalar side-input pathway**.
- **Trunk width and depth become configurable (resolved).** The review found the
  trunk at 32 features — now narrower than its own 34 input planes, and small in
  absolute terms regardless of this change. Rather than swap one hard-coded size
  for another, width and residual-block count become constructor parameters,
  training-run hyperparameters recorded in `run-config.json`, and part of each
  checkpoint's metadata, with the defaults raised to a more realistic scale. The
  spec stamp and the architecture stamp are handled differently on load: a spec
  mismatch is rejected (the input contract changed, so the weights mean nothing),
  while a differing architecture is *reconstructed* (the weights are valid, only
  the container shape differs) — which is what allows checkpoints trained at
  different widths to coexist under one code version, as any later width
  comparison will require. Choosing *which* width and depth are actually best is
  a strength question and stays out of scope here; this story only makes them
  answerable.

### New engine I/O spec (ENG_NN_2)

The `doc/neuralnetwork/` specs (`ENG_NN_{n}`) are the game↔network integration
contract, deliberately independent of network internals. Per that folder's
README, **adding feature planes changes the tensor contract and therefore mints a
new spec** — this is true even though no rule changes here (the README calls out
feature-engineering plane additions explicitly). So this story owns:

- **Mint `eng-nn-2.md` (`ENG_NN_2`).** A full input/output spec for the
  `(34, 12, 12)` input: the sixteen existing planes unchanged in place, the four
  flag-offset planes (18–21) and twelve army-strength planes (22–33) documented
  with their exact values, normalization, and perspective/coordinate conventions.
  The output contract (value head, `(8, 12, 12)` policy, movement index) is
  **unchanged** and carries over verbatim.
- **Compatible rulesets carry over.** No rule changed, so `ENG_NN_2` lists the
  same combination(s) as `ENG_NN_1` (1.2 / PRE-RELEASE / none); the input can
  still faithfully represent every distinguishable state and the action space is
  untouched.
- **Leave `ENG_NN_1` immutable.** It is not edited or deleted — story 00000009's
  checkpoints are trained against it, and the README requires superseded specs to
  remain as long as parameters trained against them exist. The new planes are a
  new spec number, not a revision of the old one.
- The encoder is the single source of truth the spec documents; the two must
  agree exactly (plane indices, order, normalization, side-to-move framing), and
  the trained-artifact metadata stamps `ENG_NN_2` rather than `ENG_NN_1`.

## Relationship to other work

- **Supersedes** the flag-relative-location noted idea in story 00000009 and the
  matching bullets in `.local/deferred-phase2-strength-measurement.md`.
- **Gated for its payoff** on the same throughput/strength apparatus as the
  strength-measurement follow-up: *whether* these features help can only be shown
  as a checkpoint-strength comparison (feature-on vs. feature-off), which needs
  the tournament runner and self-play throughput that story does not yet have.
  This story therefore delivers **correct, consumed features** — not a
  demonstrated strength gain, which is a later A/B once measurement exists.

## Out of scope

- **Proving the features help.** No strength claim; the A/B comparison waits on
  the strength-measurement apparatus and throughput.
- **The scalar side-input pathway** and any game-engine-core change — deferred as
  described above; this story stays plane-only.
- **Tower / Flag strength features** — excluded from the core set; revisit only
  if results motivate it.
- **Retaining old checkpoints** — the input-width change is retrain-from-scratch;
  checkpoint migration is not attempted.
- Placement-phase features and any placement learning (stories 00000010+).

## Acceptance criteria

- `encode_position` emits all 34 planes; `INPUT_SHAPE`/`TOTAL_FP_COUNT` updated;
  the network consumes the wider input and plays complete legal games end to end
  through the existing engine wiring.
- **Flag-offset planes** are covered by tests on constructed positions: correct
  signed value and normalization at sampled squares for both flags, and — the key
  test — a Black-to-move position and its equivalent rotated White-to-move
  position encode to identical tensors.
- **Army-strength planes** are covered by tests: full army encodes to `1.0` per
  rank; positions with known attrition encode the correct `remaining/3` ratio;
  "our"/"their" track the side to move under rotation.
- **The stack agrees on the new input width end to end** — encoder, network
  first layer, and any recorded shape/config metadata all derive from
  `INPUT_SHAPE`, with no hard-coded 18 surviving; loading a now-incompatible old
  checkpoint fails clearly rather than mis-mapping.
- **A new spec `ENG_NN_2` exists** in `doc/neuralnetwork/`, documenting the
  `(34, 12, 12)` contract (all 34 planes, conventions, unchanged output), with the
  encoder matching it exactly; `ENG_NN_1` is left untouched and the new artifact's
  metadata stamps `ENG_NN_2`.
- **Trunk width and residual-block count are configurable** — settable at
  construction, passable as training-run parameters, recorded in
  `run-config.json` and in each checkpoint's metadata, and used to rebuild the
  network on resume; supplying them to a resume warns they are ignored, matching
  the treatment of every other non-resumable hyperparameter.
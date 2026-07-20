# Implementation Plan: AI engine scaffolding (Story 00000008)

> The developer is implementing this story themselves for learning purposes.
> The steps stay deliberately high-level (intent and verification, no code),
> and several design decisions are intentionally **left open** — they are the
> learning content of the story. Each open decision lists the constraints a
> good answer must satisfy, not the answer.

## Context and constraints

The deliverable is an **untrained** learned play engine that plays complete,
legal games end to end through the same interfaces every other engine uses.
Four moving parts, mirroring the story's "What we want":

1. **Position encoding** — `CtfPosition` → a fixed-shape network input, always
   from the side-to-move's perspective, including the inactivity clock.
2. **The network** — a `torch` module with a value output (judgment of the
   position) and a policy output (preferences over moves).
3. **Move-preference decoding** — the policy output turned into a proper
   distribution over exactly the position's legal plies.
4. **Wiring into search** — an evaluator plugged into the shared library's
   `MCTSEngine`, reachable as a player from batch runs, tournaments, and
   human play.

Fixed points verified against the code (game-engine-core v0.1.1 and the
current `capture_the_flag` source), load-bearing for the whole plan:

- **Evaluator contract.** `MCTSEngine` consumes a
  `PositionEvaluation(value, policy)`. `value` is in `[-1, 1]` **from the
  active player's perspective**; `policy` is a mapping keyed by `str(ply)`.
  `MCTSEngine._expand_node` **raises `ValueError` if the policy is missing an
  entry for any legal ply** — so the decoder must emit a probability for
  *every* legal ply and no illegal ones. This is the sharpest correctness
  constraint in the story.
- **Perspective.** Boards are stored in the global White's-perspective frame
  (`board.py`: columns 0–11, rows 1–12, row 1 White's back rank). "From the
  perspective of the player to move" therefore means some transform when Black
  is to move, and the *same* transform must be shared by the encoder (to
  orient the input) and the decoder (to map the network's perspective-frame
  preferences back onto real global-frame plies). Getting these two to agree
  is the crux of the story.
- **Clock state.** After the rules revamp, the position carries a single
  shared `inactivity_counter` (rules.md 5.3). It is the only non-board state
  the encoding needs; `CtfPosition.outcome` is already current-player-relative,
  which lines up with the evaluator's value convention.
- **`torch` is a hard dependency.** `game-engine-core[learning]` (which pulls
  in torch/numpy) is now the single pinned base dependency — this project always
  ships the learned play engine, so there is no torch-free install to preserve.
  The lazy-import constraint that earlier drafts carried over from
  game-engine-core (where the base engine must run without torch) therefore does
  **not** apply here: modules may import `torch` at module load. In practice the
  current design keeps `player.py` torch-free anyway — `AICtfPlayer` receives an
  already-constructed engine, so torch only enters at the construction site in
  the runner wiring (Step 7) — but that is a consequence of the design, not a
  requirement to engineer around.
- **Training machinery fits as-is.** Story 00000009 will train against
  `MCTSEngine.select_ply_with_policy` (the visit-distribution policy target),
  which already exists. Nothing in this story needs a dependency-pin bump;
  the design just must not preclude that seam (e.g. the evaluator and network
  should be constructible with externally supplied weights later).
- **Runner seam today.** `batch_runner` currently hardcodes random-vs-random
  and `pvp_runner` human-vs-human; there is no engine-selection seam yet.
  Making the AI player reachable from the runners is therefore a real (small)
  deliverable of this story, not free.
- **Reference opponents.** The story-00000006 heuristic engine is not yet
  implemented, so "reference opponents" for volume verification means random
  movers (optionally seated with reference placement files from
  `placements/`); placement intelligence itself is out of scope.

## Decisions deliberately left open (the learning content)

The plan requires *that* these exist, not *what* they are:

- **Input representation.** How the board and clock become numbers: what the
  encoding's axes mean, how piece type and ownership are represented, how a
  bounded integer clock is best presented to a network. Constraints: fixed
  shape across all positions, side-to-move relative, faithful (two positions
  that differ under the rules must encode differently — the clock
  requirement in the story is exactly this), and the shape must be exposed
  as a constant other modules can import.
- **Action-space layout.** How every geometrically-possible ply gets a stable
  index. Constraints: fixed size known at network-construction time; every
  legal ply of every position maps to a distinct in-range index; the mapping
  is invertible on the legal set; it lives in the perspective frame so the
  network sees "my moves" consistently. Worth thinking about: what is the
  maximum move distance any piece can have, and is it cheaper to index
  squares-to-squares or square×direction×distance?
- **Network architecture.** Body type, depth/width, how the two heads attach,
  parameter count appropriate for a 12×12 board and single-workstation
  training, weight initialisation. Constraints: input shape from the encoder,
  one policy logit per action-space index, value output bounded to `[-1, 1]`,
  reproducible under a seed for testing.
- **Search settings for the untrained engine.** Iteration count (small enough
  to play at volume) and temperature. Constraint: defaults must let a batch
  of games finish in reasonable wall-clock time.

---

### Step 1 — Perspective transform and board encoding

Implement the shared side-to-move orientation transform (identity when White
is to move; the appropriate board transform plus ownership swap when Black is
to move, so the input always reads "own side moving up the board"), and use it
to encode board occupancy into the chosen input representation. Establish the
module that owns the encoding and expose its shape as a module-level constant
so later steps can depend on the shape without importing behaviour.

Depends on: nothing (leaf). Later steps depend on it: the transform is reused
by Step 3's decoder; the shape constant is consumed by Step 4's network.

Verification (automated): unit tests that (a) encode a hand-built position
with White to move and assert each occupied square lands where the chosen
representation says it should; (b) encode the *same* board with Black to move
and assert the result equals the White-to-move encoding of the transformed,
ownership-swapped board — i.e. the two perspectives are exact mirrors of each
other; (c) assert the transform is an involution (applying it twice is the
identity). Run `pytest` on the new encoding test module.

> **As implemented:** the perspective transform lives as a closure inside
> `encode_position`, so test (c) — the direct involution test — is deferred to
> Step 3, which needs the transform lifted out anyway (see the note there).
> The involution property is covered indirectly by test (b): the hand-built
> mirror-pair positions in the test module encode identically.

### Step 2 — Clock feature

Extend the encoding with the inactivity clock: the shared
`inactivity_counter`, presented in whatever bounded form the input
representation calls for. Update the shape constant from Step 1 if the
addition changes it.

Depends on: Step 1 (extends the same encoder). Later steps depend on the
finalised input shape (Step 4).

Verification (automated): unit tests on positions constructed to exercise the
clock — the same arrangement of pieces with different counter values must
encode differently, and the clock feature must track the counter value
(including near the 50-ply draw threshold). This directly satisfies the
acceptance criterion that the rule-derived clock state is covered by tests on
positions built to exercise it. Run `pytest`.

### Step 3 — Action space and policy decoding

Define the fixed action-space enumeration (see the open decision above), then
implement the decoder: given a raw policy vector and a `CtfPosition`, map the
position's legal plies (global frame) through the Step 1 transform into
action-space indices, keep only those entries, normalise into a probability
distribution over the legal set, and return a mapping keyed by `str(ply)`
covering exactly the legal plies.

Depends on: Step 1 (shares the orientation transform). Later steps depend on
the action-space size constant (Step 4) and the decoder (Step 5).

> **Deferred from Step 1:** the 180-degree `Square`-to-`Square` rotation is
> currently a closure inside `encode_position` (`_get_tensor_position`, which
> also does the 0-based index conversion). This step needs the rotation to map
> plies between frames, so lift it to a shared module-level helper here, have
> the encoder and the test fixtures use it, and add the direct involution test
> (`rotate(rotate(sq)) == sq` over all 144 squares, plus a couple of known
> mappings such as A1 -> L12) that Step 1 deferred. Keep the hand-written
> expected literals in the Step 1 tests as an independent witness — they must
> not be rebuilt through the shared helper.

Verification (automated): unit tests that, for several positions (including
one with the longest-range moves available), assert the decoded distribution
(a) has an entry for every legal ply and no others, (b) is non-negative and
sums to 1, and (c) is unaffected by the values at illegal indices (illegal
moves never receive mass). Round-trip test: every legal ply maps to a
distinct in-range index and back to itself. This locks in the `MCTSEngine`
"policy must cover all legal plies" contract before any network exists. Run
`pytest`.

### Step 4 — The network

Implement the `torch` module per the open architecture decision: input shape
from Steps 1–2, one policy logit per Step 3 action index, a bounded value
output, seedable initialisation.

Depends on: Steps 1–2 (input shape) and Step 3 (policy width). Later steps
depend on it: Step 5 runs it.

Verification (automated): unit tests that run a forward pass on a small batch
of zero/random inputs and assert the value output has the right shape and
lies in `[-1, 1]`, and the policy output has exactly the action-space width;
and that two forward passes under the same seed match. Run `pytest`.

### Step 5 — Network position evaluator

Implement the `PositionEvaluator` that composes the pipeline: encode the
position (Steps 1–2), run the network in inference mode (Step 4), decode the
policy output against the position's legal plies (Step 3), and return
`PositionEvaluation(value, policy)` — the value taken straight from the
network's (already perspective-relative) value output.

Depends on: Steps 1–4. Later steps depend on it: Step 6 wires it into a
player.

Verification (automated): unit tests that, on a handful of real mid-game
positions, assert the returned value is a float in `[-1, 1]` and the returned
policy is a valid distribution over exactly the legal plies; **and** an
integration check that constructs an `MCTSEngine(evaluator)` with a small
iteration count and calls `select_ply` on a real position, confirming it
returns a legal ply with no `ValueError` (i.e. the decoder truly satisfies
the engine's coverage contract). Run `pytest`.

### Step 6 — The AI player

Implement the `CtfPlayer` for the learned engine: `select_ply` delegated to
an `MCTSEngine` wrapping the Step 5 evaluator (with the chosen untrained-play
search settings), and `get_placement` using a random or reference placement
(placement intelligence is out of scope — stories 00000010–00000012).

Depends on: Step 5 (the evaluator to wrap). Step 7 depends on it (the player
the runners will name).

Verification (automated): a test that plays one complete match through
`play_match` with the AI player against a random player and asserts it
finishes with a legal result and no errors.

### Step 7 — Runner wiring and end-to-end volume play

Make the AI player selectable wherever players are seated today: the batch
runner (and its `Tournament` roster) and the human-play runner, so batch
runs, tournaments, and human-vs-AI games all reach it through the existing
seams. The selection mechanism (CLI options naming a player kind, etc.) is a
small design choice for the developer; existing default behaviour must be
preserved.

Depends on: Step 6 (the player to seat). Nothing depends on this step.

Verification (manual): run the batch runner at volume with the AI seated
against a random opponent, in both colours (e.g. a run where the AI holds
White and one where it holds Black, for a meaningful number of games).
A passing result: every game completes with a legal result and no errors or
exceptions — satisfying the acceptance criterion that the untrained engine
plays complete legal games at volume through the shared library. (Games will
be weak; that is expected and not part of the pass condition.) Also play a
few moves against it through the human-play runner to confirm that path.

### Step 8 — README check

Confirm `README.md` still accurately describes the project now that an AI
player and new modules exist — its status paragraph and runner instructions
predate any AI beyond random play — updating it or confirming no change is
needed.

Depends on: Step 7 (the user-visible surface is final by then).

Verification (manual): run `/update-readme` (reviews the branch diff and
updates `README.md` if warranted); confirm the described player roster and
usage examples match the shipped behaviour.

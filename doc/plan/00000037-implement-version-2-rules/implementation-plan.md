# Implementation Plan — Story 37: Implement Version 2 Rules

Thirteen steps. Each is verified before the next begins, per
[`CLAUDE.md`](../../../CLAUDE.md)'s implementation strategy.

## Notes on sequencing

Three constraints shaped the order.

**Move generation can only reach the board through the position.** `legal_plies`
is a `GamePosition` protocol property with no arguments, so once geometry stops
being a module constant, `CtfPosition` is the only channel that can carry it.
That makes "the position carries its layout" a load-bearing early step rather
than a stylistic choice, and it is why the board work cannot be deferred behind
the edition work.

**The policy head is widened before move generation emits a diagonal.** Diagonal
attack adds four movement deltas to the action space. Widening first — with the
four new indices reserved and never populated — keeps the neural path runnable at
every point in the sequence. The reverse order would leave the trained engine
unable to index a legal ply for one step.

**The documents lead the code, edition by edition.** Steps 1–10 implement only
what `rules.md` already publishes. `2-1:SKIRMISH` and the `TOWER_PLACEMENT`
appendix entry arrive together in step 11, which is where the document is written
and the code follows it in the same step.

Two transients are expected and are fine on an unmerged branch. Between steps 2
and 5 the engine plays major-2 rules while still stamping `1-2:PRE-RELEASE`.
Between steps 7 and 11 it plays and stamps `2-0:SKIRMISH`, which step 11 supersedes
— so branch-local artifacts written in that window become unloadable, and step 12
clears them.

---

### Step 1 — Widen the policy action space to twelve movements

Add the four diagonal deltas to the movement index in `tensor_layout.py`, carry
the widened action space through `ctf_policy_target.py`, `ctf_crn.py`, and
network construction, and bump `ENGINE_SPEC_NAME` to `ENG_NN_3`. No diagonal ply
is generated yet, so the four new indices stay empty throughout.

The **spec document is not minted here**. `doc/neuralnetwork/README.md` requires
a contract change to mint one, and requires a minted spec to be immutable — but
steps 7 and 8 change the same contract again, so a document written now would be
rewritten twice before the branch merges. The constant moves now, because it is
what stops an eight-movement checkpoint loading into a twelve-movement policy
head; the document is minted in step 8, once the contract has settled.

Depends on: nothing. It comes first because step 2 emits plies that need somewhere
to land in the policy target.

Verification (manual): run `python -m capture_the_flag.training_runner
--generations 1` and confirm it completes and writes a checkpoint. Existing
checkpoints being rejected on the spec stamp is the change working, not a
failure.

---

### Step 2 — Diagonal attack in move generation

Generate one-square diagonal plies in `moves.py`, onto a square occupied by an
enemy **mobile** piece only. Never onto an empty square; never extended by the
unencumbered bonus. A lake corner does not block a diagonal, so no path check
applies. `combat.py` is untouched — a diagonal attack that is generated resolves
by exactly the rules an orthogonal one does.

Depends on: Step 1 (the policy head can now index the new deltas).

Verification (automated): extend `tests/test_moves.py` — a diagonal attack on a
numbered piece is generated; on a Tower and on the Flag it is not; onto an empty
diagonal square it is not; the skirt case (a piece on A6 attacking B5 past the
lake corner at B6) is generated; an unencumbered piece gets no two-square
diagonal. Run `pytest tests/test_moves.py tests/test_combat.py
tests/test_outcome.py`.

---

### Step 3 — Board geometry becomes a value carried by the position

Introduce a board-layout value type in `board.py` holding dimensions, home-zone
rows, lake rows, the lake column pattern, the derived square sets, and the column
letters, with `standard_144` as its only value. `CtfPosition` gains a field
holding it. `moves.py`, `rendering.py`, `game_view.py`, `placement.py`,
`placement_file.py`, and `parse_square` read geometry from the layout rather than
from module constants, and the constants leave the package's public surface.

Depends on: Step 2 only by file proximity — but it must precede every step that
varies the board, and the position field is what move generation reads.

Verification (manual, no-regression): run the full `pytest` suite, then play a
terminal game (`python -m capture_the_flag.game_runner --white human --black
random`) and confirm the rendered board and legal plies are unchanged from
before the step.

---

### Step 4 — Army composition becomes a value

Introduce an army-composition value type holding the per-piece roster, with
`standard_battle` as its only value, and remove `army_count` from `PieceType` —
a count living on the enum member is a single global army by construction. Rank,
symbol, name, and mobility stay. `placement.py`, `placement_file.py`,
`game_view.py`, `record.py`, and `ctf_nn_evaluator.py` take the roster from a
composition value.

Pair the composition with the layout in a **`GameSetup`**, rather than threading
a second parameter beside the first. A board and an army are independent flags
but nothing plays a game with one and not the other, and seven signatures between
the runner and the placement seam would otherwise carry both. The pairing is also
the only place the two flags meet, so it is the only place the rules' **invalid
combinations** can be caught — an army must fit its home zone one piece per
square, which is what makes `standard_battle` on `standard_64` unplayable. Step 6
grows the run-time configuration from this rather than replacing it.

Depends on: Step 3 (both are consumed together by the configuration in step 6,
and placement touches geometry and roster in the same functions).

Verification (manual, no-regression): run the full `pytest` suite, load
`placements/white-rush.txt` through
`python -m capture_the_flag.game_runner --white-placement white-rush.txt`, and
confirm the setup is accepted and the game plays.

---

### Step 5 — The flag registry, edition table, and configuration resolution

Register `BOARD_LAYOUT` and `ARMY_COMPOSITION` in `RULE_FLAGS` with their
published defaults. Add `2-0:BATTLE` to `EDITIONS` alongside `1-2:PRE-RELEASE`,
and turn `ACTIVE_EDITION` from a single string into the set of Active ids. Drop
`Edition`'s `distribution` field: since major 2 the distribution is the resolved
`ARMY_COMPOSITION` value, not a second axis with its own claim on the army. Add
resolution from a `RulesetConfiguration` to the `GameSetup` it selects.

**`2-0:SKIRMISH` waits for step 7, not this step**, even though `rules.md`
publishes it today. `EDITIONS` is the engine's copy of the part it must act on,
and an Active edition the build cannot set up would be a claim it does not
support — `standard_64` and `standard_skirmish` do not exist until step 7.
`2-1:SKIRMISH` waits for step 11 as before.

Resolution therefore has **two** rejection paths, saying different things:
`unsupported_aspects` refuses an edition or label that is not *published*, while
resolution refuses a published label this *build* has no implementation for.
`standard_64` is the second case throughout steps 5 and 6.

Depends on: Steps 3 and 4 (resolution needs layout and composition to be values
it can resolve *to*).

Verification (automated): replace the single-roster assertion in
`tests/test_record.py` with a per-edition one — each Active edition's resolved
army matches the one it publishes, failing if an Active edition is added without
stating its army. Add tests that a historical edition, an unknown edition, and a
published-but-unbuilt label are each refused in their own words. Run
`pytest tests/test_record.py tests/test_game_setup.py`.

Verification (manual): re-run the seeded 20-game batch and confirm every record
is unchanged **apart from the `Ruleset` tag**, which now reads `2-0:BATTLE`
instead of `1-2:PRE-RELEASE`. Confirm a training run stamps the same
configuration into its checkpoint and its `run-config.json`.

---

### Step 6 — The configuration is selected at launch and threaded through

Introduce the run-time configuration object pairing a `RulesetConfiguration` with
its resolved layout and composition, and thread it through `game_runner`,
`batch_runner`, `training_runner`, `match`, `game_ui`, and `run_environment`,
defaulting to `2-0:BATTLE`. Add the CLI option that selects the ruleset. Records
stamp the configuration the game actually played rather than a build constant.

Depends on: Step 5 (there is now a configuration to select and resolve).

Verification (manual): run `python -m capture_the_flag.batch_runner -n 5 -o games`
and confirm each written record carries `[Ruleset "2-0:BATTLE"]` — not
`1-2:PRE-RELEASE` — and that the position block and move sequence are unchanged
in form.

---

### Step 7 — `standard_64` and `standard_skirmish`

Add the second value for each flag: the 8 × 8 geometry with 3 home rows, 2 lake
rows, no buffer, and lakes on columns B/C and F/G; and the 16-piece roster of 3
each of ranks 1–4, 3 Towers, 1 Flag. Add `2-0:SKIRMISH` to `EDITIONS` and to the
Active set, which step 5 deferred to here because the build could not set it up.
Everything that does not go through the neural engine becomes playable on
Skirmish.

Depends on: Step 6 (a second value is only reachable once a configuration selects
it).

Verification (manual): run `python -m capture_the_flag.batch_runner -n 5
--ruleset skirmish` and confirm it completes; the record's position block is 8
lines of 8 cells with `XXX` at B/C and F/G in rows 4–5; the tag reads
`[Ruleset "2-0:SKIRMISH"]`. Also add the automated squeeze check now that a
second layout exists: no legal diagonal ply on either published layout has lakes
on both of its flanking squares, confirming the case `technical-notes.md` leaves
unaddressed is genuinely unreachable.

---

### Step 8 — The tensor layout is derived from the configuration

Derive the input and action-space shapes from the configured layout, and
normalize the per-rank quantity features by the configured composition. The
rank-5 and rank-6 planes stay present and read zero under a composition without
those ranks, so the plane layout is one contract across compositions rather than
two — which is what keeps cross-composition transfer an open question rather than
a foreclosed one. Qualify `ENGINE_SPEC_NAME` by layout, so a checkpoint trained
on one board cannot silently meet a differently-shaped input.

Mint `doc/neuralnetwork/eng-nn-3.md` here, now that the contract is final: the
twelve-movement action space, the board-parametric shapes, and the compatible
rulesets, which are the two Active editions rather than `1-2:PRE-RELEASE`.

Depends on: Step 7 (both layouts must exist for the shape to be worth deriving,
and the step is verified on both).

Verification (manual): run a one-generation training run against each ruleset and
confirm both complete. Inspect the two checkpoints and confirm they carry
different stamped spec names and differently-shaped tensors.

---

### Step 9 — Checkpoint stamps are compared against the run's configuration

Change `ctf_checkpoint` to compare a stamped configuration against the
configuration the run is playing rather than against a build-level constant.
A checkpoint stamped with a non-Active edition is rejected *because it is not
Active* — the rules changed, so its weights never saw them — rather than because
a build holds only one edition. Adoption is unchanged for a configuration the
running code can implement.

Depends on: Step 8 (the checkpoint now carries both a layout-qualified spec and a
configuration, and both checks live on the same load path).

Verification (automated, plus one manual): tests that a checkpoint stamped
`1-2:PRE-RELEASE` is rejected with the not-Active reason, that a Skirmish-stamped
checkpoint is rejected under a Battle run, and that an unstamped checkpoint is
still rejected rather than defaulted. Manually resume a Battle training run from
its own checkpoint and confirm it continues rather than restarting.

---

### Step 10 — `TOWER_PLACEMENT`

Write the proposal into `proposed-variants.md` first — identifier, value labels,
default, what `spacing_and_lanes` does, and why — then implement it. Register the
flag, and apply the restriction in placement validation, the random placement
generator, and placement-file validation. The forbidden set is derived
geometrically from the layout (a square orthogonally adjacent to a non-lake
square in a lake row), never enumerated per layout value.

`placement.py`'s comment proving the greedy Tower walk never stalls is argued
from six Towers in 48 squares; re-derive it per layout rather than deleting it.

Depends on: Step 7 (the restriction only closes squares on `standard_64`, so it
cannot be meaningfully tested before that layout exists).

Verification (automated): tests that under `spacing_and_lanes` the closed squares
on `standard_64` are exactly A3, D3, E3, H3 and A6, D6, E6, H6 and that B3, C3,
F3, G3 stay open; that on `standard_144` the restriction closes nothing; that
random Skirmish placements across many seeds never put a Tower on a closed
square and never stall; and that a placement file violating the restriction is
rejected with a player-facing message. Run `pytest tests/test_placement.py
tests/test_placement_file.py`.

---

### Step 11 — Publish `2-1:SKIRMISH` and update the ruleset documents

Write the documents, then bring the code to them:

- `rules.md` — §3 gains the Tower lane restriction stated plainly and carried by
  the Skirmish examples; the glossary gains *Lane*; Appendix A gains
  `TOWER_PLACEMENT`, graduating from `proposed-variants.md`; Appendix B publishes
  `2-1:SKIRMISH`, moves `2-0:SKIRMISH` to Historical marked *superseded*, and
  spells out `TOWER_PLACEMENT=spacing_only` on the `2-0:BATTLE` row.
- `technical-notes.md` — the precise geometric definition, the revised Active
  edition list, and the rejected connectivity alternative.
- `changelog.md` — one entry for `2-1:SKIRMISH`, newest first, story 37 and date.
- `doc/ruleset/CLAUDE.md` — the two Active editions become `2-0:BATTLE` and
  `2-1:SKIRMISH`.
- `record.py` — `EDITIONS` gains `2-1:SKIRMISH`; the Active set becomes
  `{2-0:BATTLE, 2-1:SKIRMISH}`.

Depends on: Step 10 (an edition may not turn on a flag the engine cannot yet
implement).

Verification (manual, plus automated): run
`python -m capture_the_flag.batch_runner -n 5 --ruleset skirmish` and confirm the
tag now reads `[Ruleset "2-1:SKIRMISH"]` with **no** deviating flag token — the
flag is at its edition value, so it is omitted. Re-run `pytest
tests/test_record.py` and confirm the per-edition distribution assertion passes
for both Active editions. Read the document diff end to end.

---

### Step 12 — Retire the outdated training runs

Delete the seven directories under `training-runs/` and their sixteen
checkpoints. All are stamped `1-2:PRE-RELEASE`, all were trained under the
eight-movement action space, and all are unloadable twice over after this story —
once on the ruleset stamp and once on the engine spec. Clear any branch-local
runs written under `2-0:SKIRMISH` in the step 7–11 window for the same reason.

Depends on: Step 11 (the Active edition set is final, so what is stale is
settled).

Verification (manual): confirm `training-runs/` is empty of pre-story runs and
that nothing in the repository or documentation references a deleted run
directory by name. Then run `python -m capture_the_flag.training_runner
--generations 1 --ruleset skirmish` and confirm a fresh run directory is created
and completes.

---

### Step 13 — README check

Review `README.md` against the branch diff and update it if the story changed
anything it describes — in particular the runner invocations, which now take a
ruleset option, and any statement that assumes a single board or army.

Depends on: Step 12 (the branch is complete, so the diff is final).

Verification (manual): run the `/update-readme` command, which reviews the branch
diff and updates `README.md` if warranted, then read the result.

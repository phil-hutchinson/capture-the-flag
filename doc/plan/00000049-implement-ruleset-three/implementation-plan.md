# Implementation Plan — Story 49: Implement Ruleset Three

Twenty steps. Each is verified before the next begins, per
[`CLAUDE.md`](../../../CLAUDE.md)'s implementation strategy.

## Notes on sequencing

Five constraints shaped the order.

**The documents lead, and here they lead everything.** No code may cite a shadow
document as a definition, so major 3 has to be *published* before the engine can
be checked against it. That inverts story 37's arrangement, where the documents
were already ahead and the code caught up edition by edition: step 1 publishes the
whole ruleset, and every step after it implements a document that already governs.

**The piece enum is the one atomic change.** `PieceType` carries each piece's rank
on the member itself, so a build cannot hold both rank orderings at once — and the
edition table, the army composition, `GameSetup`, phase 1 and the network's plane
maps all name members that major 3 removes. Step 3 is therefore large and cannot be
subdivided without leaving the package unimportable partway through. Steps 2 and 4
exist to make it as small as it can be: step 2 adds the new board *before* the
swap, and step 4 deletes the major 2 geometry *after* it, so neither rides along
inside it.

**A stub start position breaks the phase-1 cycle.** Deleting placement needs
something to build a starting position from, and real generation needs the major 3
board and army, which the same step introduces. Step 3 therefore lands a
deterministic start position — the Flag on A1, the ranks in a fixed order, Black by
reflection — and steps 7 and 8 replace it with uniform generation and position IDs.
Pick the fixed arrangement so that the **weak** ranks sit in the Flag's half: the
strength rule then selects the reflection branch for it, which makes the stub a
position generation could itself have produced rather than merely a legal-looking
board. The engine is playing a real major 3 opening throughout; only its variety is
missing.

**The tensor contract is closed early, immediately after the army moves.** Step 3
leaves the encoder writing major 3 pieces into `ENG_NN_3`-shaped planes, which is
the one genuinely incoherent state in the sequence. Steps 5 and 6 close it before
the rules work starts. Nothing in steps 7–18 touches the tensor contract — the
rules changes alter which plies are legal and what combat does, never what a
position encodes to — so this costs nothing to bring forward.

**Rules changes come one at a time, and last.** By step 10 the board, the army, the
configuration, the start position and the network are all major 3; what remains is
six independent rule changes (steps 11–17), each of which can be turned on and
tested on its own against a game that plays correctly before and after.

## Expected transients

Two, both fine on an unmerged branch and both closed before it merges.

- **Between steps 3 and 17 the engine stamps `3-0:PRE-RELEASE` while not yet
  playing it.** Movement, combat and the endings arrive one step at a time, so
  records written in that window name rules the game was not played under. No
  artifact from this window is meant to survive; do not keep records or
  checkpoints written before step 18.
- **Between steps 3 and 6 the encoder writes major 3 pieces into `ENG_NN_3`
  planes.** The Tower and rank-6 entries are dropped so the maps still resolve,
  but the spec name still claims a contract the planes no longer honour. Step 6
  ends it.

---

### Step 1 — Publish the ruleset documents

Graduate [`doc/ruleset/proposed-3/`](../../ruleset/proposed-3/README.md) into the
published documents: `rules.md` and `technical-notes.md` replaced by their shadow
copies, `start-position.md` added, the changelog entry published at the top of
`changelog.md` as published rather than proposed, and the folder deleted. Withdraw
`DIAGONAL_ATTACKABLE` and `DIAGONAL_ATTACK_PATH` from `proposed-variants.md`,
recording that they landed as baseline behaviour at major 3 rather than as flags.
Apply the two corrections story 46 named as owed on adoption — the within-major
scoping of the notation-break sentence, and anything in `technical-notes.md` that
generalises over the major 2 rulesets. Update `doc/ruleset/CLAUDE.md` (one Active
edition; no shadow folder; a single board and army in its "three places" tables)
and the root `CLAUDE.md` (the game is no longer two-phase and has no secret
placement).

Depends on: nothing.

Why it comes first: every later step is checked against a published document, and
until this step there is no published document to check against. It is also the
step that makes the decision — after it, major 3 is the ruleset and major 2 is
history.

Verification (manual): read `rules.md` and `start-position.md` end to end and
confirm the game could be implemented from those two alone. Then run
`git status --short` and confirm the change set is documents only, with
`doc/ruleset/proposed-3/` deleted, and `grep -rn "proposed-3" doc README.md
CLAUDE.md` returning nothing outside this story's own folder.

---

### Step 2 — Add the major 3 board

Add the 8 × 8, two-home-row, lake-free layout to `board.py` alongside the three
existing ones, and register it in `BOARD_LAYOUTS` under an id that is **not** a
published `BOARD_LAYOUT` label — `standard_64` permanently names the Skirmish
board, which is 8 × 8 *with* lakes.

Depends on: Step 1 (the board is `rules.md` §2.1's).

Why it comes here: purely additive, so it can be verified on its own — and it
means step 3 finds the board it needs already present rather than introducing a
board and an army together.

Verification (automated): a test asserting the layout's dimensions, that each home
zone is two rows of eight squares, and that the existing three layouts are
unchanged. `pytest tests/test_board.py`.

---

### Step 3 — The army, the edition, and the end of phase 1

The atomic swap. Replace `PieceType` with major 3's five ranks plus the Flag —
rank 5 strongest, no Tower, no Knight or Halberdier, Peasant added — and add the
rank-reduction relation (which piece a given rank reduces to) as data on the enum
rather than as a lookup somewhere else. Replace the three army compositions with
the single 16-piece one. In `record.py`, publish `3-0:PRE-RELEASE`, make it the
only member of `ACTIVE_EDITIONS` and the default, move the three major 2 editions
to historical rows, and empty `RULE_FLAGS`. Collapse `GameSetup`: no flag
resolution, no `tower_placement`, and an army that must *fill* its home zone
rather than merely fit it. Delete `placement.py`, `placement_file.py`, the
`placements/` directory and its `.gitignore` entry, both of their test modules,
the `get_placement` seam on `CtfPlayer` and its two implementations, the
placement dialogue in `player.py`, `PlayerContext.placements_dir`, the
`-p`/`--placements-dir` option, and `MatchResult`'s placement fields. In their
place, `match.build_initial_position` and `CtfPositionFactory` build the
deterministic stub start position described above. Drop the Tower branch from
`combat.py`, and drop the Tower and rank-6 entries from the evaluator's plane maps
so they still resolve.

Depends on: Step 2 (the board), Step 1 (the army and the edition are published).

Why it comes here: `PieceType` cannot hold two rank orderings, and everything
listed names a member that major 3 removes — so the package is unimportable at any
intermediate point. Everything that *can* be lifted out of it has been: the board
in step 2, the major 2 geometry in step 4, the plane set in step 6.

Verification (manual): `python -m capture_the_flag.game_runner --white random
--black random --seed 7` plays a complete game on an 8 × 8 board with 16 pieces a
side, no Towers, no lakes and no placement prompt, and announces a result. Confirm
the record's `Ruleset` tag reads `3-0:PRE-RELEASE` and that `--ruleset` offers only
`PRE-RELEASE`. `pytest` passes, with the tests for deleted concepts deleted rather
than skipped.

---

### Step 4 — Delete the major 2 geometry

Remove what step 3 orphaned: the three major 2 layouts and their compositions,
`BoardLayout`'s `lake_rows`, `lake_pattern`, `lake_squares`, `lane_squares`,
`lane_adjacent_squares`, `is_lake` and the lake validation, the lake checks in
`moves.py`, the `XXX` cell in `rendering.py`, and the `TOWER_PLACEMENT` labels and
`forbidden_tower_squares` in `game_setup.py`. Module docstrings that explain
geometry this repository no longer has go with them.

Depends on: Step 3 (nothing may still reference any of it).

Why it comes here: dead-code removal separated from the swap that killed it, so a
failure in this step is unambiguously a missed reference rather than a rules
mistake.

Verification (automated + improvised): `pytest` and `pyright` pass, and
`grep -rniE "lake|lane|tower|standard_144|asymmetric_100|standard_64|standard_battle" capture_the_flag tests`
returns nothing but deliberate historical mentions (the major 2 edition rows and
the changelog references to them).

---

### Step 5 — Write the `ENG_NN_4` specification

Write `doc/neuralnetwork/eng-nn-4.md`: the plane list for major 3 (Tower and
rank-6 presence planes gone, five ranks per side with 5 strongest, the passability
plane gone on a board with no impassable squares, and the twelve per-rank quantity
planes **removed**), the unchanged twelve-offset action space, and
`3-0:PRE-RELEASE` as the one compatible ruleset combination. State the two
arguments that look like problems until they are written down: why the action space
needs no change (the new rules only remove legality, which is never part of the
compatibility test) and why White's one-square first ply needs no plane (a repeat
of the starting arrangement is only reachable by non-capturing plies, which raise
the already-encoded inactivity counter, so the two positions do encode
differently).

Depends on: Step 1 (the rules the spec is compatible with), Step 3 (the army whose
ranks it enumerates).

Why it comes here: the spec is a document and the document leads. Writing it first
also means step 6 is transcription rather than design.

Verification (manual): read it against `doc/neuralnetwork/README.md`'s list of what
a spec must contain, and confirm `eng-nn-3.md` is left untouched — a superseded
spec stays in the folder unchanged.

---

### Step 6 — Implement `ENG_NN_4`

Bring `tensor_layout.py`, the evaluator's encoding, and the checkpoint spec stamp
to the spec written in step 5: the new plane constants and count, the quantity
planes and their per-rank normalisers deleted, the passability plane deleted, and
`ENGINE_SPEC_NAME` bumped to `ENG_NN_4`.

Depends on: Step 5 (the spec), Step 3 (the army and board it encodes).

Why it comes here: it closes the incoherent window step 3 opened, and it is the
last step that touches the tensor contract — steps 7–18 change rules, which the
contract is indifferent to.

Verification (automated + manual): `pytest tests/engines` passes, then
`python -m capture_the_flag.training_runner --generations 1 --games 2
--iterations 8 --seed 3` completes a generation, writes a checkpoint stamped
`ENG_NN_4` and `3-0:PRE-RELEASE`, and a second invocation resuming that run is
accepted. Confirm an `ENG_NN_3` checkpoint from before this branch is refused on
its spec stamp.

---

### Step 7 — Generated start positions

Replace the stub with real generation in a start-position module: White's
arrangement drawn uniformly from the constrained set (Flag on a uniform square of
row 1, the fifteen numbered pieces shuffled into the rest), and Black's derived by
the strength rule — sum the ranks of the seven numbered pieces in the Flag's half,
half-turn at 22 or more, reflect at 21 or less. **Derive the threshold from the
army** in the general form `start-position.md` §3 states rather than writing 22 as
a constant.

Depends on: Step 3 (the army and the stub seam it replaces).

Verification (automated): tests asserting, over many seeded draws, that both home
zones are always full, that the Flag is always on row 1 (and row 8 for Black), and
that Black's army is congruent to White's under the turn the strength rule selects.
Plus the cheapest check that generation and the rules agree: **every legal opening
ply originates on row 2**, one per front-row piece, with no back-row piece able to
move — the enclosure `start-position.md` §1 derives from a completely full home
area. (The document's stronger claim, that there are exactly eight opening plies,
also needs the one-square first-ply restriction and so is step 11's to verify;
until then each front-row piece additionally has its two-square move.) Plus a test
that the derived threshold equals 22 for this army.

---

### Step 8 — Position IDs

Add encoding, decoding and validation for the 16-character hexadecimal position
ID, case-normalised on input, handled as a string throughout; and a `mirror_of`
helper the generator does not call.

Depends on: Step 7 (an arrangement to encode).

Why it comes here: generation is what makes an ID worth having, and the validator's
job is defined against the constrained set step 7 implements.

Verification (automated): round-trip every position from a batch of seeded draws;
confirm the worked example in `start-position.md` §5 decodes to the rows it states;
confirm the documented endpoints `1112223F33444555` and `F555444333222111` validate
and that codes failing each individual rule — wrong rank counts, no `F`, `F` on row
2, wrong length, lowercase-then-normalised — are accepted or rejected as the
document says.

---

### Step 9 — Name a starting position from the runners

Add `--start-position <ID>` to the single-game and batch runners, and make
`--seed` seed start-position generation where it used to seed placement. Show the
position's ID where a game announces its setup, so a position worth replaying can
be read off a played game.

Depends on: Step 8 (IDs to parse and print).

Why it comes here: it is the first point at which the document's stated purpose —
replaying a position, and playing it twice with the sides reversed — is reachable
from this repository.

Verification (manual): two runs of `python -m capture_the_flag.game_runner --white
random --black random --seed 11` open from the same position; a run passing that
position's ID to `--start-position` reproduces the same board with a different
seed; and a malformed ID is refused with a message naming what is wrong with it.

---

### Step 10 — The position carries a ply count

Add a ply count to `CtfPosition`, set to 0 by generation and raised by one on
every applied ply. No rule reads it yet.

Depends on: Step 7 (generation is what initialises it).

Why it comes here: scaffolding for step 11, introduced on its own so that step 11
is a rule change and nothing else. `CtfPosition` is the only channel move
generation has — `legal_plies` takes no arguments — so this is the only place the
first-ply rule can read its condition from.

Verification (improvised): a short script or test playing a fixed sequence of
plies from a generated position and printing the count at each step, confirming it
starts at 0 and rises by exactly one per ply, including on plies that reset the
inactivity counter.

---

### Step 11 — White's first ply is limited to one square

Restrict move generation to one-square plies when the position is the game's
first.

Depends on: Step 10 (the ply count).

Verification (automated): a generated position offers exactly eight plies, all of
distance one; the same board with a non-zero ply count offers two-square plies as
well. `pytest tests/test_moves.py`.

---

### Step 12 — Direction-relative encumbrance

Replace the eight-square encumbrance test with the five-squares-ahead-or-beside
test, evaluated per direction of travel rather than once per piece. Judged from
the square the piece starts on, as before.

Depends on: Step 4 (move generation is already free of lakes), and it follows
step 11 so that each move-generation change is turned on by itself.

Verification (automated): a position where one piece has an enemy behind it and
therefore keeps its two-square move forward, one where an enemy diagonally ahead
removes it, and one where the same piece is unencumbered in one direction and
encumbered in another. `pytest tests/test_moves.py`.

---

### Step 13 — Diagonal attack against every piece, behind an open path

Delete the movable-target restriction so the Flag can be attacked diagonally, and
add the open-path requirement: at least one of the two squares orthogonally
adjacent to both attacker and target must be empty, whichever side occupies them.

Depends on: Step 12 (both are move generation; sequenced so a failure belongs to
one rule).

Verification (automated): the C3 → D4 case from `rules.md` §4.4 is legal with C4
or D3 empty and illegal with both occupied — including when the occupiers are
friendly; a Flag on a diagonal is attackable; an empty diagonal square is never a
destination. `pytest tests/test_moves.py`.

---

### Step 14 — Combat inverts

Higher rank now wins, and the formation bonus rescues the piece exactly one rank
*below* its opponent rather than one above.

Depends on: Step 3 (the Tower branch is already gone, so rank is the only axis
left).

Verification (automated): rank 5 beats rank 4 as attacker and as defender; equal
ranks draw; a rank 4 with an adjacent friendly rank 4 draws against a rank 5
instead of losing; a rank 3 with no formation loses to a rank 5 and to a rank 4.
`pytest tests/test_combat.py`.

---

### Step 15 — Rank reduction

Reduce the surviving piece by one rank as the board is rebuilt in
`transitions.py` — attacker or defender, whichever survives — leaving
`resolve_combat` a pure question about who survives. A draw reduces nothing;
capturing the Flag reduces nothing. Assert rather than branch on the rank-1 floor:
a rank 1 never survives combat, so the case cannot arise.

Depends on: Step 14 (who survives has to be right before what happens to the
survivor is).

Verification (automated + manual): tests that a winning rank 5 stands on the
destination as a rank 4, that a defender surviving a failed attack is reduced in
place, that a mutual loss reduces nothing, and that a Flag capture leaves the
capturing piece at its rank. Then
`python -m capture_the_flag.game_runner --white random --black random --seed 5`
and watch a piece's symbol drop after it wins a fight.

---

### Step 16 — Attrition and mutual attrition

Replace the no-legal-move loss with attrition: a player with no numbered pieces
loses immediately, checked after every ply, with the Flag not counting; and one
ply leaving both players with no numbered pieces is a draw, tested before the
single-sided case. Update the reason vocabulary to `Attrition` and
`Mutual Attrition`. An empty ply list becomes an assertion, not an ending.

Depends on: Step 15 (attrition is reached through combat, so combat must resolve
correctly first).

Verification (automated + manual): tests for a position where one side holds only
its Flag, and for a trade that empties both armies at once. Then
`python -m capture_the_flag.batch_runner -n 200 --seed 2 -o /tmp/ctf-step16` and
confirm the ending-category breakdown reports `Attrition` and no longer reports
`No Legal Move`.

---

### Step 17 — The inactivity limit drops to 40

Change the limit, and the comments and tests that state 50.

Depends on: Step 16 (both are endings; separated so the batch statistics move for
one reason at a time).

Verification (automated): a position at 39 is ongoing and at 40 is a draw.
`pytest tests/test_outcome.py`.

---

### Step 18 — Notation

Add the `=N` mark to the logged ply annotation — read off the resulting board, as
survival already is — so every combat ply marks each of its two squares exactly
once with `x` or `=N`. Add the optional `[StartPosition "…"]` header tag to the
record writer. Restate the plain form as input-only notation in the docstrings
that currently call it a record form.

Depends on: Step 15 (there is nothing to write `=N` about until pieces are
reduced), Step 8 (the ID the header tag carries).

Why it comes here: it is the last rules-visible change, and it is what makes the
records written from this point on replayable by a consumer.

Verification (manual): play a game to a file and read the record — confirm each
combat ply marks both squares exactly once, that a Flag capture is the only ply
marking one square, that the `=N` values fall by one from the rank that started on
the square, and that the header carries `Ruleset "3-0:PRE-RELEASE"` and a
`StartPosition` tag whose ID reproduces the position block.

---

### Step 19 — Sweep the prose and the suite

Bring the comments, docstrings and section references left over from major 2 to
the published documents: `rules.md` section numbers moved, "phase 1"/"phase 2"
language, the vocabulary that describes several boards or several rulesets, and
any test name that still says Battle or Skirmish. Then run the whole suite,
including the slow tests.

Depends on: Steps 1–18.

Why it comes here: prose that describes the old rules is the failure mode
`doc/ruleset/CLAUDE.md` warns about — a stale sentence is how a superseded rule
becomes the apparent ruleset — and it can only be swept once every rule has
actually moved.

Verification (automated): `pytest`, then `pytest -m slow`, then `pyright` and
`ruff check .`, all clean.

---

### Step 20 — README check

Review `README.md` against everything this story changed — the two-phase framing,
placement and the `placements/` folder, the ruleset and edition lists, the record
example, the runner options, and the engine spec — and update it. Run
`/update-readme`, which reviews the branch diff and updates the README if
warranted.

Depends on: Step 19 (the diff has to be complete for the review to be).

Verification (manual): read the updated `README.md` and confirm every command it
shows runs as written, and that nothing it describes has been deleted.

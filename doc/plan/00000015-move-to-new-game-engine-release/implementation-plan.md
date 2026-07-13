# Implementation Plan: Move to the new game-engine-core release

This plan adopts `game-engine-core` at git tag `v0.1.1` and uses its new seams to
close the three gaps recorded in `doc/game-engine-core-requirements.md`. The
v0.1.1 protocol changes are **breaking, with no compatibility shims** (confirmed
from the upstream stories: `GamePosition` gains a required `outcome_reason`,
logging is split into a new `GameLogging` protocol, `StandardGame`/`Tournament`
take a `GameLogging`, and `Tournament`'s `position_factory` is widened to receive
both players). Because there is no shim, the repin and the minimal adaptation
that restores a green build are inseparable and form Step 1; the interesting new
behaviour is layered on top in later steps.

## Step 1 — Repin to v0.1.1 and restore a green build on the new protocols

Implement the dependency bump and the smallest set of conformance changes that
make the project compile, test, and run a batch again on the new release:

- Bump the pinned `game-engine-core` to `@v0.1.1` in **both** the base dependency
  and the `learning` extra (kept identical, in a commit of its own per
  `CONTRIBUTING.md`) and rebuild the container so the new version is installed.
- Give `CtfPosition` the new required `outcome_reason` property, returning a
  short game-specific string for each ending Capture the Flag can reach (flag
  captured, unbreachable flag, inactivity, no progress, no legal move), paralleling
  the branch that `compute_outcome` takes, and `None` while the game is ongoing.
- Introduce a `GameLogging` implementer for Capture the Flag carrying `text_board`
  (moved off the UI) and, for now, a placeholder `ply_annotation` that returns
  `str(ply)`. Slim `CtfGameUI` to the interactive pair (`render_board`,
  `get_next_ply`).
- Update the match construction and any test scaffolding to the new `StandardGame`
  signature (required `game_logging`, optional `game_ui`).

Why it comes here: nothing else can build until the project conforms to the
breaking v0.1.1 protocols, so this is the foundation every later step stands on.
The real reason *strings* are produced here (they are needed for `StandardGame`
to run at all); later steps surface them and enrich the ply annotation.

Verification (automated + manual): the full test suite passes against
`game-engine-core` `v0.1.1`, including a new unit test that `outcome_reason`
returns the correct label for each ending category; then
`python -m capture_the_flag.batch_runner` completes a small batch and writes one
record file per game.

## Step 2 — Migrate batch play onto the shared Tournament runner

Replace the hand-rolled match/batch machinery with the library's `Tournament`,
driven through the widened game-start seam:

- Provide a Capture-the-Flag position factory of the new `(side_one, side_other)`
  shape that consults each player for its secret placement (downcasting to the
  `CtfPlayer` subprotocol for that game-specific state) and returns the assembled
  opening position — respecting the side order the tournament passes.
- Rebuild the batch runner on `Tournament`, using its standings/aggregation
  instead of the bespoke win/draw/loss counters, and reconcile per-game CtF record
  files with the tournament's output: the library's `GameRecord` yields player
  names plus a full `GameResult` (opening board, log) per game rather than our
  former `MatchResult`, so record-file writing sources what it needs from there
  (with the factory the place to capture placements if the record needs them
  beyond the opening board).
- Retire or trim the now-redundant single-match wrapper and hand-rolled tallying.

Why it comes here: it depends on Step 1's `GameLogging` and the conforming
position (the tournament requires both), and it establishes the final
record-production shape that Steps 3 and 4 write into, so their content changes
are made once rather than reworked.

Verification (manual): run a batch through the new runner and confirm it produces
one record file per game plus a standings/summary, with win/draw/loss totals
matching a hand count on a small run; the game-length statistics are unchanged
from Step 1's behaviour.

## Step 3 — Surface the real result reason in records and the batch summary

Now that each `GameResult` carries `result_reason`, put it to use:

- Write the actual ending into each record file's `ResultReason` tag instead of
  the `Unknown` placeholder.
- Add an ending-category breakdown (counts per reason) to the batch summary,
  alongside the existing outcome and length statistics.

Why it comes here: it consumes `result_reason`, which exists from Step 1 and flows
through the Step 2 runner, and it writes into the record shape Step 2 finalised.

Verification (manual): run a batch containing at least a few distinct endings and
confirm each record file's `ResultReason` names the true ending (never `Unknown`)
and the summary's category breakdown sums to the number of games played; covered
by a test asserting the reason reaches the record and the summary.

## Step 4 — Render combat notation for logged plies

Replace the placeholder ply annotation with the real combat notation:

- Implement `ply_annotation` for Capture the Flag using the pre-ply position, the
  ply, and the resulting position to mark the attack result, producing the combat
  forms from `rules.md` Section 4.4 (`A4-A5`, `A4-A5x`, `A4x-A5`, `A4x-A5x`). The
  plain source-destination form remains `str(ply)` and the move's identity;
  only the logged/record string changes.
- Ensure the record's move sequence uses these annotations (it already draws from
  the game log), and update `doc/ruleset/technical-notes.md` and any `rules.md`
  note that currently marks the combat notation "reserved for later use."

Why it comes here: it depends on the `GameLogging` seam from Step 1 and the
finalised record production from Step 2, and it is independent of Step 3, so it
follows naturally as the last behavioural change.

Verification (automated + manual): unit tests covering all four notation forms
(quiet move, successful attack, failed attack, mutual loss) from constructed
positions; then run a batch and confirm record move sequences show combat
notation while the legal-move and ply-uniqueness tests from story 00000004 still
pass.

## Step 5 — Close out the upstream-requirements record

With all three gaps closed, reconcile `doc/game-engine-core-requirements.md`:
mark each of the three items resolved by the v0.1.1 adoption (citing the seam that
resolved it), or remove the document if it no longer serves a purpose now that the
work is done. Confirm no other doc still describes the retired workarounds.

Why it comes here: it can only be truthful once Steps 1–4 have actually landed all
three closures.

Verification (manual): the document reflects the resolved state (or is removed),
and a search for the old workaround language (`ResultReason "Unknown"`,
"reserved for later use", hand-rolled match/batch) turns up nothing stale.

## Step 6 — README accuracy check

Review whether the story's changes affect anything `README.md` describes — the
pinned dependency version, the batch runner's behaviour and output, record
contents, or package layout — and update it if warranted, or confirm no update is
needed. The `/update-readme` command automates this against the branch diff.

Why it comes here: it verifies the repository's top-level documentation against the
completed change set, so it must come last.

Verification (manual): run `/update-readme`; confirm the README accurately
describes the repinned dependency, the tournament-based batch runner, and the
enriched records, with no remaining references to the superseded workarounds.

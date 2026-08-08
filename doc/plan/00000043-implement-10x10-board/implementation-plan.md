# Implementation Plan — Story 43: Implement the 10 × 10 Board (`CLASH`)

Documents lead, code follows (`doc/ruleset/CLAUDE.md`), so Steps 1–3 publish the
ruleset and Steps 4–8 bring the engine's copies to it. Within the code steps the
order is bottom-up: geometry, then the army, then the edition that names both,
then the placement rule that reads the geometry. Nothing is playable as `CLASH`
until Step 7, which is the first step at which `ACTIVE_EDITIONS` carries it.

## Step 1 — Publish the third board and army in `rules.md`

Rewrite `rules.md` for three rulesets rather than two, and move both flag values
across from `proposed-variants.md` in the same step so neither document carries
them twice. The passages to change are tabled in
[`story.md`](story.md) §3: Section 1's "Two rulesets" (and the `#two-rulesets`
anchor Appendix B links to), Section 2.1's lead and its "Both boards" lane
generalization, a third board subsection and a third army subsection, Section 3's
Tower lane restriction restated as a property of the board rather than of
Skirmish, the glossary's *Lane* entry, all three Appendix A tables, and Appendix
B's Active table plus its independent-minors paragraph. Section 1's
recommendation keeps Skirmish as the starting point and places Clash as the
middle game.

Depends on: nothing. This is the definition every later step copies from.

Verification (manual): Read the changed sections and confirm —
- No sentence claims a property of "both boards" that Clash lacks; in particular
  Section 2.1 no longer promises a lane at each far edge.
- Section 2.1's Clash subsection gives 3 home / 1 buffer / 2 lake / 1 buffer / 3
  home, the lake pattern `L O O L O O L L L O`, and blocks of 1 × 2, 1 × 2 and
  3 × 2; the glossary lists Clash's three lanes as B–C, E–F and J.
- Appendix B's Active table has three rows and `2-0:CLASH` sets all three flags
  explicitly.
- Every in-document link still resolves, the renamed Section 1 anchor included
  (grep the file for `#two-rulesets` and confirm no stale target remains).
- `proposed-variants.md` no longer contains either graduated entry, and nothing
  else in that file moved.

## Step 2 — Restate the squeeze argument in `technical-notes.md`

Replace the "2 × 2 lake blocks all aligned to the same two rows" premise with the
one that actually holds — every lake row shares a single column pattern, so two
adjacent lake columns are lake in both rows and the diagonal's own source or
destination is a lake. Note that this is structural in `BoardLayout` rather than
a property of the published values, update "unreachable on both published
layouts" to all three, and state what a future layout would need (per-row lake
patterns, which the type cannot currently express). The reserved decision itself
does not change and `rules.md` still says nothing about the squeeze. Also update
this file's Active-editions list, and correct the same stale count in
`proposed-variants.md`'s `open_path` entry.

Depends on: Step 1 (the third layout must be published before this file can call
it a published layout).

Verification (improvised, then superseded): Run a short throwaway script that
enumerates every diagonal on all three lake patterns — Clash's hardcoded, since
the layout does not reach `board.py` until Step 4 — and reports any case with
both flanks lake and both endpoints open. Confirm it reports none for all three,
which is what the restated premise predicts. Step 4 replaces this with a
permanent test over the layout registry; the script is not committed.

## Step 3 — Changelog, project context, and the engine-spec example

Add the changelog entry for `2-0:CLASH` (newest first, story 43, the date),
covering the four points [`story.md`](story.md) §7 requires: a third ruleset with
Battle and Skirmish untouched, the notation unaffected, three Active editions
with unrelated minors, and the board's left-right asymmetry. Update
`doc/ruleset/CLAUDE.md` from two active editions to three, keeping its warning
about not tidying minors into step. Add `ENG_NN_3/asymmetric_100` to
`doc/neuralnetwork/eng-nn-3.md`'s list of qualified spec names — an example, not
a contract change.

Depends on: Steps 1–2 (the changelog summarises what those published).

Verification (manual): Read the changelog entry against
[`story.md`](story.md) §7 and confirm each of the four points is stated; confirm
`doc/ruleset/CLAUDE.md` names three active editions; confirm `eng-nn-3.md` still
describes one spec with three qualified names rather than implying a new spec.

## Step 4 — The `asymmetric_100` layout

Add the layout value to `board.py` and register it in `BOARD_LAYOUTS`. Extend
`tests/test_board.py` with the coverage it already gives `STANDARD_144` — home
zone sizes, the lake and lane square counts, lakes confined to the lake rows,
home zones disjoint from lakes, buffer rows carrying neither — and add the
squeeze guard written over `BOARD_LAYOUTS` rather than over one layout, so a
fourth layout inherits it.

Depends on: Step 1 (the layout's definition) and Step 2 (the property the guard
asserts).

Verification (automated): `pytest tests/test_board.py` passes, including the new
assertions. Confirm by deliberately breaking one lake column in a scratch copy
that the squeeze guard can fail — a guard that cannot fail is not a guard.

## Step 5 — Move generation on the wider lake block

No source change: this step confirms the existing generic move generation handles
geometry neither published board has. Add cases to `tests/test_moves.py` on the
new layout covering a diagonal attack past the corner of the 3-wide lake block
(G–I) and an orthogonal approach into the single-column J lane.

Depends on: Step 4 (the layout must exist to build a position on).

Verification (automated): `pytest tests/test_moves.py` passes. If a new case
fails, the bug is in move generation's assumptions about block width, not in the
test — do not adjust the expectation without deciding which is right.

## Step 6 — The `standard_clash` army

Add the composition to `pieces.py` and register it in `ARMY_COMPOSITIONS`, with
test coverage of its size and of Militia's absence resolving to a count of zero
rather than an error.

Depends on: Step 1 (the army's definition). Independent of Steps 4–5.

Verification (automated): `pytest tests/test_pieces.py` passes.

## Step 7 — Publish edition `2-0:CLASH`

Extend `record.py`: both flag registries gain their new value label with defaults
unchanged, `EDITIONS` gains the `2-0:CLASH` row spelling out all three flags, and
`ACTIVE_EDITIONS` gains the id. Update `tests/test_record.py`'s per-edition
distribution map — it asserts set equality against `ACTIVE_EDITIONS` and will
fail until Clash's published army is written out, which is the check working.
Add the `tests/test_game_setup.py` cases: `setup_for_ruleset("CLASH")` stamps
`2-0:CLASH` and resolves to the layout, army and `spacing_only`, and
`forbidden_tower_squares` is empty on Clash under *both* `TOWER_PLACEMENT`
values.

Depends on: Steps 4 and 6 — an Active edition naming a layout or army this build
cannot resolve is a build that fails at setup.

Verification (automated): `pytest tests/test_record.py tests/test_game_setup.py`
passes, and `--ruleset` now offers CLASH in the runners' help output without any
change to the runners (`python -m capture_the_flag.game_runner --help`).

## Step 8 — Tower placement feasibility on the new board

Extend `placement.py`'s per-setup non-stalling derivation with the Clash case: 4
Towers into 30 candidates, the lane rule inert so nothing is subtracted, at least
3 candidates remaining for the last Tower. Add Clash coverage to
`tests/test_placement.py` alongside the Skirmish cases it already parametrises.

Depends on: Step 7 (the tests resolve the setup by ruleset name).

Verification (automated): `pytest tests/test_placement.py` passes, including
repeated random placements on Clash for both sides.

## Step 9 — Play a Clash game end to end

No source change. Exercise the whole path — placement, move generation,
rendering, and record stamping — on the new board.

Depends on: Step 8.

Verification (manual): Run
`python -m capture_the_flag.game_runner --white random --black random --ruleset clash --seed 1`
and confirm the rendered board is 10 wide with columns A–J, the lakes appear at
A, D and G–I across two rows, and the game reaches a legal end. Then run
`python -m capture_the_flag.batch_runner -n 2 --ruleset clash -o <scratch-dir>`
and confirm a written record's `[Ruleset "..."]` tag reads exactly `2-0:CLASH`
with no deviating flags, and its position block is 10 columns wide.

## Step 10 — Full suite and static checks

No source change unless something below fails.

Depends on: Step 9.

Verification (automated): `pytest` passes whole; `pyright` reports no errors;
`ruff check .` passes.

## Step 11 — README check

`README.md` describes two published rulesets, documents `--ruleset
battle|skirmish`, and states the placement-file shapes for Battle and Skirmish —
all three are stale once Clash is Active, so this step expects a change rather
than a confirmation.

Depends on: Step 10 (the diff must be complete to check against).

Verification (manual): Run `/update-readme` and confirm the resulting `README.md`
names three rulesets, offers `clash` in the `--ruleset` documentation, and gives
Clash's placement-file shape (3 rows of 10) alongside the other two.

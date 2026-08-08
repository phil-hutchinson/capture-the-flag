# Story 43: Implement the 10 × 10 Board — the `CLASH` Ruleset

## Summary

Implement the board and army [story 41](../00000041-add-10x10-board-proposed-rule/story.md)
proposed, and publish them as a third live ruleset.

1. **`BOARD_LAYOUT = asymmetric_100` and `ARMY_COMPOSITION = standard_clash`
   graduate** from [`proposed-variants.md`](../../ruleset/proposed-variants.md)
   to `rules.md` Appendix A, and become real geometry and a real roster in
   `board.py` and `pieces.py`.
2. **A third edition is published — `2-0:CLASH`** — and joins the Active table
   and `ACTIVE_EDITIONS`. `BATTLE` and `SKIRMISH` do not move.
3. **`rules.md` stops being written as a document about two boards.** Several
   passages generalize over "both boards" in ways that are false on Clash, and
   one of them — the lane description in Section 2.1 — is false in a way a player
   would act on.
4. **`technical-notes.md`'s squeeze argument is restated on its real premise.**
   The reserved decision stays reserved and stays unreachable, but the reason
   given for it currently cites a property of the two published layouts rather
   than the property that actually does the work.

Story 41 opened no implementing branch, by design; this is that branch, and its
merge is what moves both values across under `proposed-variants.md`'s graduation
rule.

## Context: the machinery already exists

This story is a much smaller job than [story 37](../00000037-implement-version-2-rules/story.md)
was, and deliberately so. Story 37 made the board, the army, and the Tower rule
into run-time configuration; everything downstream of that — placement, move
generation, the text UI, the tensor contract, the checkpoint stamp, the runners'
`--ruleset` argument — already takes a `GameSetup` or derives from
`ACTIVE_EDITIONS`. **Adding a third ruleset is adding data to three tables.**

Two consequences worth stating up front, because they are what keeps this story
small:

- **Nothing in the engine needs a new parameter.** If implementing Clash requires
  threading a new value through a signature, something is wrong with the change
  rather than with the board — the seams story 37 built are the ones to use.
- **The work is concentrated in the documents**, and specifically in prose that
  was correct when exactly two boards existed. A third board is the first real
  test of whether `rules.md` describes rules or describes Battle and Skirmish.

## Specification

### 1. Edition `2-0:CLASH`

| | |
|---|---|
| `BOARD_LAYOUT` | `asymmetric_100` |
| `ARMY_COMPOSITION` | `standard_clash` |
| `TOWER_PLACEMENT` | `spacing_only` |

**Major 2, because the notation does not break.** Board size stopped forcing a
major bump at major 2 — that is what that bump was spent on — and a 10 × 10 grid
is expressible in the existing notation exactly as it stands: columns A–J, rows
1–10, and a position block from which the dimensions and the lake layout are both
recoverable. Clash shares this rules text with Battle and Skirmish, which is what
sharing a major asserts.

**Minor 0, because minor is namespaced per ruleset.** `2-0:CLASH` is the first
published Clash edition; its minor says nothing about `2-0:BATTLE`'s or
`2-1:SKIRMISH`'s, and the three are not meant to be brought into step.

**`TOWER_PLACEMENT = spacing_only`, and `spacing_and_lanes` would be inert
anyway.** `asymmetric_100` has a buffer row between each home zone and the lake
rows, so no home square is orthogonally adjacent to a lane square and the flag
closes nothing — confirmed against the geometry, not assumed: the lane-adjacent
set on this layout reaches into rows 4 and 7 only, both buffer. Clash is the
second board on which the flag is legal to select and does nothing, and setting
it on would spend an edition for no behavioral change, which is the same argument
that kept `2-0:BATTLE` where it is.

**Battle and Skirmish do not move, and this is not a rules change for them.**
`rules.md` gains a third board and a third army and loses some two-board phrasing,
but every game legal under the old wording is still legal and resolves the same
way — the behavioral test `doc/ruleset/CLAUDE.md` sets for a clarification. A
changelog entry is still mandatory: it is what publishes `2-0:CLASH` to the
front-end application and to anyone tracking the rules.

**`DEFAULT_EDITION` stays `2-0:BATTLE`**, and its stated reason survives intact —
both `BOARD_LAYOUT` and `ARMY_COMPOSITION` keep their existing defaults, so Battle
is still what the rules resolve to in the absence of a choice. Adding a third
Active edition must not turn the default into an arbitrary pick among three.

### 2. The two flag values, as published

Content is [story 41](../00000041-add-10x10-board-proposed-rule/story.md)'s
Specification section; it is transcribed rather than redesigned. Restated here
only where the implementation needs a fact story 41 left implicit.

#### `BOARD_LAYOUT = asymmetric_100`

| | |
|---|---|
| Grid | 10 × 10 |
| Rows | 3 home / 1 buffer / 2 lake / 1 buffer / 3 home |
| White home | rows 1–3 · Black home rows 8–10 |
| Buffer | rows 4 and 7 |
| Lake rows | 5 and 6 |
| Home zone | 3 × 10 = 30 squares |

Lake pattern, shared by both lake rows (`L` = lake, `O` = open):

| Column | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| | L | O | O | L | O | O | L | L | L | O |

Three lake blocks 1, 1 and 3 columns wide; three lanes — B–C, E–F, and J. **A
lake sits at one board edge and a lane at the other**, which neither published
layout does, and the pattern is not its own mirror image. 10 lake squares and 10
open squares in the 2 × 10 lake zone, the same 50:50 split both published layouts
have.

#### `ARMY_COMPOSITION = standard_clash`

3 each of ranks 1–5, 4 Towers, 1 Flag — **20 pieces** into 30 home squares.
Militia (rank 6) does not appear.

**A rank the army does not field needs no code.** `ArmyComposition.count` already
returns 0 for an omitted type, and the tensor contract already carries all six
rank planes for every composition — the evaluator gives an unfielded rank's
quantity plane a divisor of 0 and a constant 0.0, which `standard_skirmish`
already exercises for two ranks. Clash is a third composition through machinery
that is already general.

#### Naming: the labels become permanent at merge

`asymmetric_100` and `standard_clash` are `proposed-variants.md` entries today
and can still be renamed; on merge they reach Appendix A and can never be
renamed or redefined. Keep both as proposed. `asymmetric_100` names the property
that actually distinguishes this layout from its siblings rather than its size
alone, which is the right thing for a label to carry given a fourth 10 × 10
layout could be published later; `standard_clash` matches the `standard_*`
convention its two siblings set. This paragraph exists so the decision is made
knowingly rather than by default.

### 3. `rules.md` stops generalizing over two boards

This is the substantive documentation work. Each of these is a claim that is
true of Battle and Skirmish and false, or incomplete, on Clash.

| Location | Today | Required |
|---|---|---|
| §1 "Two rulesets" | "played in two forms", two bullets | Three forms, three bullets. The heading renames, so the `#two-rulesets` anchor moves — Appendix B links to it and must move with it |
| §2.1 lead | "Both boards are square…" | Three boards; all three are still square, so only the count changes |
| §2.1 "Both boards" | "the lakes leave single-column lanes at the two far edges and double-column lanes through the interior" | **False on Clash**: column A is a lake and column J is a single-column lane. Restate per board, or drop the generalization and let each board's own subsection carry its lanes |
| §2.1 | two board subsections | A third, `Clash — 10 × 10`, with the row table, the lake pattern, and its three lake blocks named as 1 × 2, 1 × 2 and 3 × 2 |
| §2.2 | two army subsections | A third, `Clash — 20 pieces`, and the note that Clash uses the top five ranks (Militia absent) |
| §3, Tower lane rule | "In Skirmish… This does not apply in Battle" | The rule is geometric, not per-ruleset: it closes squares only where a home zone abuts a lake row. State it that way and note that Clash, like Battle, has a buffer row — otherwise the next board added has to amend this sentence again |
| §7 glossary, *Lane* | enumerates Battle's four and Skirmish's three | Add Clash's three: B–C, E–F, J |
| Appendix A, `BOARD_LAYOUT` | two-row table | Third row; the note that a value names a *complete* layout carries over unchanged |
| Appendix A, `ARMY_COMPOSITION` | two-row table | Third row |
| Appendix A, `TOWER_PLACEMENT` | "squares closed" table, two rows | Third row: `asymmetric_100` → none. The prose "a real restriction on Skirmish and no restriction whatever on Battle" becomes a statement about buffer rows |
| Appendix B, Active | two rows | `2-0:CLASH`; and "the two minor numbers advance independently" becomes three, with Clash at minor 0 as its own first edition rather than as agreement with Battle |

**Where Clash sits in the recommendation.** §1 currently tells a new player to
start with Skirmish, and Appendix B repeats it. **Skirmish stays the
recommendation.** Clash is described as the middle game — a larger board and a
fifth rank, but the same 3-per-rank shape and a home zone with real placement
choice. Making this call in the story rather than leaving it to whoever edits the
section is deliberate: "which one should I play" is the first question the
section answers, and three options make it a real question for the first time.

### 4. The squeeze argument needs its real premise

`technical-notes.md` reserves a decision for the first layout on which a diagonal
attack can have **both flanking squares lakes** with source and destination open,
and explains that this is unreachable today because "with 2 × 2 lake blocks all
aligned to the same two rows, that forces the source and destination squares to
be lakes as well."

**The conclusion holds on Clash — verified, not assumed.** Enumerating every
diagonal on `asymmetric_100` produces no squeeze case. But the *stated* reason
does not survive: Clash's lake blocks are 1, 1 and 3 columns wide, so an argument
resting on 2 × 2 blocks would predict the squeeze is now reachable, and it is not.

The premise that actually does the work is that **every lake row shares one
column pattern**. Two lake columns adjacent to each other are therefore lake in
*both* rows, which makes the diagonal's source or destination a lake and rules the
attack out before the flanking squares matter. Block width is irrelevant. This is
also a structural property of `BoardLayout` rather than a coincidence of the
published values — `lake_pattern` is one per-column tuple shared by all lake
rows, so no layout expressible in the current type can reach the squeeze at all.

Restate the section on that premise, update "unreachable on both published
layouts" to all three, and say plainly what a future layout would have to do to
make it reachable — per-row lake patterns, which the type does not currently
support. The reserved decision itself does not change and `rules.md` still says
nothing about the squeeze.

**Also fix the same stale count in `proposed-variants.md`**, where the
`DIAGONAL_ATTACKABLE` / `open_path` entry says "currently unreachable on both
published boards." That file carries no promises, but the sentence is load-bearing
for whoever picks the proposal up.

### 5. Code

| File | Change |
|---|---|
| `board.py` | `ASYMMETRIC_100: BoardLayout`, and its entry in `BOARD_LAYOUTS` |
| `pieces.py` | `STANDARD_CLASH: ArmyComposition`, and its entry in `ARMY_COMPOSITIONS` |
| `record.py` | `RULE_FLAGS`: both value tuples gain a label, both defaults unchanged. `EDITIONS`: the `2-0:CLASH` row. `ACTIVE_EDITIONS`: gains `2-0:CLASH` |
| `placement.py` | the per-setup Tower feasibility derivation gains its Clash case |

**Nothing else.** `ACTIVE_RULESETS`, `DEFAULT_RULESET`, the runners' `--ruleset`
choices, `resolve_setup`, `TensorLayout`, and the checkpoint compatibility check
all derive from the tables above. A change needed anywhere else is a signal that
something reads geometry from a module constant, which
`doc/ruleset/CLAUDE.md` already names as a bug.

**The feasibility comment is an argument, not a note.** `placement.py`'s random
generator carries a per-setup derivation that Tower placement never stalls, one
case per board and Tower rule. Clash's: 4 Towers into 30 candidates with the lane
rule inert, so no subtraction; each placed Tower removes at most its nine-square
closed neighbourhood, leaving at least 30 − 27 = 3 candidates for the fourth. Add
the case; do not generalize the existing ones away.

**No `CLASH_SETUP` constant.** `BATTLE_SETUP` exists because a runner needs a
default and there is exactly one default. A per-ruleset constant for each of the
three would be three names for what `setup_for_ruleset` already returns.

**`ENG_NN_3` is unchanged.** The spec is stated parametrically in the board and
roster, and the artifact-qualifying name `ENG_NN_3/asymmetric_100` arises from
`layout_id` with no spec change. `eng-nn-3.md` gives `ENG_NN_3/standard_144` and
`ENG_NN_3/standard_64` as its examples and should mention the third, but the
contract does not move — a checkpoint trained on one board still cannot be seated
in a game on another, and that check is per-run rather than per-build.

### 6. Tests

- **`test_record.py`'s per-edition distribution map gains `2-0:CLASH`.** It
  asserts set equality against `ACTIVE_EDITIONS`, so it fails the moment the
  edition is published and passes only when the published army is written out —
  which is the prompt working as intended, not a test to relax.
- **`test_board.py`** covers the new layout the way it covers `STANDARD_144`: 30
  home squares per zone, 10 lake and 10 lane squares, lakes confined to rows 5–6,
  home zones disjoint from lakes, and buffer rows 4 and 7 carrying neither.
- **A squeeze guard over `BOARD_LAYOUTS`, not over one board.** Assert that no
  registered layout admits a diagonal with both flanks lake and both endpoints
  open. Written over the registry, a fourth layout inherits the check and cannot
  silently re-open the reserved decision — which is exactly the failure mode
  §4 is about.
- **`test_game_setup.py`**: `setup_for_ruleset("CLASH")` stamps `2-0:CLASH` and
  resolves to the layout, the army, and `spacing_only`; and
  `forbidden_tower_squares` is empty on Clash under *both* `TOWER_PLACEMENT`
  values, pinning the inertness claim rather than leaving it to the prose.
- **`test_placement.py`** exercises `random_placement` on Clash across seeds for
  both sides, as it already does for Skirmish — the feasibility argument in §5 is
  what this checks empirically.
- **`test_moves.py`** gains at least one diagonal case against the 3-wide lake
  block (G–I). A skirt past the corner of a wider-than-2 lake is geometry neither
  published board has, and it is the case most likely to expose an accidental
  assumption about block width.

### 7. What the changelog entry must say

The front-end player application tracks the changelog and prototypes against it,
which is the reason story 41 exists at all. The entry must be explicit that:

- **A third ruleset is published**, `2-0:CLASH`, and Battle and Skirmish are
  untouched — no consumer is required to do anything unless it wants Clash.
- **The notation is unaffected.** A 10 × 10 board was already expressible; a
  consumer that reads dimensions from the position block, as major 2 requires,
  reads Clash records with no change.
- **Three Active editions now exist with three unrelated minors**, and a consumer
  must not infer a relationship between them.
- The board is **not left-right symmetric**, which a renderer that mirrors the
  lake pattern to save a few characters will get wrong.

## Documents to change

| Document | Change |
|---|---|
| `doc/ruleset/rules.md` | §1, §2.1, §2.2, §3, §7 glossary, Appendix A (three entries), Appendix B Active — see §3 above |
| `doc/ruleset/technical-notes.md` | the squeeze argument restated on its real premise; the Active-edition list; `ENG_NN_3` qualified-name examples if listed there |
| `doc/ruleset/changelog.md` | one entry for `2-0:CLASH`, newest first, recording story 43 and the date |
| `doc/ruleset/proposed-variants.md` | both graduated entries removed; the stale "both published boards" in the `open_path` entry corrected |
| `doc/ruleset/CLAUDE.md` | "There are two active editions" becomes three, with the same warning about not tidying minors into step |
| `doc/neuralnetwork/eng-nn-3.md` | the third qualified spec name in its examples; the contract does not change |
| `README.md` | "Two rulesets are published" and the `--ruleset battle|skirmish` line; the placement-file shapes paragraph names Battle's and Skirmish's row/column counts |

## Out of scope

- **Committed placement files for Clash.** `placements/*.txt` are Battle-shaped
  and stay valid for `2-0:BATTLE`; a file's shape identifies its board, and
  3 × 10 would be distinguishable from both existing files, but nothing needs one
  to play Clash.
- **Training a Clash network, or any transfer question** between the three
  boards. Whether weights move between rulesets is still unexamined and still
  refused at load time.
- **Revisiting the piece counts.** 3 each of ranks 1–5 and 4 Towers is published
  as proposed. If playtesting moves them it costs a new `ARMY_COMPOSITION` value
  and a new edition, not an edit to `standard_clash`.
- **Moving `TOWER_PLACEMENT` for Clash**, now or in response to playtesting.
- **Tuning the inactivity counter per ruleset.** Still 50 plies on all three;
  a third board is a third confound, not a reason to move it.
- **A fourth board or army value**, and any change to the lake pattern proposed
  in story 41.

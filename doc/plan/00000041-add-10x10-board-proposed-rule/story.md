# Story 41: Add 10×10 Board ("Clash") Proposed Rule

## Summary

Propose a new board size — 10 × 10, to sit alongside Skirmish (8 × 8) and Battle
(12 × 12) as a third ruleset called **Clash** — entered into
[`doc/ruleset/proposed-variants.md`](../../ruleset/proposed-variants.md) as two
new candidate values on the already-published `BOARD_LAYOUT` and
`ARMY_COMPOSITION` flags.

1. **`BOARD_LAYOUT = asymmetric_100`** — a 10 × 10 grid, 3 home rows / 1 buffer /
   2 lake rows / 1 buffer / 3 home rows, with a lake pattern that is not
   left-right mirror-symmetric (unlike `standard_144` and `standard_64`).
2. **`ARMY_COMPOSITION = standard_clash`** — 3 each of ranks 1–5, 4 Towers, 1
   Flag (20 pieces), fitting the 30-square home zone.

**This story is documentation only.** No code changes, no `RULE_FLAGS` entry, no
`rules.md` edit, no new edition. Per `proposed-variants.md`'s graduation rule, a
value reaches Appendix A only when its implementing branch merges — this story
opens no such branch. The two entries exist so the companion front-end player
application can prototype the board for human playtesting, and so the values are
argued about, before any decision is made to implement them here.

## Motivation

`BOARD_LAYOUT` and `ARMY_COMPOSITION` are unusual among proposals in that they
are already-published, permanent flags (`rules.md` Appendix A) — this is not a
brand-new flag identifier like story 39's `DIAGONAL_ATTACKABLE`, but a proposal
to add a **third value** to each of two existing flags. `proposed-variants.md`'s
graduation model works the same way regardless: a value sits here, provisional,
until the branch that implements it merges.

Clash is meant to explore two things at once:

- **A third army-size point** between Skirmish (16 pieces, 8 × 8) and Battle (25
  pieces, 12 × 12), using the top 5 ranks rather than 4 or 6 — a data point
  between the two published rank orders.
- **A non-mirror-symmetric lake pattern.** Both published layouts use lake
  patterns that are left-right mirror images of themselves (`standard_144`:
  `O LL OO LL OO LL O`; `standard_64`: `O LL OO LL O`), built from uniform
  2-wide lake blocks. Clash deliberately breaks both properties: its lake
  blocks are 1, 1, and 3 columns wide, and the pattern is not a mirror image of
  itself — a lake sits at one board edge (column A) while a lane sits at the
  other (column J). This is a genuinely different shape of board, not just a
  different size, and worth having a real proposal to prototype against.

**Why the asymmetry is not a fairness problem.** Column letters are fixed to
physical left-right position and do not flip per player (`rules.md`
[Section 4.4](../../ruleset/rules.md#44-recording-a-move)); only row numbering
is relative to each player's back rank. Both home zones sit the same distance
from the same lake rows, with a buffer row on each side — the board is
symmetric top-to-bottom, which is what placement fairness actually depends on.
The left-right asymmetry in the lake pattern applies identically to both
players' approach to it, so neither player's crossing options are worse than
the other's. It does, as a side effect, let this board pre-test a less
homogeneous lake pattern than either published layout uses, ahead of any
decision to build one into a published edition.

## Specification

### `BOARD_LAYOUT` — new candidate value `asymmetric_100`

**Existing flag**, published in `rules.md` Appendix A with values
`standard_144` | `standard_64`, default `standard_144`. This proposes a third
value; the default is unchanged, so no existing edition is affected.

| | |
|---|---|
| Grid | 10 × 10 |
| Rows | 3 home / 1 buffer / 2 lake / 1 buffer / 3 home |
| Home zone | 3 rows × 10 columns = 30 squares |

Lake pattern, identical in both lake rows, read left to right across all 10
columns (`O` = open, `L` = lake):

```
L O O L O O L L L O
```

| Column | A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|---|
| | L | O | O | L | O | O | L | L | L | O |

This forms three lake blocks of **non-uniform width** — 1 column (A), 1 column
(D), and 3 columns (G–I) — and three lanes: a 2-column lane (B–C), a 2-column
lane (E–F), and a 1-column lane at the J edge only. **Column A has no lane**:
unlike both published layouts, which are open at both edges, Clash has a lake
at one edge and a lane at the other. Lake and open squares split evenly within
the lake rows — 10 lake squares and 10 open squares across the 2 × 10 lake
zone — matching the 50:50 ratio both published layouts also use, just
distributed unevenly across the row instead of in uniform 2-wide blocks.

**The reserved "squeeze" case stays unreachable.** `technical-notes.md`'s
["Diagonal attacks and lakes"](../../ruleset/technical-notes.md#diagonal-attacks-and-lakes--a-decision-reserved-for-future-layouts)
section reserves a decision for the first layout that makes a diagonal attack's
two flanking squares both lakes while its source and destination stay open —
and warns that breaking the 2-wide, edge-to-edge alignment of the lakes (as
`asymmetric_100`'s 1- and 3-wide blocks do) is exactly the kind of change that
could make it reachable. It does not, here: because both lake rows share the
identical column pattern, any two columns that are both lake columns and
adjacent to each other are lake in *both* rows, which makes the diagonal's
source or destination a lake too and rules the attack out before the squeeze
question arises — the same reasoning that keeps it unreachable on
`standard_144` and `standard_64`, and it does not depend on the lake blocks
being a uniform width. `asymmetric_100` does not need `technical-notes.md`'s
reserved decision, and does not disturb it.

**Why:** Tests a genuinely non-uniform, non-mirror-symmetric lake pattern for
human playtesting, and a board size between Skirmish and Battle, before any
decision is made on whether either property is worth building into a published
edition.

**Status:** proposed.

### `ARMY_COMPOSITION` — new candidate value `standard_clash`

**Existing flag**, published in `rules.md` Appendix A with values
`standard_battle` | `standard_skirmish`, default `standard_battle`. This
proposes a third value; the default is unchanged.

| Rank | Piece | Qty |
|---|---|---|
| 1 | Master-of-Arms | 3 |
| 2 | Champion | 3 |
| 3 | Knight | 3 |
| 4 | Halberdier | 3 |
| 5 | Foot Soldier | 3 |
| — | Tower | 4 |
| — | Flag | 1 |
| | **Total** | **20** |

Uses the top 5 ranks (Militia, rank 6, does not appear — the one rank Battle
has and Clash does not). Paired with `asymmetric_100`'s 30-square home zone,
20 pieces is a 66.7% fill — close to Skirmish's 67% (16 in 24) and denser than
Battle's 52% (25 in 48).

**Why:** A third army-size point, between Skirmish's 4 ranks and Battle's 6,
for the same playtesting purpose as the board.

**Status:** proposed.

### Together: the `CLASH` ruleset

These two values are a co-designed pair — `asymmetric_100` and
`standard_clash` are only meaningful in combination, exactly as `standard_64`
and `standard_skirmish` are. If both are ever implemented, they would name a
new ruleset, **Clash**, alongside Skirmish and Battle.

**No `TOWER_PLACEMENT` value is needed.** `spacing_and_lanes` exists because
Skirmish's home zones abut the lake rows directly, putting a home square in
the mouth of every lane (`technical-notes.md`, "the geometric definition").
`asymmetric_100` has a buffer row between each home zone and the lake rows,
exactly as `standard_144` does, so no home square is ever in a lane's mouth —
the existing default, `spacing_only`, is the only sensible setting, same as
Battle. `spacing_and_lanes` would be legal to select but inert, as it already
is on `standard_144`.

## Documents to change

| Document | Change |
|---|---|
| `doc/ruleset/proposed-variants.md` | Add both entries under "Proposals" |

No other document changes. `rules.md`, `technical-notes.md`, `changelog.md`,
`CLAUDE.md`, `record.py`, `board.py`, and `pieces.py` are all untouched by this
story.

## Out of scope

- **Implementing either value's behavior.** No change to `BOARD_LAYOUTS`,
  `ARMY_COMPOSITIONS`, or any engine code.
- **Deciding whether Clash should ship, or whether either value should ship
  independently of the other.** This story only makes the proposal available
  to argue about and prototype against.
- **Choosing 20 as final, or any other count.** The specific rank selection
  (top 5) and Tower count (4) are a starting proposal, not a settled design.
- **A fourth `BOARD_LAYOUT`/`ARMY_COMPOSITION` pairing beyond what's proposed
  here**, and any interaction analysis beyond the squeeze check and the
  `TOWER_PLACEMENT` note above.

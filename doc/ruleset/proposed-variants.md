# Capture the Flag — Proposed Variants

**This document carries no promises.** Entries here are added, reworked, and
deleted freely. Nothing in it is published, nothing in it is permanent, and
nothing outside this file may depend on it — not the engine, not a record, not a
trained network, not the front-end player application. A proposal that is
abandoned is simply deleted, leaving no trace and breaking nothing.

Contrast [`rules.md`](rules.md) Appendix A, the **Variants** appendix, which is
the opposite in every respect: append-only, and its flag names and value labels
permanent once written.

**Terminology.** This file uses **rule flag**, the project's term (root
`CLAUDE.md`). `rules.md` says **variant** for the same thing, because it is
written for players — the same one-off audience exception that makes it say
"move" where everything else says "ply." One rule flag = one variant.

## The graduation rule

A rule flag moves from this file to Appendix A **when its implementing branch
merges** — not when it is designed, not when it is agreed to be a good idea, and
not while its implementation sits in an unmerged branch.

This is what makes the sandbox safe. A flag can be specified here in full detail,
reviewed, and iterated on while its implementation is still in progress, without
any of that provisional wording landing in a document that promises permanence.
An experiment that does not work out deletes its entry here and violates no
promise. Only a merge — the point at which the engine actually implements the
flag and can stamp it into a record — moves an entry across.

At graduation, the entry is rewritten for Appendix A's audience: player-facing
prose, no implementation detail, no rationale. Its identifier and value labels
carry across unchanged and become permanent at that moment, so those are worth
settling here rather than at the last minute.

## Proposal format

An entry should carry enough to be argued about and enough to be implemented
from:

- **Identifier** and its **value labels** — becoming permanent on graduation, so
  choose them as if they already were.
- **Default** — which value preserves current behavior. Every flag has one; a
  proposal whose default would change existing play is not a flag proposal, it is
  a rules change (see [`technical-notes.md`](technical-notes.md)).
- **What each non-default value does**, in enough detail to implement.
- **Why** — what the variant is meant to test or improve. This is the part
  Appendix A will not carry, so this file is the only place it is recorded.
- **Status** — free-form: under discussion, being prototyped, branch open,
  parked.

## Recently graduated

`TOWER_PLACEMENT` was proposed here and **graduated to
[`rules.md`](rules.md) Appendix A** with story 00000037, which published
`2-1:SKIRMISH` setting it to `spacing_and_lanes`. Its identifier and value labels
are permanent from that point; the reasoning behind it, and the connectivity rule
rejected in its favour, moved to
[`technical-notes.md`](technical-notes.md).

## Proposals

### `DIAGONAL_ATTACKABLE`

**Values:** `movable_only` (default) | `all`

Governs which enemy pieces are legal targets of a diagonal attack.

| Value | Behavior |
|---|---|
| `movable_only` | Unchanged from today: only a numbered (movable) piece may be attacked diagonally. Towers and the Flag may only be attacked orthogonally. |
| `all` | A Tower or the Flag may also be attacked diagonally, exactly as a numbered piece can be today. Combat resolves by the same rank/formation rules regardless of target type; a diagonal Tower attack is still a partial sacrifice, as any Tower attack is. |

**Why:** Tests whether removing the Flag's and Towers' orthogonal-only immunity
changes the balance of the tollbooth dynamic `technical-notes.md` describes for
`TOWER_PLACEMENT`, and whether the Flag's defensive perimeter is better served
by staying orthogonal-only or opened up.

**Status:** proposed.

### `DIAGONAL_ATTACK_PATH`

**Values:** `always` (default) | `open_path`

Governs whether a diagonal attack requires a clear path between attacker and
target, independent of which pieces `DIAGONAL_ATTACKABLE` allows as targets.

| Value | Behavior |
|---|---|
| `always` | Unchanged from today: a diagonal attack is legal whenever the target square is diagonally adjacent and holds a legal target, regardless of what stands on the two squares flanking that diagonal. |
| `open_path` | A diagonal attack additionally requires that **at least one** of the two squares flanking the diagonal (the two squares orthogonally adjacent to both attacker and target) be unoccupied — by a piece of either side — and not a lake. If both flanking squares are lakes, occupied, or some combination of the two, the diagonal attack is illegal. |

**Why:** Tests a stricter, path-based reading of the diagonal attack, closer in
spirit to how a lake or a piece already blocks orthogonal movement, against the
current adjacency-only rule.

**Interaction with the existing lake-corner note.** `technical-notes.md`
already distinguishes the *skirt* (one flanking square a lake, the other open —
legal today) from the *squeeze* (both flanking squares lakes — decided illegal,
though currently unreachable on both published boards). `open_path`'s "at least
one flank open" reading is consistent with both of those existing decisions: a
skirt still has an open flank and stays legal, and a squeeze has no open flank
and stays illegal — `open_path` generalizes the squeeze decision to also cover
flanks blocked by pieces, not just lakes.

**Status:** proposed.

### `BOARD_LAYOUT` — new value `asymmetric_100`

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
unlike both published layouts, which are open at both edges, this value has a
lake at one edge and a lane at the other. Lake and open squares split evenly
within the lake rows — 10 lake squares and 10 open squares across the 2 × 10
lake zone — matching the 50:50 ratio both published layouts also use, just
distributed unevenly across the row instead of in uniform 2-wide blocks.

**The reserved "squeeze" case stays unreachable.**
[`technical-notes.md`](technical-notes.md#diagonal-attacks-and-lakes--a-decision-reserved-for-future-layouts)
reserves a decision for the first layout that makes a diagonal attack's two
flanking squares both lakes while its source and destination stay open, and
warns that breaking the 2-wide, edge-to-edge alignment of the lakes — as this
value's 1- and 3-wide blocks do — is exactly the kind of change that could make
it reachable. It does not, here: because both lake rows share the identical
column pattern, any two columns that are both lake columns and adjacent to
each other are lake in *both* rows, which makes the diagonal's source or
destination a lake too and rules the attack out before the squeeze question
arises — the same reasoning that keeps it unreachable on `standard_144` and
`standard_64`, and it does not depend on the lake blocks being a uniform
width. This value does not need `technical-notes.md`'s reserved decision, and
does not disturb it.

**Why:** Tests a genuinely non-uniform, non-mirror-symmetric lake pattern for
human playtesting, and a board size between Skirmish and Battle, before any
decision is made on whether either property is worth building into a published
edition.

**Status:** proposed.

### `ARMY_COMPOSITION` — new value `standard_clash`

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
has and this value does not). Paired with `asymmetric_100`'s 30-square home
zone, 20 pieces is a 66.7% fill — close to Skirmish's 67% (16 in 24) and
denser than Battle's 52% (25 in 48).

**Why:** A third army-size point, between Skirmish's 4 ranks and Battle's 6,
for the same playtesting purpose as the board.

**Status:** proposed.

### Together: the `CLASH` ruleset

`asymmetric_100` and `standard_clash` are a co-designed pair, only meaningful
in combination — exactly as `standard_64` and `standard_skirmish` are. If both
are ever implemented, they would name a new ruleset, **Clash**, alongside
Skirmish and Battle.

**No `TOWER_PLACEMENT` value is needed.** `spacing_and_lanes` exists because
Skirmish's home zones abut the lake rows directly, putting a home square in
the mouth of every lane (`technical-notes.md`, "the geometric definition").
`asymmetric_100` has a buffer row between each home
zone and the lake rows, exactly as `standard_144` does, so no home square is
ever in a lane's mouth — the existing default, `spacing_only`, is the only
sensible setting, same as Battle. `spacing_and_lanes` would be legal to select
but inert, as it already is on `standard_144`.

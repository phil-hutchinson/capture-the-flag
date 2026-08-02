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

## Proposals

### `TOWER_PLACEMENT`

**Identifier.** `TOWER_PLACEMENT`

**Value labels.** `spacing_only` | `spacing_and_lanes`

**Default.** `spacing_only` — exactly the placement rule as published: no two
Towers adjacent, including diagonally, and no other restriction on where a Tower
goes. Turning the flag on for no edition changes no existing play and no existing
record.

**What `spacing_and_lanes` does.** The spacing rule, *and* a Tower may not stand
on a square orthogonally adjacent to a **lane square** — a square in a lake row
that is not itself a lake. Nothing about any other piece changes; the numbered
pieces and the Flag stay unrestricted.

The set is **derived from the board, not listed per board.** That matters because
the two published boards give completely different answers to it:

- On **Skirmish** (`standard_64`) the lanes are columns A, D, E, H, and each home
  zone's front rank sits directly against a lake row. The restriction closes
  A3, D3, E3, H3 for White and A6, D6, E6, H6 for Black — four of twenty-four
  home squares each. B3, C3, F3, G3 stay open: those columns are lake in the lake
  rows, so nothing behind them is in front of a lane.
- On **Battle** (`standard_144`) it closes **nothing at all**. A neutral buffer
  row separates each home zone from the lake rows, so no home square is
  orthogonally adjacent to a lane square. The flag is well-defined there and is
  simply inert.

A layout enumerating its own closed squares would have to be right about that
twice, and wrong once for every board added later. Deriving it means a new layout
gets the rule correct by construction — including getting "closes nothing" right,
which is the answer for any board with a buffer row.

**Why.** Skirmish's home zone abuts the lakes, which puts a home square in the
mouth of every lane. That interacts badly with two other rules at once:

- A Tower can only be removed by an **orthogonal** attack (diagonal attacks are
  restricted to movable pieces), and any attack on a Tower is a **draw** — the
  attacker dies too.
- A lane at its narrowest is one square wide, so a piece crossing it can be
  attacked from, and can attack, only along the lane.

A Tower in a lane mouth is therefore a tollbooth: the only way past is to walk a
piece into it and lose that piece, and the approach is single-file so the trade
cannot be set up favourably. Three Towers against four lanes means a player can
plug three of them — spacing permitting, A3/D3/H3 or A3/E3/H3 — and reduce the
opening to which lane was left. Battle has the same Towers and the same lanes but
a buffer row, so the lane mouth is a neutral square nobody may occupy at
placement, and the position never arises.

The flag exists to test whether closing those squares makes Skirmish openings
more varied without touching anything else. It is deliberately narrow: it removes
a placement option rather than changing how Towers or lanes behave, so a game
played under it is legible to anyone who knows the base rules.

**What was rejected.** A *connectivity* rule — "a placement must leave some path
across the board" — was considered and rejected for step 11's write-up in
`technical-notes.md`. It states the intent more directly but is far worse as a
rule: it is a property of the two placements *together*, which secret simultaneous
placement cannot check, and it would need a path definition of its own that the
rest of the rules do not have. The geometric restriction is checkable by one
player alone, at the moment they place the piece.

**Status.** Branch open (story 37, step 10). Graduating to Appendix A in step 11,
together with the `2-1:SKIRMISH` edition that sets it to `spacing_and_lanes`.

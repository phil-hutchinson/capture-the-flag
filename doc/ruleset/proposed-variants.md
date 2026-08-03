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

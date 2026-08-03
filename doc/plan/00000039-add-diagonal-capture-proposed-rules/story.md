# Story 39: Add Diagonal-Capture Proposed Rules

## Summary

Propose two new rule flags touching diagonal attacks, entered into
[`doc/ruleset/proposed-variants.md`](../../ruleset/proposed-variants.md) in the
format that document's "Proposal format" section specifies: identifier, value
labels, default, what each non-default value does, why, and status.

1. **`DIAGONAL_ATTACKABLE`** — whether a diagonal attack may target *any* enemy
   piece, or only movable ones as today.
2. **`DIAGONAL_ATTACK_PATH`** — whether a diagonal attack additionally requires
   a clear corner to make the ply, or is legal by adjacency alone as today.

**This story is documentation only.** No code changes, no `RULE_FLAGS` entry, no
`rules.md` edit. Per the proposed-variants.md graduation rule, a flag enters code
and `rules.md` Appendix A only when its implementing branch merges — this story
opens no such branch. The two entries exist to be read and argued about, the
purpose the sandbox document is for.

## Motivation

`rules.md`'s diagonal-attack rule ([Section 4.3](../../ruleset/rules.md#diagonal-attacks))
currently combines two independent restrictions into one baseline rule with no
flag: a diagonal attack may target only a movable piece, and is legal purely by
adjacency (subject to the existing lake-corner allowance recorded in
`technical-notes.md`). Both restrictions are worth being able to test loosened,
independently of each other, before deciding whether either is worth
implementing:

- **`DIAGONAL_ATTACKABLE = all`** would let a diagonal attack remove a Tower or
  the Flag directly, removing the asymmetry where Towers and the Flag currently
  have a defensive perimeter that ordinary pieces do not.
- **`DIAGONAL_ATTACK_PATH = open_path`** would make a diagonal attack
  contingent on the geometry between attacker and target, rather than on
  adjacency alone — closer to how orthogonal movement is already blocked by
  intervening lakes and pieces.

Neither is proposed as a replacement for the baseline; both are variations to be
evaluated, which is exactly what a rule flag with a preserving default is for.

## Specification

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
| `open_path` | A diagonal attack additionally requires that **at least one** of the two squares flanking the diagonal (the two squares orthogonally adjacent to both attacker and target) be both unoccupied — by a piece of either side — and not a lake. If both flanking squares are lakes, occupied, or some combination of the two, the diagonal attack is illegal. |

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

## Documents to change

| Document | Change |
|---|---|
| `doc/ruleset/proposed-variants.md` | Add both entries under "Proposals," replacing the current `*(none)*` |

No other document changes. `rules.md`, `technical-notes.md`, `changelog.md`,
`CLAUDE.md`, and `record.py`'s `RULE_FLAGS` are all untouched by this story.

## Out of scope

- **Implementing either flag's behavior.** No change to move generation, combat
  resolution, or the `RULE_FLAGS` registry.
- **Deciding which value should ship, or whether either should ship at all.**
  This story only makes the proposals available to argue about and prototype
  against, per the sandbox document's stated purpose.
- **Any interaction between the two flags and `TOWER_PLACEMENT` or other
  existing flags**, beyond the qualitative note above. If either flag is later
  implemented, its interaction with the lane-restriction geometry and the
  squeeze/skirt cases needs its own analysis at that time.

# Story 46: Document Ruleset Three

## Summary

Write a complete proposed ruleset for a **major 3** of Capture the Flag, as a set
of **shadow documents** under
[`doc/ruleset/proposed-3/`](../../ruleset/proposed-3/) rather than as edits to any
published document. Nothing is published, no edition is created, no ruleset
pointer moves, and `2-0:BATTLE`, `2-0:CLASH` and `2-1:SKIRMISH` are untouched.

**This story is documentation only.** No code, no engine change, no `RULE_FLAGS`
entry, no edit to [`rules.md`](../../ruleset/rules.md) or
[`changelog.md`](../../ruleset/changelog.md). The documents exist so that the
companion front-end player application can implement and playtest the ruleset,
and so the design can be argued about, before any decision is taken to implement
it in this repository.

## Motivation

Major 2 gets its depth from four places: terrain (lakes and lanes), immobile
blockers (Towers), hidden setup, and combat. Major 3 removes the first three and
replaces them with a single new mechanic in the fourth — **rank reduction**,
where any piece surviving combat drops a rank. The bet is that one mechanic
carrying real strategic weight makes a better game than three sources of
complexity that each carry a little, and that a smaller, fully-open, fully-visible
game is easier to learn, easier to reason about, and easier to build against.

Two secondary goals shape the rest of it:

- **Make the numbering intuitive.** Higher rank = stronger piece. There is no
  mechanical argument for the change, but the cost of a counter-intuitive
  convention is paid forever by every new player and every new consumer, and it
  can only be fixed at a major bump.
- **Remove the placement metagame without removing variety.** A generated
  starting position drawn from over a billion possibilities gives every game a
  different shape while leaving nothing hidden.

## Why this needs a major, and not flags

Most of the change would fit major 2's flag model with behaviour-preserving
defaults. Two things do not:

1. **The rank numbering is inverted**, which redefines what a published symbol
   means in every position block. Appendix A's permanence promise exists to
   forbid exactly that, and it cannot be a flag without making a glyph's meaning
   depend on a setting.
2. **Rank reduction breaks replay-by-schema.** The piece arriving at a
   destination square is a different rank from the one that left the source, and
   the major 2 tape has no way to say so — so a consumer would render every
   post-combat board wrong, silently. The fix is a new notation mark, and a
   notation change is what a major is for.

Everything else — removing the lakes and Towers, the new army, the two-row home
area, direction-relative encumbrance, the generated start — rides the bump
because it is happening, not because it requires one.

## What was produced

| Document | What it is |
|---|---|
| [`proposed-3/README.md`](../../ruleset/proposed-3/README.md) | shadow-status statement and reading order |
| [`proposed-3/rules.md`](../../ruleset/proposed-3/rules.md) | the complete ruleset, player-facing and self-contained |
| [`proposed-3/start-position.md`](../../ruleset/proposed-3/start-position.md) | generating a starting position; counts; position IDs |
| [`proposed-3/technical-notes.md`](../../ruleset/proposed-3/technical-notes.md) | rationale, derivations, consumer hazards |
| [`proposed-3/changelog.md`](../../ruleset/proposed-3/changelog.md) | the entry this would publish, in the form consumers track |

`rules.md` and `start-position.md` are together sufficient to implement the game
without reading the major 2 documents.

## The ruleset in brief

- **8 × 8, entirely open.** No lakes, no lanes, no Towers.
- **16 pieces:** three each of ranks 1–5 plus a Flag, with **5 strongest**.
- **No placement phase.** Home areas are two rows and are filled completely; the
  starting position is generated and fully visible.
- **Rank reduction:** any piece that survives combat drops one rank.
- **Direction-relative encumbrance:** an enemy behind you does not slow you down.
- **Diagonal attacks against every piece**, the Flag included, subject to an
  open-path requirement — which is what gives a Flag its defence.
- **Piece exhaustion** replaces "no legal move," with mutual exhaustion a draw.
- **White's first ply is limited to one square**, to offset part of the
  first-player advantage.
- **Inactivity limit 40 plies**, down from 50.

## Out of scope

- **Any code change.** No engine, evaluator, or record-format implementation.
- **Engine and training implications.** Rank reduction and the new board have real
  consequences for feature encoding and for anything normalised against the army
  composition, and the generated start changes the shape of the learning problem.
  None of that is analysed here; this story describes a ruleset.
- **The fate of the major 2 rulesets.** Whether Battle, Clash and Skirmish
  continue to be offered alongside major 3 is a separate decision. This story does
  not make it and does not prejudge it.
- **Graduating anything.** The two diagonal-attack flags proposed in
  [`proposed-variants.md`](../../ruleset/proposed-variants.md) —
  `DIAGONAL_ATTACKABLE` and `DIAGONAL_ATTACK_PATH` — are adopted here as *baseline
  behaviour at major 3*, not graduated as flags. Their entries in that file are
  unaffected and remain proposals against major 2.

## Known open items

- **`PRE-RELEASE` is a working name**, and it reuses a ruleset name already
  retired at major 1. If major 3 is adopted, the ruleset should get its own name
  as a deliberate decision.
- **40 plies is provisional**, in the same sense 50 has always been. It is the
  first number to revisit once games have been played.
- **Rank reduction's main risk is passivity** from top-rank pieces, since using
  your best piece costs you a rank. That is the first thing to watch in
  playtesting.
- **If major 3 is adopted**, the sentence in
  [`technical-notes.md`](../../ruleset/technical-notes.md) stating that a notation
  break "moves every live ruleset to the next major at once" should be reworded to
  make its within-major scoping explicit, and the root
  [`CLAUDE.md`](../../../CLAUDE.md) description of a two-phase game no longer
  applies to this major.

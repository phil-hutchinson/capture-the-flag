# Ruleset — Claude project context

[`rules.md`](rules.md) in this folder is the **official, authoritative ruleset**
for Capture the Flag: the single source of truth that the engine implementation,
its tests, evaluators, and any external consumer are checked against. If the code
and `rules.md` disagree, that is a bug — and `rules.md` is the reference.

`rules.md` is written to be handed to a player as-is. Keep developer- and
design-facing material out of it: version metadata, provisional/tunable values,
naming history, and cross-references belong in
[`technical-notes.md`](technical-notes.md), not in the rulebook.

**Exception — Appendices A and B.** The Variants and Rulesets appendices in
`rules.md` deliberately carry edition ids and variant settings, which is
metadata by the rule above. They live in the rulebook because a player has to be
able to answer "which rules is this game using, and what are its settings?" from
the rulebook alone. The exception is those two appendices and nothing else:
their permanence promises are player-facing, while the reasoning behind an
edition, the record and checkpoint stamping, and the policy on what forces a
major bump stay in `technical-notes.md`. Proposed-but-unpublished variants stay
out of `rules.md` entirely — they belong in
[`proposed-variants.md`](proposed-variants.md).

## Rule: ruleset changes require a changelog entry

**Any change to `rules.md` must be accompanied by an entry in
[`changelog.md`](changelog.md)** (newest first) recording the edition, the story
number, and the date, plus a short summary of what changed.

**When the change alters how the game is played**, it also publishes a new
edition: add its row to `rules.md` Appendix B, move that ruleset's Active pointer
to it, note the superseded edition in the Historical table, and update
`ACTIVE_EDITION` in `capture_the_flag/record.py`. That table is what stamps every
game record and every checkpoint, so a stale value silently mis-tags everything
written after the change.

### The document leads; the code follows

Some rules facts are necessarily duplicated in code, because code cannot read
`rules.md`. The army composition is the clearest case, living in three places:

| Where | What it is |
|---|---|
| `rules.md` §2.2, and the row in Appendix B | **the definition** |
| `pieces.py` (`PieceType.army_count` → `ARMY_ROSTER`) | the engine's copy, enforced on every placement |
| the edition table in `record.py` | the copy each record and checkpoint is stamped from |

**Always change the document first, then bring the copies to it.** A change that
starts in code and is then written up backwards into `rules.md` is how a code
constant quietly becomes the real ruleset. `rules.md` governs: where it and the
code disagree, the code is the bug, whichever was edited first.

**A failing distribution test is not a prompt to edit the edition table.**
`tests/test_record.py` asserts the active edition's distribution equals
`ARMY_ROSTER`, so changing the roster fails it. That failure means the army
composition changed, which is a rules change, which publishes a **new edition**
— the previous one keeps the distribution it was published with, because records
and checkpoints stamped with it were played under exactly that. Editing the
existing edition's row to match the new roster would make the test pass and
retroactively falsify every artifact carrying that id. The test cannot tell those
two apart; this rule is what does.

**When the change is a clarification** — better wording for a rule that already
worked that way — the edition does not move. It still needs a changelog entry, so
that consumers tracking the changelog can see the text changed and re-read it.
The test for which case you are in is behavioral: if every game legal under the
old wording is still legal under the new one and resolves the same way, it is a
clarification.

New *behavior* is normally added as a rule flag with a
behavior-preserving default rather than as an edit to the core rules text — see
[`technical-notes.md`](technical-notes.md), "How a rules change lands", and
[`proposed-variants.md`](proposed-variants.md) for where a variant starts out.

**Why this is mandatory:** the rules are consumed outside this repository — in
particular, a separate front-end player application depends on them and tracks the
changelog to know when and how to update. A rules change with no changelog entry
is a silent breaking change for those consumers. Treat the changelog as part of
the ruleset, not optional documentation.

## Terminology: "move" in this document only

`rules.md` is written for a non-technical player audience, so it uses **"move"**
for a single player's action — *not* the project's standard term "ply." This is a
deliberate, documented one-off exception to the vocabulary in the root
`CLAUDE.md`: `rules.md` is the only document that prefers "move." Anywhere it
appears in `rules.md`, **"move" should be interpreted as "ply"** (one move = one
ply). When editing `rules.md`, preserve "move" terminology; use "ply" everywhere
else.

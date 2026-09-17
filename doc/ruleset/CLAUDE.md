# Ruleset — Claude project context

[`rules.md`](rules.md) at this level — not the copy inside any `proposed-*/`
shadow folder, see below — is the **official, authoritative ruleset**
for Capture the Flag: the single source of truth that the engine implementation,
its tests, evaluators, and any external consumer are checked against. If the code
and `rules.md` disagree, that is a bug — and `rules.md` is the reference.

`rules.md` is written to be handed to a player as-is. Keep developer- and
design-facing material out of it: version metadata, provisional/tunable values,
naming history, and cross-references belong in
[`technical-notes.md`](technical-notes.md), not in the rulebook.

**Exception — the Appendix.** `rules.md`'s Appendix deliberately carries edition
ids (and, once a major publishes any, rule-setting values), which is metadata by
the rule above. It lives in the rulebook because a player has to be able to
answer "which rules is this game using, and what are its settings?" from the
rulebook alone. The exception is that Appendix and nothing else: its permanence
promise is player-facing, while the reasoning behind an edition, the record and
checkpoint stamping, and the policy on what forces a major bump stay in
`technical-notes.md`. Proposed-but-unpublished settings stay out of `rules.md`
entirely — they belong in [`proposed-variants.md`](proposed-variants.md), or in
a shadow folder as described next.

## Shadow folders: whole-ruleset proposals

`proposed-variants.md` holds a proposal that fits *within* the published rules
text — a single rule flag with a behavior-preserving default. A proposal that
**replaces** the rules text cannot live there, because there is no flag to write
it as. That gets a **shadow folder** instead: a complete proposed major, as
shadow copies of `rules.md`, `technical-notes.md` and `changelog.md`, plus any
document with no published counterpart yet. `proposed-3/` was one such folder,
holding the proposed major 3 (Story 00000046) until story 00000049 adopted it.

Everything about such a folder is scoped to it:

- **Nothing in it is authoritative.** A shadow `rules.md` is a proposal;
  `rules.md` at this level remains the single source of truth the engine, its
  tests, and every external consumer are checked against. Where the two disagree
  that is expected, not a bug — the rule that "if the code and `rules.md`
  disagree, that is a bug" is about the published document only.
- **The changelog rule below does not reach inside it.** A shadow `changelog.md`
  is a draft of the entry the change *would* publish. It is not part of
  [`changelog.md`](changelog.md), and editing a shadow document publishes no
  edition, moves no ruleset pointer, and needs no entry here.
- **Nothing outside it may depend on it.** No code, no test, and no published
  document may cite a shadow document as a definition.

If a shadow ruleset is adopted, its documents merge into or replace their
counterparts at this level and the folder goes away; if it is abandoned, the
folder is deleted and nothing breaks. Either way the decision is explicit — a
shadow folder never graduates by drift.

No shadow folder currently exists.

## Rule: ruleset changes require a changelog entry

**Any change to `rules.md` must be accompanied by an entry in
[`changelog.md`](changelog.md)** (newest first) recording the edition, the story
number, and the date, plus a short summary of what changed.

**When the change alters how the game is played**, it also publishes a new
edition: add its row to `rules.md`'s Appendix, move that ruleset's Active pointer
to it, note the superseded edition in the Historical table, and update the set of
active editions in `capture_the_flag/record.py`. That table is what stamps every
game record and every checkpoint, so a stale value silently mis-tags everything
written after the change.

**There is one active edition** — `3-0:PRE-RELEASE` — and major 3 publishes no
rule flags, so a rules change is a change to the one rules text rather than a
choice to be considered across several flag-bearing rulesets. This was not
always so: major 2 carried three active editions (`2-0:BATTLE`, `2-0:CLASH` and
`2-1:SKIRMISH`) sharing one rules text and differing only in flag values, so a
change there had to be checked against all three, and their minor numbers could
(and did) advance independently. If major 3 grows a second ruleset, this note is
the place to restate that discipline.

**Prose that generalizes over the live rulesets is a maintenance hazard.**
Publishing a second major-2 ruleset (Clash) falsified several sentences in that
era's `rules.md` that were true of only one board, and one in `technical-notes.md`
that justified a reserved decision by a property that happened to hold rather
than one that was guaranteed to. When a second ruleset exists again, grep for the
sentences that say *both* or *every*.

### The document leads; the code follows

Some rules facts are necessarily duplicated in code, because code cannot read
`rules.md`. The army composition is the clearest case, living in three places:

| Where | What it is |
|---|---|
| `rules.md` §2.2 | **the definition** |
| the roster in `pieces.py` | the engine's copy, drawn by the start-position generator |
| the edition table in `record.py` | the copy the one active edition is stamped from |

Board layout works the same way, with `rules.md` §2.1 as its definition and the
layout in `board.py` as the engine's copy.

**Both collapse to a single value at major 3.** There is one board and one army,
and neither is published as a flag — `rules.md`'s Appendix names
`3-0:PRE-RELEASE` with no settings at all, so their ids are internal and appear
only in the engine-spec name and in error messages. `BoardLayout` and
`ArmyComposition` survive as types even though each has exactly one instance, so
the seam is already there the day major 3 grows a second board or army. Code
that assumes a second one exists today is premature, not a bug, until it
actually does.

**Always change the document first, then bring the copies to it.** A change that
starts in code and is then written up backwards into `rules.md` is how a code
constant quietly becomes the real ruleset. `rules.md` governs: where it and the
code disagree, the code is the bug, whichever was edited first.

**A failing distribution test is not a prompt to edit the edition table.** The
record tests assert each active edition's resolved distribution against the
engine's roster for that edition, so changing a roster fails them. That failure
means the army composition changed, which is a rules change, which publishes a
**new edition** — the previous one keeps the distribution it was published with,
because records and checkpoints stamped with it were played under exactly that.
Editing the existing edition's row to match the new roster would make the test
pass and retroactively falsify every artifact carrying that id. The test cannot
tell those two apart; this rule is what does.

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

**The one exception is a major bump**, which republishes the baseline rules text
and can therefore carry a behavior change unflagged; diagonal attack landed this
way at major 2. Do not reach for this to avoid writing a flag. A major bump is
justified by a **notation** break and nothing else, and behavior only rides one
that is already happening for that reason.

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

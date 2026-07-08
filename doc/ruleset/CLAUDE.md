# Ruleset — Claude project context

[`rules.md`](rules.md) in this folder is the **official, authoritative ruleset**
for Capture the Flag: the single source of truth that the engine implementation,
its tests, evaluators, and any external consumer are checked against. If the code
and `rules.md` disagree, that is a bug — and `rules.md` is the reference.

`rules.md` is written to be handed to a player as-is. Keep developer- and
design-facing material out of it: version metadata, provisional/tunable values,
naming history, and cross-references belong in
[`technical-notes.md`](technical-notes.md), not in the rulebook.

## Rule: ruleset changes require a changelog entry

**Any change to `rules.md` must be accompanied by an entry in
[`changelog.md`](changelog.md)** (newest first) recording the ruleset version, the
story number, and the date, plus a short summary of what changed. Bump the version
in both `changelog.md` and `technical-notes.md` when the rules change.

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

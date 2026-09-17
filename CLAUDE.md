# Claude project context

## Project

Capture the Flag is a single-phase, perfect-information battlefield board game:
every game begins from a generated starting position, fully visible to both
players from the first move, and proceeds by alternating play until the game
ends. It is implemented on top of [game-engine-core](https://github.com/phil-hutchinson/game-engine-core),
which is consumed as a pinned third-party dependency (see CONTRIBUTING.md) — the
generic engine, MCTS/PUCT search, and learning infrastructure live there; this
repo implements the game-specific rules, evaluators, and training.

## Intended audience

Assume a technically sophisticated audience — comfortable with algorithms, data
structures, game AI, and software design patterns. Avoid over-explaining
fundamentals; focus explanations on non-obvious design decisions and
domain-specific constraints. When writing user stories, the "user" is the
developer building this game and its AI — stories should reflect those goals
(e.g. implementing the ruleset, wiring up an evaluator, running training) rather
than end-user interactions.

## Conventions

See [CONTRIBUTING.md](CONTRIBUTING.md) for coding conventions (imports,
dependency pinning, etc.).

## Story Documentation

The folder `doc/plan/{story-name}/` (where the story name can be derived from the
branch) will contain the following, as needed. Pad the story number to 8 digits.

- **`story.md`** — the original story describing what was requested
- **`implementation-plan.md`** — the plan describing what was intended to be implemented
- **`peer-review.md`** — a peer review that also includes status and resolution of peer review items

Note: please do not make references to products with trademarked names.

## Implementation Strategy

The **`implementation-plan.md`** will contain one or more steps, each with a
testing strategy. Progress through steps one at a time, pausing after each one to
receive confirmation from the developer that the step has been implemented
correctly and that there are no issues. In the case that the testing is manual,
you may provide the developer with a reminder of what needs to be tested and how
this can be done. Always check for files that have not been committed before
beginning a new step: if there are files that have not been committed, **stop**
and verify whether the developer wants to commit the existing files before
continuing.

## Creation of Implementation Plans

Before creating or modifying an `implementation-plan.md`, read
`doc/guidelines/implementation-plan-guide.md` and follow it exactly.

## Vocabulary

For this repository, the following terms should be used:

**Ply** — a single action taken by one player in a turn-based game. Preferred
over "move" to avoid ambiguity: in common usage "move" can mean one player's
action *or* a full round of actions by all players. A ply is always unambiguous —
it refers strictly to one player's turn.

**Exception — the official rules document.** `doc/ruleset/rules.md` is written for
a non-technical player audience and deliberately uses **"move"** (not "ply") for
this same concept throughout. This is the *only* document where "move" is the
preferred term; everywhere else (code, tests, plans, design docs) use "ply." When
editing `rules.md`, keep it in "move" terminology and do not "correct" it to
"ply."

**Ruleset** — a mutable name for a body of rules. A ruleset name is a pointer,
not a definition — it always resolves to whichever edition is currently active
for it, and that pointer moves. One ruleset is live: `PRE-RELEASE`, on an 8 × 8
board with no lakes.

**Edition** — an immutable identifier of the form `<major>-<minor>:<Ruleset>`
(e.g. `3-0:PRE-RELEASE`), naming a **major baseline plus a complete set of rule
flag values**. Once published, an edition never changes meaning; a rules change
publishes a new edition and moves the ruleset's pointer to it. Immutability
attaches to the published label, not to a frozen copy of rules text or engine
code.

The **major names the baseline rules text; flags parameterize within it.** Two
editions sharing a major are two points in one flag space and differ only by
flag values. Two editions with different majors are not comparable that way — a
major bump republishes the baseline, so behavior can differ with no flag
distinguishing it (diagonal attack is baseline at major 2 and absent at major 1,
under no flag). A major is specifically a **notation** break; see
`doc/ruleset/technical-notes.md`.

Piece distribution is **not** a separate axis of an edition. Where a major
publishes flags, it is the resolved value of one (`ARMY_COMPOSITION`, at major
2) like anything else. Major 3 publishes no flags at all, so `3-0:PRE-RELEASE`'s
army is fixed directly by its baseline rules text — the zero-flags case of the
same rule: nothing but a major's own definition (baseline text plus whatever
flags it has) ever has a claim on what an edition means.

**Minor is namespaced per ruleset; major is global.** `2-0:BATTLE` and
`2-1:SKIRMISH` shared a major because they shared a notation and a baseline, but
their minors advanced independently — this is what actually happened: `SKIRMISH`
moved to `2-1` for a placement restriction that changed nothing about Battle, and
`BATTLE` stayed at `2-0`. The two were not meant to be brought back into step. A
notation break moves every live ruleset to the next major together — scoped to
whichever rulesets are live *at that moment*. Whether a new major also retires
the rulesets that came before it is a separate decision, not a consequence of
the notation break itself: major 3 made that decision explicitly, retiring
`BATTLE`, `CLASH` and `SKIRMISH` rather than carrying them forward (see
`doc/ruleset/technical-notes.md`).

The separator for editions is a **dash, not a dot** (`1-2:`, never `1.2:`): the
id is a compound label rather than a decimal, and a dot invites decimal ordering,
under which minor 10 would sort before minor 2.

**Rule flag** — an enum-valued rules parameter naming one point of rule
variation (e.g. `TOWER_MOVEMENT = on | off`). Always an enum even when currently
binary, so a third value can be added later without a type change. A flag's
default is always the standard behavior that predated the flag, so introducing
one alters no existing edition and no existing record. Published flag names and
value labels are permanent and never redefined — new behavior gets a new label.

A **resolved configuration** names an edition plus only the flags that deviate
from it; a flag absent from that list carries the edition's value for it.

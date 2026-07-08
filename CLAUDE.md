# Claude project context

## Project

Capture the Flag is a two-phase, perfect-information battlefield board game: phase 1
is secret simultaneous placement, phase 2 is alternating perfect-information
play. It is implemented on top of [game-engine-core](https://github.com/phil-hutchinson/game-engine-core),
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

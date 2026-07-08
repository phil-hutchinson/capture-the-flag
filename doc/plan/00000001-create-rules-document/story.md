# Story: Create the official rules document

## Summary

Produce a single, authoritative, human-readable rules document for **Capture the
Flag** — the kind of rulebook that would ship in the box with a physical board
game. It consolidates the rules that are currently scattered across several
exploratory design notes into one canonical reference that a person could read
and then sit down and play the game.

## Motivation

The rules of Capture the Flag currently exist only inside design-discussion
documents that were written to *work out* what the rules should be, not to
*state* them. Those documents interleave the ruleset with AI/training
design, open questions, rejected alternatives, and lengthy justifications. They
are invaluable as design history, but they are the wrong artifact for anyone who
just needs to know how the game is played:

- The rules are spread across multiple files and must be reassembled mentally.
- Player-facing rules are tangled together with machine-learning design and
  implementation concerns that a rules reader does not care about.
- The framing is deliberative ("we considered X, rejected it because…") rather
  than declarative ("this is the rule").

Before we implement the ruleset in code, we want one document that says, plainly
and completely, what the game *is*. It becomes the shared source of truth that
the implementation, tests, and evaluators are checked against — if code and the
rulebook disagree, that is a bug in one of them, and the rulebook is the
reference.

## What we want

A standalone rules document, written as an official rulebook for a general
audience (a player, not an engine developer). It should be complete enough that
someone could learn and play the game from it alone, and precise enough that it
resolves the edge cases that come up in real play.

It is fine — expected, even — for this to be a Markdown file living in the
repository.

### Content to cover

Drawn from the offline design notes:

- **Overview** — the theme, the two-phase structure (secret simultaneous
  placement, then alternating fully visible play), and the object of the game.
- **Components** — the board and the full piece roster (ranks, quantities,
  special pieces, non-combatants), presented as a player would encounter them.
- **The board** — dimensions, home zones, neutral buffers, and the lake pattern,
  including which squares are impassable.
- **Phase 1 — placement** — how the simultaneous secret setup works, that turn
  order is fixed and known before placement, and what constraints (if any) apply
  to where pieces may go.
- **Phase 2 — play** — turn order, movement (baseline plus the Knight charge and
  Skirmisher rush), and all combat rules: rank, equal-rank resolution, and every
  special-piece interaction (Assassin, Sapper vs. Tower, Halberdier vs. Knight,
  Knight-vs-Knight charge, Archer support, legality of sacrificial attacks).
- **Win conditions** — flag capture, loss on having no legal ply, the "no hope"
  structural win, and the no-progress draw clock, with the edge cases stated
  clearly enough to adjudicate an actual game.

### Scope and framing

- **In scope:** a clear, complete, declarative statement of the rules of play.
- **Out of scope:** the AI/training design, engine architecture, and
  implementation details — those belong in their own documents and should not
  appear in the rulebook.
- **Rationale is trimmed, not transcribed.** The design notes justify most rules
  at length; the rulebook states the rule. A short note on *intent* is welcome
  where it genuinely helps a player understand a rule, but the surveys of
  rejected alternatives and open design questions stay out.
- **Terminology.** Follow the project vocabulary — use "ply" for a single
  player's action. Do **not** use the trademarked names of any existing
  commercial board games, even though the design notes reference one for
  lineage; the rulebook stands on its own.

## Acceptance criteria

- A single rules document exists in the repository, readable start to finish as
  a self-contained rulebook.
- A newcomer could learn to play the game from this document alone, with no
  access to the design notes.
- Every rule from the design notes that governs actual play is represented; the
  win-condition and combat edge cases are covered precisely enough to settle
  disputes during a game.
- The document contains no AI/training or implementation content, no trademarked
  product names, and uses "ply" per the project vocabulary.

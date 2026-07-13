# Story: Move to the new game-engine-core release

## Summary

Adopt `game-engine-core` at git tag **`v0.1.1`** (the v0.1.1-alpha release) and
use its new capabilities to close the three upstream gaps that story 00000004
documented and worked around locally. After this story, Capture the Flag no
longer hand-rolls machinery the shared library now provides: game records state
*why* each game ended, the game log shows moves in the readable combat notation
from the rulebook, and batch play runs on the library's own tournament runner
instead of a bespoke copy. The deliverable is the existing headless batch run,
producing richer, more accurate records and a fuller summary, on top of the
newly pinned release.

## Motivation

Story 00000004 surfaced three things the shared engine could not express, recorded
them in `reference/game-engine-core-requirements.md`, and shipped local workarounds for
each: records that could only ever write `ResultReason "Unknown"`, a move log
stuck with the bare identity notation, and a hand-written match-and-batch runner
that reimplemented tallying the library's `Tournament` already offers but could
not be reused (its game-start seam had no way to run our secret placement phase).

Those gaps have now been addressed upstream. `game-engine-core` v0.1.1-alpha adds
a position-derived reason for a game's ending, splits a game's log rendering from
its interactive display so a game can annotate plies richly without disturbing
the ply's identity, and widens the tournament runner's game-start seam so a game
whose opening position depends on both players' private state can build it. This
story pulls those in and retires the corresponding workarounds.

It is worth doing now, before the work that depends on it. The text-UI story
(00000005) wants both the human-readable combat notation for its move entry and
score sheet and a correctly announced ending ("how it was reached"); the AI epic's
strength-measurement runs (stories 00000009–00000010) want the library's
tournament standings and cross-table over players that have a placement phase.
Closing these gaps here keeps those later stories from re-deriving the same
workarounds.

## What we want

- **Repin to the release.** Move the pinned `game-engine-core` dependency from its
  commit pin to the `v0.1.1` release tag — in both the base dependency and the
  `learning` extra, kept identical — and rebuild so the new version is actually
  installed and exercised (see `CONTRIBUTING.md`).

- **Records that say why the game ended.** Every ending Capture the Flag can
  reach — flag captured, unbreachable flag, inactivity, no progress, no legal
  move — is named in the game record instead of the placeholder `Unknown`, using
  the vocabulary already reserved in `doc/ruleset/technical-notes.md`. The batch
  summary gains a breakdown of endings by category, not just win/draw/loss tallies.

- **Combat notation in the move log.** The game log and the record's move sequence
  show the richer combat notation from `rules.md`
  [Section 4.4](../../ruleset/rules.md#44-recording-a-move) — marking each move's
  attack result — rather than the plain source-destination form. The plain form
  remains the move's identity everywhere it matters (legal-move generation, and
  the uniqueness property story 00000004's tests rely on); only what is *shown*
  changes. This retires the "reserved for later use" status the combat notation
  currently carries in the ruleset docs.

- **Batch play on the shared tournament runner.** The batch runner is rebuilt on
  the library's tournament machinery, feeding it a game-start step that runs our
  secret phase-1 placement (each side arranges its army privately) and hands the
  assembled opening position to phase-2 play. The bespoke tallying is dropped in
  favour of the standings and aggregation the library already computes, so a
  Capture-the-Flag batch reuses the same reporting every other game on the engine
  gets.

- **Close out the requirements record.** `reference/game-engine-core-requirements.md`
  is updated to reflect that all three items are resolved by the v0.1.1 adoption,
  and the ruleset/technical notes that described the old workarounds are corrected
  to describe the new behaviour.

## Out of scope

- **The text UI and human play** (story 00000005). This story does not add
  interactive board display, move entry, placement entry, or draw-by-agreement.
  It only makes the record and log carry the information those features will
  present.
- **Engine opponents** (story 00000006 and the AI epic). Batches here remain
  random-vs-random; this is a dependency-adoption and record-quality story, not a
  new-player-strength story.
- **New upstream features.** This story consumes v0.1.1 as published; it does not
  request or design further `game-engine-core` changes.
- **Placement sophistication.** The placement used to start each game is whatever
  story 00000004 already provides; no new placement intelligence is introduced.

## Acceptance criteria

- The project builds and its full test suite passes against `game-engine-core`
  pinned to the `v0.1.1` release tag, with the base dependency and `learning`
  extra pinned identically.
- A headless batch run writes one game-record file per game in which
  `ResultReason` names the actual ending (never `Unknown`), and the move sequence
  is rendered in combat notation.
- The plain source-destination notation is still each move's identity: legal-move
  generation and the uniqueness guarantee from story 00000004 are unchanged, and
  their tests still pass.
- The batch summary reports endings broken down by category alongside the existing
  win/draw/loss and game-length statistics.
- Batch play is driven by the shared library's tournament runner via its
  game-start seam; the previously hand-rolled tallying is gone.
- `reference/game-engine-core-requirements.md` and the affected ruleset/technical notes
  reflect the resolved state rather than the old workarounds.

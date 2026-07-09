# Story: Story buildout — map the repository's development into stories

## Summary

A planning pseudo-story. With the official rules document in place (story
00000001), lay out the development of the whole repository as a sequence of
stories, agree on the big picture, and write an initial `story.md` for each
planned story. The deliverable is this document plus the initial versions of
stories 00000004 through 00000012 in their respective `doc/plan/` folders.

## The roadmap

Development proceeds in three tracks, in order:

1. **A playable game.** Implement the full ruleset as a working game engine,
   prove it by running complete games at volume between random-moving opponents
   (story 00000004), then make it playable by two humans through a text
   interface (story 00000005).
2. **A reference opponent.** A simple engine that values pieces at flat rates
   and searches a little (story 00000006). Deliberately modest — its job is to
   be a fixed rung on the strength ladder that later engines are measured
   against, not to be good.
3. **The main AI** (stories 00000008–00000012, grouped under epic story
   00000007). A learned engine for both phases of the game: a self-play-trained
   network for the fully visible play phase, and a population-based system that
   learns a mixture of placement strategies for the secret placement phase. The
   two are designed to work as a unit — the play engine's judgment of a revealed
   position is what scores candidate placements.

### The stories

| # | Story |
|---|---|
| 00000003 | Story buildout (this pseudo-story) |
| 00000004 | Core game engine and random-play runner |
| 00000005 | Text UI and PvP runner |
| 00000006 | Simple heuristic engine |
| 00000007 | Epic: Main AI engine (pseudo-story) |
| 00000008 | AI engine scaffolding |
| 00000009 | Phase 2 AI self-play training |
| 00000010 | PSRO skeleton |
| 00000011 | Best-response oracle |
| 00000012 | Co-training orchestration and diagnostics |

## Process decisions recorded here

- **Story granularity.** A story must have a true deliverable — something
  runnable or usable on its own. Work that lacks one is a step inside a story's
  implementation plan, not a story. (This is why story 00000004 is one large
  story rather than three small ones: only the random-play runner at its end
  constitutes a deliverable.)
- **Stories stay non-technical.** Story documents describe what is wanted and
  why, in plain terms; technical design belongs in each story's
  `implementation-plan.md`. Some of the AI stories are unavoidably technical in
  subject matter — they should still push detail toward the plan.
- **Epic structure and branching.** Stories 00000008–00000012 belong to the
  Main AI engine epic (story 00000007). Story branches merge into the epic
  branch, and the epic branch merges into `develop`. Branch naming for the
  epic: `feat/main-ai-engine/7-epic`, `feat/main-ai-engine/8-ai-engine-scaffolding`,
  and so on.
- **Shared-library candidates.** Some components built for the AI epic are
  game-agnostic and will ultimately belong in the shared game-engine library.
  The approach: identify these early, build them in this repository with a
  clear delineation (code and tests) between shareable assets and the
  game-specific code that consumes them, and migrate them once proven — first
  duplicating into the shared library, then repointing this project at the
  shared versions, then deleting the local copies.

## Acceptance criteria

- Each of stories 00000004–00000012 has a `doc/plan/` folder containing an
  initial `story.md`, written to the granularity and style decisions above.
- This document accurately summarizes the agreed roadmap and process decisions.
- Story documents are initial versions: each will be revisited (and may be
  revised) when its implementation begins.

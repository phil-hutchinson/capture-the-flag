# Story: Epic — Main AI engine

## Summary

A pseudo-story holding the epic for the project's main AI: a learned engine for
both phases of Capture the Flag. The play phase (fully visible, alternating) is
handled by a network trained through self-play and used to guide search. The
placement phase (secret, simultaneous) is handled by a population-based system
that learns a *mixture* of placements — since against a capable opponent, the
right way to place is to be unpredictable in a principled way. The two systems
are designed as a unit: the play engine's judgment of a just-revealed position
is what scores candidate placements.

A hard constraint carried through the epic: **pure discovery.** No hand-written
placement layouts, no strategic hints — the system learns from the rules and
self-play alone. (Inputs derived from the rules themselves are permitted;
anything derived from human strategic judgment is not.)

## Child stories

| # | Story | In short |
|---|---|---|
| 00000008 | AI engine scaffolding | Everything the learned engine needs to stand and play, before any training: how positions are presented to the network, the network itself, and its wiring into search. Plays legally (and badly) end to end. |
| 00000009 | Phase 2 AI self-play training | Train the play engine to basic competence through self-play from random placements, with checkpoints and measurable strength gains against the reference engines. |
| 00000010 | PSRO skeleton | The placement-phase machinery, end to end but without improvement yet: a pool of candidate placements, scoring via the play engine's judgment, solving for the best mixture over the pool, and an in-game chooser that samples from it. |
| 00000011 | Best-response oracle | The improvement engine for placement: search for new placements that beat the current mixture, verify them with real games, and admit them to the pool. |
| 00000012 | Co-training orchestration and diagnostics | Interlock the two training loops on a schedule, and instrument the whole system with the health and progress measurements that tell us it is working. |

## Process notes

- Branching: story branches merge into the epic branch, the epic branch merges
  into `develop`. Naming: `feat/main-ai-engine/7-epic`,
  `feat/main-ai-engine/8-ai-engine-scaffolding`, and so on.

## Shared-library candidates

Several components built in this epic are game-agnostic and are expected to
migrate to the shared game-engine library once proven, per the process
recorded in story 00000003 (build here with clear delineation; migrate by
duplicating into the shared library, repointing this project, then deleting
the local copies). This section is the epic's single inventory of those
candidates — child stories refer back here rather than restating it.

Expected shared-library candidates:

- **Mixture solver** (story 00000010) — given a table of pairing scores
  between two sides' strategy pools, compute the best mixture for each side.
  Pure math; knows nothing about any game.
- **Strategy-pool machinery** (stories 00000010 and 00000012) — the pool
  itself (members retired to zero weight rather than deleted), the
  pairing-score table with support for refreshing scores, and mixture
  bookkeeping. Generic over what a "strategy" actually is.
- **Mixture chooser** (story 00000010) — seeded, reproducible weighted
  sampling from a solved mixture at game time.
- **Improvement-loop scaffolding** (story 00000011) — the
  propose/verify/admit/re-solve loop and its keep-what-scores-better search,
  generic over the game-specific notion of a "small alteration" to a strategy.
- **Exploitability measurement and diagnostics harness** (stories 00000011
  and 00000012) — defined entirely in terms of the machinery above.

Staying game-side: the placement representation and its two-square-exchange
alteration, the board's mirror symmetry, the rule-derived network inputs, and
the network with its position encoding and move-preference decoding.

Delineation mechanics while these live here: shareable assets go in their own
top-level package beside `capture_the_flag/`, may depend on the shared
game-engine library but never import from the game package, and carry their
own standalone tests — so the eventual migration is mechanical.

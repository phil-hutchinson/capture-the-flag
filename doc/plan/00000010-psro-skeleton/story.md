# Story: PSRO skeleton

## Summary

The placement phase handled end to end, without improvement yet. Placement is
a game of secret, simultaneous choice, so the goal is not one best layout but
a principled *mixture* of layouts. This story builds the skeleton of the
population-based approach (PSRO — Policy-Space Response Oracles): a pool of
candidate placements, each pairing scored by the trained play engine's
judgment of the revealed position, a solver that computes the best mixture
over the pool, and an in-game chooser that samples a placement from that
mixture. The deliverable is an engine whose placements are drawn from a
computed mixture over a (for now, randomly seeded) pool — the vessel that
story 00000011 fills with strength.

## Motivation

Placement is where this game's AI departs from the well-trodden path. There is
no turn-by-turn feedback during placement — only the final arrangement matters
— so search-as-you-go approaches don't apply, and a single fixed layout is
exploitable by an opponent who learns it. The mixture-over-a-pool structure is
the foundation the rest of the epic builds on, and it is worth proving as
plumbing — pool, scoring, solving, sampling — before any effort goes into
making the pool's contents good.

## What we want

- **A placement pool.** A collection of complete, legal placements — seeded
  with random ones for now — that both playing roles draw from, with members
  retired to zero weight rather than deleted. The board's left-right mirror
  symmetry should be exploited: a placement and its mirror image are the same
  strategy.
- **Pairing scores.** For any pair of pool placements (one per side), an
  estimate of the expected result, obtained cheaply from the trained play
  engine's judgment of the revealed starting position — with actual played-out
  games available as the slower, grounding alternative.
- **The mixture solver.** From the table of pairing scores, compute the best
  mixture over the pool for each role (first mover and second mover — turn
  order is known during placement, and the two roles may warrant different
  mixtures). As a byproduct, the solution measures how much moving first is
  worth — a number worth surfacing.
- **The chooser.** At game time, sample a placement from the appropriate
  role's mixture (with a coin-flip mirror), reproducibly under a seed.
- **Delineation.** The pool, scoring table, solver, and chooser machinery are
  game-agnostic candidates for the shared library; keep them cleanly separated
  (code and tests) from the Capture the Flag specifics, per the
  shared-library-candidates inventory in the epic story (00000007).

## Out of scope

- Improving the pool — searching for placements that beat the mixture is story
  00000011.
- Re-scoring schedules and interlocking with play-engine training — story
  00000012.

## Acceptance criteria

- An engine seat exists that places via a sampled draw from a computed
  mixture and then plays using the trained play engine — usable in batch runs
  and tournaments like any other engine.
- The solver's mixtures are correct on small hand-checkable score tables, and
  sampling honors weights and the mirror convention, reproducibly under a
  seed.
- Pairing scores from the play engine's judgment agree in direction with
  played-out games on a spot-checked sample.
- The shareable machinery does not depend on Capture the Flag specifics, and
  its tests stand alone.

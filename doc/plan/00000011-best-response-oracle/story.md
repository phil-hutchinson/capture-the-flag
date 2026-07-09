# Story: Best-response oracle

## Summary

The improvement engine for the placement pool. Given the current mixture of
placements (from story 00000010), search for a new placement that beats it,
verify the discovery with real played-out games, and admit it to the pool —
then re-solve the mixture and repeat. The deliverable is a running improvement
loop whose pool demonstrably strengthens over its random seeds, and whose
progress can be measured by how hard it has become to find anything that beats
the current mixture.

## Motivation

The skeleton's pool is random, so its mixture is only "the best of bad
options." All placement strength in the final system comes from this story's
loop: propose a challenger, prove it earns its place, add it, adapt the
mixture. The same loop also supplies the system's honesty check — the harder
it is for a fresh search to beat the current mixture, the closer that mixture
is to genuinely unexploitable, and that difficulty is a measurable quantity.

## What we want

- **A challenger search.** Starting from candidate placements (random ones,
  and later samples from the current pool), repeatedly try small alterations —
  exchanging the contents of two squares keeps every candidate automatically
  legal — keeping changes that score better against the current opposing
  mixture, as judged cheaply by the play engine. Run per role, since the two
  roles' mixtures differ. Within the epic's pure-discovery constraint: no
  human placement wisdom seeds or steers the search.
- **Verification before admission.** The cheap judgment that guides the search
  can flatter a challenger; a candidate joins the pool only after real
  played-out games confirm its edge against the current mixture.
- **The loop.** Admit, re-solve the mixture, search again — with sensible
  stopping and record-keeping, so a run of the loop is observable after the
  fact (what was tried, what was admitted, how the mixture shifted).
- **An exploitability measure.** The verified edge of the best challenger the
  search can currently find, tracked over time — the epic's primary health
  number for placement, and the signal that the loop has plateaued.
- **Delineation.** The search scaffolding and loop are game-agnostic shared
  library candidates; the placement-specific parts (what an alteration is,
  what the mirror symmetry is) stay game-side, per the
  shared-library-candidates inventory in the epic story (00000007).

## Out of scope

- Scheduling this loop against play-engine retraining, and the broader
  diagnostic suite — story 00000012.
- A learned generator of placements (a possible later refinement for seeding
  the search); random and pool-drawn seeds suffice here.

## Acceptance criteria

- The loop runs end to end: challengers found, verified with real games,
  admitted, mixture re-solved — repeatedly, without manual patching.
- Starting from a random pool, the loop produces a mixture that verified
  measurement shows is much harder to beat than the initial one.
- Challengers that fail real-game verification are rejected (and it is visible
  that this actually filters candidates in practice).
- The exploitability measure is produced and recorded over the course of a
  run.

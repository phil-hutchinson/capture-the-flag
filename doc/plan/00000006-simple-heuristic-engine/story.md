# Story: Simple heuristic engine

## Summary

A deliberately simple engine that plays meaningfully better than random: it
values each piece type at a flat rate and uses the shared library's search to
pick moves, with an equally simple approach to placing its army. The
deliverable is a reference opponent that reliably beats the random engine and
gives later engines a fixed rung to be measured against.

## Motivation

"Better than random" is too low a bar to measure progress against, and the main
AI is too far away to be its own yardstick. A cheap, transparent engine in
between gives the project a stable comparison point: when the learned engine of
the AI epic starts training, "does it beat the flat-value engine, and by how
much" is an immediate, interpretable progress measure. This engine is
explicitly a reference, not a destination — minimal effort, no tuning beyond
what basic credibility requires.

## What we want

- **A flat-value judgment of positions.** Each piece type is worth a fixed
  amount; a position's worth is the material on each side (plus, at most, some
  similarly crude signal — nothing clever).
- **Move selection via the shared library's search**, using that judgment to
  compare outcomes. Modest search effort is fine.
- **A placement approach.** The engine needs some way to lay out its army that
  is not embarrassing (e.g. Flag placed with some protection, pieces not
  obviously squandered). Explicitly low-effort: simple constrained randomness
  is acceptable. This is a reference engine, and placement sophistication is
  the entire subject of the AI epic — no real design energy goes here.
- **Comparison runs.** Batches of games — flat-value engine versus random —
  demonstrating a decisive edge, using the volume-running machinery from story
  00000004.

## Out of scope

- Any learned component, any tuned piece values, any placement intelligence
  beyond the minimum described above.
- Strength for its own sake. If it beats random decisively, it is strong
  enough.

## Acceptance criteria

- The engine plays complete legal games through the shared library's
  interfaces, in both headless batches and (via story 00000005) against a
  human.
- In a sizeable batch of games against the random engine, it wins decisively.
- Its piece values and placement approach are simple enough to state in a
  few sentences — transparency is part of being a good reference.

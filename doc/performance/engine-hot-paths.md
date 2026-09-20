# Engine hot paths — deferred optimizations

Measured costs in the rules layer that are worth fixing but are not scheduled.
Nothing here is a bug: every entry describes code that is correct and produces
the right plies, outcomes and records. They are collected so a future
optimization story starts from measurements rather than from guesses, and so a
reader who notices the same cost does not have to rediscover it.

**These are notes, not a plan.** An entry is a starting point: re-measure before
acting on one, since the numbers below were taken at a particular commit under a
particular workload, and the rules layer keeps moving.

## Direction-relative encumbrance is the engine's hottest function

Filed as finding #6 of story 49's peer review, which is where the measurements
come from.

`moves.is_encumbered_in_direction` decides whether a piece may step two squares
in a given direction: whether an enemy stands on any of the five squares ahead
of or beside it there (`rules.md` §4.2). It is called once per direction per
piece per ply generation, and ply generation is the pipeline's hottest seam.

**Measured over 15 seeded games:** 236,848 calls, 0.880s cumulative of 1.606s
total — **55% of engine runtime** — with 0.454s of that in the function body
itself rather than in what it calls.

Two costs, both structural:

- **The offsets are recomputed per call.** The five-offset tuple is a pure
  function of the direction, but each call rebuilds it: six tuple allocations
  plus the perpendicular arithmetic, for one of four possible answers.
- **The four directions rescan each other's squares.** Each direction reads up
  to five neighbours independently, so a piece costs up to 20 `board.get` calls
  and 20 `Square` constructions — against 8 for the whole-neighbourhood test
  this rule replaced at major 3, since every square any direction cares about is
  one of the eight around the piece.

Two approaches, in increasing order of payoff and of disruption:

1. **Hoist the offsets** to a module-level mapping from direction to its five
   offsets, built once at import. Mechanical, local, and leaves the call
   structure alone.
2. **Read the neighbourhood once per piece** in `_reachable_squares` and derive
   all four direction answers from that single scan. This is the one that
   removes the rescanning, and it is sound precisely because the rule is defined
   over the piece's own eight surrounding squares and nothing else — encumbrance
   is judged only from where the piece stands, never from what surrounds the
   destination (`rules.md` §4.2). If impassable terrain or a longer step is ever
   reintroduced, re-check that this still holds before trusting the scan.

### Constraint on any restructuring

`is_encumbered_in_direction` and `diagonal_path_is_open` are **public and have a
second caller**: `game_ui._illegal_reason` uses them to explain why a ply was
refused in the terms the rule is written in. A restructuring that inlines either
predicate into ply generation must leave the explanation calling the same
definition the generator uses, or the UI acquires a second implementation of a
rule that can drift from the first. Keeping a public predicate that the fast
path happens not to call is an acceptable outcome; two implementations is not.

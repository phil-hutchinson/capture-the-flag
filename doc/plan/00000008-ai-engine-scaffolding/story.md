# Story: AI engine scaffolding

## Summary

Everything the learned play engine needs to exist and play, before any training
happens: a way of presenting a game position to a neural network, the network
itself, a way of reading the network's preferences back out as moves, and the
wiring that lets the shared library's search use it. The deliverable is an
untrained AI engine that plays complete, legal games end to end — badly, but
through exactly the pathway that training will later improve.

## Motivation

Separating "the machinery works" from "the machinery is trained" makes both
tractable. Every piece of this story is testable without a single training
step: positions encode correctly, the network's outputs have the right shape
and meaning, search consumes them, games complete. When story 00000009 then
trains the network and strength doesn't improve, the fault is known to be in
training — not in plumbing.

## What we want

- **Position presentation.** A faithful encoding of a game position as network
  input, always from the perspective of the player to move. Alongside the
  board itself, this includes facts the rules already compute that would be
  needlessly hard for a network to rediscover — which Flags are walled in,
  which Sappers are available, and the clock states. (This is within the
  epic's pure-discovery constraint: these are facts derived from the rules,
  with no judgment attached about whether they are good or bad.)
- **The network.** A model sized for this board and for training on a single
  workstation, producing both a judgment of the position and preferences over
  moves.
- **Reading preferences out.** The network's raw move preferences turned into
  a proper distribution over the position's actual legal moves.
- **Wiring into search.** The engine plugged into the shared library's
  search-based move selection, and playable through the same interfaces as
  every other engine — batch runs, tournaments, and human play all work.

## Out of scope

- Training of any kind (story 00000009).
- Placement — the untrained engine can use random or reference placements for
  now; placement intelligence is stories 00000010–00000012.
- Auxiliary training signals beyond the basic two outputs — candidates for a
  later story if training needs them.

## Acceptance criteria

- The untrained engine plays complete legal games at volume through the shared
  library, with no errors, against random and reference opponents.
- Position encoding is covered by tests, including the rule-derived facts
  (enclosure, Sapper availability, clocks) on positions constructed to
  exercise them.
- The move-preference decoding is covered by tests: only legal moves receive
  probability, and the distribution is well-formed in every tested position.
- The pieces fit the shared library's training machinery as-is, so story
  00000009 starts from working plumbing.

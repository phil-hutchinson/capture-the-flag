# Story: Core game engine and random-play runner

## Summary

Implement the complete Capture the Flag ruleset as a working game engine, built
on the building blocks the shared game-engine library provides, and prove it
with a runner that plays complete games between two random-moving opponents at
volume. The deliverable is an application that can run batches of random games
from randomly generated placements, with every game finishing in a legal
outcome.

## Motivation

The rules exist only on paper (`doc/ruleset/rules.md`). Everything that follows
— human play, reference engines, the main AI — needs a trustworthy
implementation of the game itself: what the board looks like, what moves are
legal, how combat resolves, and how games end. Random-vs-random play at volume
is the cheapest honest test of that implementation: it exercises rules and
endings that hand-written scenarios miss, and it proves that every game
actually terminates.

## What we want

- **The game state.** A representation of the board and pieces that follows the
  official rules exactly: the 12×12 board with its lakes, the 48-piece armies,
  whose turn it is, and the two clocks (each player's inactivity counter and
  the shared progress counter).
- **A move convention.** A single, unambiguous written form for a move — usable
  to display a move, to record a game, and later to type a move in as a human
  player. Every legal move in a position must have a distinct written form.
- **Full legality.** From any position, exactly the legal moves per the rules:
  the one-square step, the Knight's charge, the Skirmisher's rush, lake and
  blocking restrictions, and attack legality (including sacrificial attacks).
- **Full combat.** Every combat rule in the rulebook: rank resolution,
  equal-rank mutual loss, and all special cases — Assassin, Sapper and Tower,
  Halberdier versus charge, the Knight-vs-Knight charge exception, and the
  Archer's defensive support.
- **Every ending.** Flag capture, loss by having no legal move, loss by
  inactivity, the no-progress draw, and the Unbreachable Flag win with its
  edge cases. (Draw by agreement is a human-interaction concern and belongs to
  the text-UI story.)
- **Random placement.** A generator producing uniformly random legal
  placements, used to start games. How a pair of placements becomes a game's
  starting position should be one clean seam, so later stories can swap in
  smarter placement (human entry, heuristic, learned) without touching the
  game itself.
- **The runner.** A headless application that plays many random-vs-random games
  and reports the outcomes — how each game ended and basic tallies across the
  batch. The shared library's game and tournament running should be reused
  rather than rebuilt.

The engine should slot into the shared game-engine library's interfaces so that
the library's engines, players, game runner, and (later) training machinery all
work with this game without adaptation.

## Out of scope

- Any human interface (story 00000005).
- Any engine smarter than random (stories 00000006 and the AI epic).
- Performance optimization beyond what volume runs need to complete in
  reasonable time — speeding up the rules engine is a known future concern for
  self-play training, addressed when profiling justifies it.

## Acceptance criteria

- `doc/ruleset/rules.md` is the authority: for any disagreement between code
  and rulebook, the code is wrong.
- The rules implementation is covered by tests, including the special combat
  rules and the ending conditions with their edge cases.
- The runner plays large batches (thousands) of random-vs-random games from
  random placements with no errors, no illegal moves, and no game failing to
  terminate.
- Batch results report every way a game ended; the outcomes seen are consistent
  with the rules (and the run demonstrates the clocks actually bound game
  length).

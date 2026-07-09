# Story: Text UI and PvP runner

## Summary

Make the game playable by people: a text-based interface for displaying the
board and entering moves, plus a runner that takes two human players through a
complete game — secret placement included — in the terminal. The deliverable is
a full game of Capture the Flag playable start to finish by two humans.

## Motivation

Story 00000004 proves the rules work; this story makes them experienceable.
Playing the game by hand is how rule questions, balance impressions, and
playability problems actually surface — and a human-usable interface is also
what lets a developer play against the engines built in later stories.

## What we want

- **Board display.** A clear text rendering of the full board: pieces of both
  sides distinguishable, lakes visible, and enough context to play from (whose
  turn it is, pieces captured so far, and the state of the clocks).
- **Move entry.** Moves typed in the written convention established in story
  00000004, with helpful rejection of illegal or malformed input (re-prompt,
  don't crash).
- **Placement entry.** A way for each player to set up their army secretly
  before play begins. This need not be elaborate — supplying a prepared
  placement (e.g. from a file) and/or entering it interactively with the screen
  cleared between players are both acceptable. A player should also be able to
  request a random legal placement.
- **Draw by agreement.** The one rule deferred from story 00000004: a player
  may offer a draw on their turn; the opponent accepts (game ends drawn) or
  declines (play continues).
- **The runner.** An application wiring the above into the shared library's
  game loop for a complete human-vs-human game, announcing the outcome and how
  it was reached.

Human-vs-engine play should fall out naturally from the shared library's player
abstractions (a human seat and an engine seat are interchangeable), but the
experience of playing against an engine is not this story's focus.

## Out of scope

- Graphical or web interfaces. A separate front-end player application exists
  as a longer-term consumer of the ruleset; this story is strictly the
  in-repository terminal experience.
- Engine opponents themselves (story 00000006 and the AI epic).

## Acceptance criteria

- Two people can play a complete game in the terminal: secret placement,
  alternating play, and a correctly announced ending.
- Every legal move can be entered; illegal and malformed input is rejected with
  a useful message and no loss of game state.
- Draw offers work as the rulebook describes.
- The display alone gives players everything they need to play correctly,
  including clock states relevant to the inactivity and no-progress rules.

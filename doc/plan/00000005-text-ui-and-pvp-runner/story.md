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
  turn it is, pieces captured so far, and the state of the clocks). The board
  itself reuses the position-block rendering already used for game-record
  files — that renderer draws any board, so only the surrounding status (turn,
  captures, clocks) is new.
- **Move entry.** Moves typed in the simple source–destination notation
  established in story 00000004 (e.g. `A2A3`) — the same form that identifies
  a ply — with helpful rejection of illegal or malformed input (re-prompt,
  don't crash). The game log continues to use the extended combat (`-`/`x`)
  form.
- **Placement from file.** Rather than an interactive placement UI, each
  player supplies their setup as a prepared placement file. Files live in a
  dedicated, gitignored folder in the repository; at placement time the player
  types a file name, the runner loads it from that folder, and a missing file
  is an error (re-prompt, don't crash). A player may also request a random
  legal placement instead of naming a file.

  A placement file is 4 rows of 12 characters, each character one of the
  one-character piece abbreviations (`1`–`9`, `A`, `T`, `F`). The file is
  written from the owning player's seat — first line the home row nearest the
  lakes, last line the back rank, columns left to right as that player sees
  them — so the same file produces the same setup for either side (for Black
  this is a 180° rotation of the board frame). A file that is
  not in this form (wrong row count, wrong row length, unknown character) is
  rejected with an error saying what is wrong. A file that is in proper form
  but does not match the army roster is rejected with an explanation of which
  piece types appear too many times and which too few.
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
- **Draw by agreement** (rules.md Section 6.6), previously deferred from story
  00000004 and now deferred again. This interface exists for game testing, not
  end-user play, so the rule adds nothing until engine opponents can weigh a
  draw proposal — revisit it when a consider-draw-proposal seam is added to
  the engine.
- Interactive placement entry. Placement is supplied by file (or random
  request) as described above.

## Acceptance criteria

- Two people can play a complete game in the terminal: placement from files
  (or random request), alternating play, and a correctly announced ending.
- Every legal move can be entered; illegal and malformed input is rejected with
  a useful message and no loss of game state.
- Placement-file problems are each reported usefully and re-prompted: a file
  that doesn't exist, a file not in the 4×12 form, and a well-formed file with
  the wrong piece distribution (naming the over- and under-supplied types).
- The display alone gives players everything they need to play correctly,
  including clock states relevant to the inactivity and no-progress rules.

## Notes from earlier stories

- **`play_match` / `MatchResult` retained for this story.** Story 00000015
  moved batch play onto the shared `Tournament` runner, which left
  `capture_the_flag.match.play_match` (and its `MatchResult`) unused by
  production code — only tests exercise it. It was deliberately kept rather than
  removed because this story's human-vs-human runner needs a single-game entry
  point (secret placement → phase-2 play → announced outcome) that `play_match`
  already provides. If this story's runner ends up not building on `play_match`,
  reconsider its retention and remove it (or fold it into the new runner) rather
  than leaving a second, untested-in-production game-construction path alongside
  `Tournament._play_game`.

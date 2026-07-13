# Implementation Plan: Text UI and PvP runner

Builds the story in five code steps plus a README check. The sequence is
bottom-up: pure parsing/rendering first (placement files, the game view), then
the interactive input pieces (ply prompt, human player), and finally the runner
that wires everything into `play_match`. Every step before the runner is
verifiable by automated test; the runner itself is verified by playing.

### Step 1 — Placement-file parsing and loading

Implement a placement-file module: given the text of a placement file and the
side it is for, produce a `Placement` (the existing home-zone mapping consumed
by `assemble_position`). The file is 4 rows of 12 one-character piece
abbreviations (`1`–`9`, `A`, `T`, `F`), written from the owning player's seat
(first line nearest the lakes, last line the back rank), so parsing maps
side-relatively onto the absolute home squares — a 180° rotation of the board
frame for Black. Report problems in two distinct vocabularies: a file not in
proper form (wrong row count, wrong row length, unknown character) says what is
structurally wrong; a well-formed file with the wrong piece distribution lists
which piece types appear too many times and which too few. Alongside parsing,
provide a loader that resolves a plain file name against the placements folder
and reports a missing file distinctly, and add the gitignore entry for that
folder (e.g. `placements/`).

Depends on: nothing — pure functions over the existing `Placement`,
`PieceType`, and home-square data. Steps 4 and 5 consume it.

Verification (automated): unit tests covering — a valid file parsed for White
and for Black lands the same setup on the correct absolute squares (the
rotation is checked explicitly); each malformed-form case produces its
structural message; a roster mismatch names the over- and under-supplied piece
types; a missing file name reports as such. Run `pytest` and confirm the new
tests pass.

### Step 2 — Full game-view rendering

Implement the status display the story requires around the existing position
block (`render_position_block` already draws any board): whose turn it is, each
side's pieces captured so far — derived by diffing the current board against
the army roster, so no extra state is threaded through the game — and the
three clocks (both inactivity counters and the shared progress counter, with
their limits so players can apply Sections 6.4–6.5). Expose this as a
game-view rendering of a `CtfPosition` and make `CtfGameUI.render_board` print
it, so `StandardGame`'s existing render hooks show the full view.

Depends on: nothing new — reads `CtfPosition` fields that already exist. It
precedes the input steps so that, once input works, play is fully observable.

Verification (automated): unit tests on constructed positions — captured-piece
lines reflect pieces missing from the board, and the turn and clock lines
report the position's fields. Optionally eyeball the composed view once via a
throwaway render of a random opening position (improvised).

### Step 3 — Ply entry

Implement parsing of the simple source–destination notation (e.g. `A2A3`) into
a `CtfPly` — the inverse of the ply's identity string, on top of the existing
square parsing — and implement `CtfGameUI.get_next_ply` (the seam story
00000004 left deferred): prompt the active player, parse the input, check the
result against the position's `legal_plies`, and on malformed or illegal input
print a useful message and re-prompt without disturbing game state. Structure
the prompt's input/output so tests can drive it with scripted input.

Depends on: Step 2 (completes `CtfGameUI`, whose display half Step 2 built).
Step 4 delegates to it.

Verification (automated): tests feeding scripted input — malformed text
re-prompts with a message, a well-formed but illegal ply re-prompts naming the
problem, and a legal ply is returned as the correct `CtfPly`. Run `pytest`.

### Step 4 — The human player

Implement a human `CtfPlayer`. `get_placement` prompts for a placement file
name, loads it via Step 1, and re-prompts on any of the three error kinds
(missing file, malformed file, wrong distribution) until a valid placement is
obtained; the player may instead request a random legal placement (the
existing `random_placement`). `select_ply` delegates to the UI's
`get_next_ply`, and the player asks to have the board rendered before each of
its turns so `StandardGame` shows the Step 2 view at the right moments.

Depends on: Step 1 (placement loading) and Step 3 (the ply prompt).

Verification (automated): scripted-input tests — a bad file name followed by a
good one yields the file's placement; the random request yields a placement
that assembles into a valid position; `select_ply` returns the ply the
scripted prompt entered. Run `pytest`.

### Step 5 — The PvP runner

Implement the runnable module (`python -m capture_the_flag.pvp_runner`): take
optional player names and a placements-folder override, build two human
players sharing a `CtfGameUI`, and drive one complete game through the
existing `play_match` — this is the single-game entry point the note from
story 00000015 retained it for, settling that question in favour of keeping
it. When the game ends, announce the outcome: which named player won (or that
the game is drawn) and the ending reason, in the vocabulary of `outcome.py`.
Clear the screen between the two placement prompts so the first player's typed
file name is not left visible to the second.

Depends on: Steps 1–4 — it is pure wiring of everything above into the shared
library's game loop.

Verification (manual): prepare two placement files in the placements folder
crafted so the flags are quickly reachable, then play a short complete game:
confirm the full view renders before each turn, a malformed and an illegal
move are each rejected with a message and re-prompted, a bad file name at
placement time is re-prompted, and the final announcement names the right
winner and reason. Play a second game using the random-placement request for
one seat to confirm that path.

### Step 6 — README check

Verify `README.md` against the story's changes: the status paragraph (which
currently says AI beyond random play lands later but does not mention human
play) and a new section on playing a human-vs-human game in the terminal are
expected to need updating; the `/update-readme` command automates the review.

Depends on: Steps 1–5 (documents the finished feature).

Verification (manual): read the resulting README diff and confirm it describes
the runner, the placement-file format and folder, and the move-entry notation
accurately — or confirm explicitly that no change was needed.

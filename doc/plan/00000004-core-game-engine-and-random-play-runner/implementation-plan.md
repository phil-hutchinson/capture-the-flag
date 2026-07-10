# Implementation Plan: Core game engine and random-play runner

Implements the Capture the Flag ruleset as a `game-engine-core`-compatible engine
and proves it with a headless random-vs-random batch runner. `doc/ruleset/rules.md`
is the authority throughout; where code and rulebook disagree, the code is wrong.

The written notation (move form, colour-encoded position block, PGN-style record
headers) follows the working spec in `.local/game-notation-suggestion.md`, which is
promoted into `rules.md` / `technical-notes.md` in Step 8.

## Architecture at a glance

The engine implements the `game-engine-core` protocols so the library's players,
`StandardGame`, and (later) training machinery consume it unchanged:

- `CtfPosition` implements `GamePosition` — `outcome`, `active_player_id`,
  `legal_plies`, `apply_ply`. It carries the board, side to move, three counters
  (two per-player inactivity/loss counters and one shared progress/draw counter),
  and cached breachability state.
- `CtfPly` implements `GamePly` — a source/destination pair. `str(ply)` is the
  **simple** move notation (`A4A5`, no separator), which is unique among a
  position's legal plies and sufficient to replay a game (the rules recover any
  combat result). Combat notation (the `-`/`x` display variant) is deferred and
  needs an upstream logging-format change; it is not implemented here.
- A **placement seam** builds a `CtfPosition` from two per-side placements; a
  random generator is one producer of placements. Phase-1 placement is modelled as
  a `CtfPlayer` subprotocol of `Player`, so a match wrapper can drive placement and
  then hand phase-2 play to `StandardGame`.

## Upstream `game-engine-core` requirements (documented, not implemented here)

Per the developer's direction these are recorded, not built in this story:

1. **`GameResult.result_reason`** — a free-text (or enum) field on `GameResult`,
   populated by `StandardGame`, letting a consumer record *why* a game ended
   (a concept common to most games: agreement, resignation, timeout, stalemate,
   …). Until it exists, records carry `ResultReason "Unknown"` and the batch
   summary reports outcomes + game length only, not ending category.
2. **A more flexible tournament / match runner** that accommodates a pre-play
   (phase-1) step, so the round-robin `Tournament` can be reused for games with a
   placement phase rather than us wrapping `StandardGame` ourselves.
3. **A separate logging/display ply format** — `StandardGame`'s game log currently
   uses `str(ply)`, which must stay the simple, unique identity key. An optional
   per-ply log renderer (defaulting to `str(ply)`) would let consumers log the
   richer combat notation without changing the identity key.

These are captured as a persistent artifact in Step 12.

## Steps

### Step 1 — Domain primitives: pieces and board geometry

Extend `board.py` (and add a piece module) with the static domain data: the piece
symbols and ranks, the 48-piece army roster, and mobility categories (Tower/Flag
immobile; Knight and Skirmisher as the special movers). Add the coordinate system —
column letters A–L / rows 1–12 in the global White's-perspective frame, with
parse/format, the two home-zone square sets, the lake square set (derived from
`LAKE_PATTERN`), orthogonal adjacency, and straight-line path enumeration between
two squares.

Depends on: nothing (foundational; everything else builds on it).

Verification (automated): `pytest` — unit tests assert the army sums to 48 with the
per-rank counts from the rules table, coordinate parse/format round-trips over all
144 squares, the lake set is the 12 expected squares, each home zone is 48 squares,
and straight-line path enumeration returns the correct intermediate squares
(including rejecting non-collinear pairs).

### Step 2 — Position state, placement seam, and random placement

Introduce `CtfPosition` as an immutable state container (board occupancy keyed by
square → (side, piece), side to move, the three counters (two per-player
inactivity/loss counters and one shared progress/draw counter), and slots for cached
breachability) and its `active_player_id`. Add a `Placement`
type (one side's 48-square home-zone arrangement), the seam that assembles a
`CtfPosition` from a White and a Black placement, and a uniformly-random legal
placement generator.

Depends on: Step 1 (pieces, board geometry).

Verification (automated): generate many random placements, build positions, and
assert each side has exactly 48 pieces confined to its home zone with correct
per-rank counts, the buffer/lake rows are unoccupied, side to move is White, and
all clocks start at 0. A fixed seed makes the generator's output reproducible in the
test.

### Step 3 — Colour-encoded board text rendering

Implement the shared position-block rendering: the full 12×12 board from White's
perspective (row 12 top → row 1 bottom, column A left), 3-char cells `[R]` / `*R*`
/ `---` / `XXX`, space-separated. This is the string later reused by the record
file and the library-facing `text_board`.

Depends on: Step 2 (a position to render).

Verification (automated + manual): a golden test asserts the exact rendered string
for a known placement (lake columns B, C, F, G, J, K show `XXX`; home zones full;
buffers `---`), plus a quick manual eyeball of one rendered board for readability.

### Step 4 — Ply type and legal move generation

Define `CtfPly` (source, destination) with its `__str__` as simple notation
(`A4A5`), and implement `legal_plies`: baseline one-square orthogonal steps, the
Knight charge (2–3 squares, clear straight line, attack-only, forbidden against a
Halberdier), the Skirmisher rush (1–3 squares, move or attack, clear line), lake /
blocking / friendly-occupancy restrictions, and all (including sacrificial) attacks.
Legality does not depend on the combat result (sacrificial attacks are always
legal), so no result is stored on the ply; the result is computed in `apply_ply`.

Depends on: Steps 1–2 (board/paths, position). Independent of combat (Step 5).

Verification (automated): on crafted positions, assert the exact set of legal ply
strings — correct step/charge/rush distances, charge-vs-Halberdier excluded,
clear-line blocking by pieces and lakes, sacrificial attacks present — and that all
`str(ply)` values in a position are distinct.

### Step 5 — Combat resolution

Implement combat as pure rules over (position, attacker square, defender square):
resolve to attacker-wins / attacker-loses / mutual-loss, covering rank order,
equal-rank mutual loss, and every special case — Assassin (offense/defense, the
Assassin-vs-Assassin and Assassin-vs-Tower exceptions), Sapper-vs-Tower and the
non-Sapper-vs-Tower complete sacrifice, the Knight-vs-Knight charge exception
(charge distinguished from an adjacent attack), and the Archer's defensive support
including its trigger-square geometry (one square beyond the defender along the
attacker's line, on-board and holding a friendly Archer) and the Archer-covered
Tower/Sapper trade.

Depends on: Steps 1–2 (pieces, board, position). Combat resolution feeds
`apply_ply` (Step 6); it is not needed for move generation (Step 4) or the ply
string, since simple notation carries no result.

Verification (automated): table-driven unit tests exercising every rank pairing,
equal-rank mutual loss, and each special case on crafted positions, with explicit
geometry tests for Archer support (valid support, off-board/lake/no-Archer
non-support, and the Tower+Archer vs Sapper trade).

### Step 6 — `apply_ply`: transitions, clocks, and breachability cache

Implement `apply_ply` returning the successor `CtfPosition`: move or resolve the
attack per the ply's result, advance side to move, update both inactivity counters
and the progress counter per Sections 6.4–6.5 (attack resets your counter; a
non-attack raises it; an opponent's sacrificial attack resets yours; a capture
resets the shared progress counter, a complete sacrifice does not), and recompute
the four cached breachability values only when the ply removed a Tower or a Sapper
(the only events that can change enclosure or Sapper availability).

Depends on: Steps 2–5 (state, combat, plies). Cache recompute reuses the Step-1
reachability/path primitives.

Verification (automated): unit tests drive sequences and assert clock values after
moves, winning attacks, trades, complete sacrifices, and opponent sacrifices; and
assert the breachability values change only across tower/sapper-removing plies and
are carried forward unchanged otherwise.

### Step 7 — Outcome and endings

Implement `outcome` (current-player-relative `1 / 0 / -1 / None`): flag capture,
loss by no legal move, loss by inactivity (counter reaches 50), the no-progress
draw (progress counter reaches 80), and the Unbreachable Flag win/draw computed from
the four cached breachability values — White wins iff its flag is enclosed and Black
has no available Sapper, symmetrically for Black, both-at-once a draw — including the
mutual last-Sapper-trade edge case.

Depends on: Step 6 (clocks and breachability maintained by `apply_ply`).

Verification (automated): unit tests construct positions realizing each ending and
assert the outcome, with dedicated cases for the Unbreachable Flag conditions
(availability re-checked after a Tower opens/closes a path) and the mutual
last-Sapper trade resolving to draw (both flags enclosed) vs. win (only one).

### Step 8 — Promote the notation into the official docs

Add the coordinate system and move notation to `rules.md` (player-facing score-sheet
section, in "move" terminology) — documenting both the simple form (current) and the
combat form (future display variant), distinguished by the `-` separator — and the
full game-record file format — colour-encoded position block, PGN-style headers
(Seven Tag Roster + `ResultReason`, `Result` required, PGN result values),
section/blank-line rules, LF/CRLF read tolerance, UTF-8 — to `technical-notes.md`.
Because `rules.md` changes, add a `changelog.md` entry and bump the ruleset version
1.0 → 1.1 in `changelog.md` and `technical-notes.md`.

Depends on: Steps 3 and 5 (the rendered position block and move notation now exist
and are stable). Comes before the record writer (Step 10) so the writer implements a
documented spec.

Verification (manual): review that `rules.md` describes exactly the notation Steps 3
and 5 emit, that `technical-notes.md` fully specifies the file format, and that the
changelog entry and version bump are present and consistent.

### Step 9 — GameUI, the `CtfPlayer` seam, random player, and match wrapper

Implement `CtfGameUI` (`text_board` = the Step-3 render; `render_board` prints it;
`get_next_ply` raises `NotImplementedError`, deferred to the text-UI story). Define
the `CtfPlayer` subprotocol of `Player` adding phase-1 placement, and a
`RandomCtfPlayer` (random placement + a `RandomEngine`-backed `select_ply`). Add the
match wrapper: obtain both placements, build the initial `CtfPosition` via the seam,
run phase-2 through the library's `StandardGame`, and return the placements together
with the resulting `GameResult`.

Depends on: Steps 2–7 (a fully playable position) and Step 3 (rendering). Reuses
`StandardGame`, `RandomEngine`, and `AIPlayer` from `game-engine-core`.

Verification (manual): run a single match end-to-end and confirm it terminates with a
legal outcome; print the opening board and move log and spot-check that plies are
legal and the notation reads correctly.

### Step 10 — Game-record file writer

Assemble a complete record file from a match result: PGN-style header tags (`Result`
from the absolute outcome, `ResultReason "Unknown"`, plus best-effort roster tags),
the setup position block, and the move sequence built from `StandardGame`'s game log
(round numbering, White/Black pairing, lone final White ply).

Depends on: Steps 8 (documented format) and 9 (match output).

Verification (manual + automated): write a record for a completed game and confirm it
matches the documented format by eye; an automated test round-trips the position
block (render → parse → render) and confirms a reader accepts both LF and CRLF.

### Step 11 — Batch runner application

Add the headless batch runner: play N random-vs-random matches, write each game's
record file, and report a batch summary — win/draw/loss tallies and game-length
statistics (min / max / mean plies). Expose it as a runnable module/script with the
batch size and output directory configurable.

Depends on: Steps 9–10 (match wrapper and record writer).

Verification (manual): run a modest batch (e.g. a few hundred games) and confirm it
completes with no errors, writes one record per game, and prints a coherent summary
whose length statistics stay within the clock-implied bound.

### Step 12 — Document required `game-engine-core` changes

Capture the upstream requirements surfaced by this story as a persistent artifact
(e.g. `doc/game-engine-core-requirements.md`) so the separate `game-engine-core`
project can act on them: (1) a `result_reason` field on `GameResult` populated by
`StandardGame`; (2) a match/tournament runner that accommodates a phase-1 pre-play
step; (3) a separate logging/display ply format (defaulting to `str(ply)`) so richer
combat notation can appear in logs without disturbing the identity key. Each entry
records the motivation and how this repo works around its absence today.

Depends on: Steps 9–11 (the workarounds these changes would replace now exist and
can be referenced concretely).

Verification (manual): review that the document names all three changes with
rationale and current workaround, and is self-contained enough to hand to the
`game-engine-core` project.

### Step 13 — Acceptance volume run and README check

Run the full-scale acceptance batch — thousands of random-vs-random games from random
placements — and confirm no errors, no illegal moves, every game terminating, outcome
tallies consistent with the rules, and length statistics demonstrating the clocks
bound game length. Then verify `README.md` reflects the now-implemented engine and
runner (package layout, how to run a batch), updating it as warranted (the
`/update-readme` command automates this).

Depends on: Step 11 (the runner); Step 12 (upstream requirements recorded).

Verification (manual): execute the large batch and confirm the acceptance criteria
hold; review and, if needed, update `README.md`.

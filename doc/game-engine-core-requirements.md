# Required `game-engine-core` changes

This document records three gaps in
[`game-engine-core`](https://github.com/phil-hutchinson/game-engine-core)
surfaced while implementing Capture the Flag (Story 00000004). None of them
were built in this repo — `game-engine-core` is consumed as a pinned
third-party dependency (see `CONTRIBUTING.md`), not vendored — so each is
worked around locally today and recorded here for the `game-engine-core`
project to act on. Each entry gives the motivation, the concrete workaround in
this repo, and a suggested shape for the upstream change.

## 1. `GameResult.result_reason`

**Motivation:** `game_engine_core.models.game_result.GameResult` carries only
`outcome: Literal[1, 0, -1]` — no record of *why* the game ended. This is a
concept nearly every game needs (agreement, resignation, timeout, stalemate,
checkmate-equivalent, …), not something Capture the Flag–specific. Without it,
a consumer that only sees a `GameResult` cannot distinguish a flag capture from
an inactivity loss from a no-progress draw.

**Current workaround:** `capture_the_flag/record.py`'s `write_record` always
writes the header tag `[ResultReason "Unknown"]` — see `record.py:62`, and the
docstring on `write_record` (`record.py:40-48`) which states this explicitly.
The game-record file format (`doc/ruleset/technical-notes.md`, "Record file
format") reserves a `ResultReason` tag with example values (`Flag Captured`,
`Inactivity`, `No Progress`, `Unbreachable Flag`, `No Legal Move`) that the
engine cannot currently populate. The batch summary in
`capture_the_flag/batch_runner.py` likewise reports only outcome tallies
(win/draw/loss) and length statistics, not an ending-category breakdown,
because that information doesn't exist upstream.

**Suggested shape:** add a `result_reason: str | None` (or a small enum, if
`game-engine-core` wants to standardize categories across games) field to
`GameResult`, populated by `StandardGame.run()`. Since only the game
implementation's `outcome`/`apply_ply` logic actually knows why a game ended,
this likely needs `GamePosition` to expose the reason alongside (or instead
of) the raw `1/0/-1` — e.g. a `outcome_reason` property parallel to `outcome`,
which `StandardGame` reads once the loop exits and threads into the
`GameResult` it returns.

## 2. A match/tournament runner that accommodates a phase-1 pre-play step

**Motivation:** `game_engine_core.tournament.tournament.Tournament` takes a
bare `position_factory: Callable[[], TPosition]` (`tournament.py:36`) — a
zero-argument callable with no way to consult per-player state before
building the initial position. Capture the Flag has a secret, simultaneous
phase-1 placement step: each side privately arranges its 48 pieces, and only
*then* does phase-2 alternating play (which `StandardGame` already models
correctly) begin. `Tournament`'s round-robin scheduling, standings, and
cross-table computation are all things this project wants to reuse unchanged
for CtfPlayer-vs-CtfPlayer round robins — but there's no seam for a
per-pairing pre-play step that produces the starting position from both
players' own state.

**Current workaround:** `capture_the_flag/match.py` hand-rolls a single-match
wrapper, `play_match`, instead of reusing `Tournament`: it calls
`white_player.get_placement(Side.WHITE)` and
`black_player.get_placement(Side.BLACK)` (`match.py:43-44`) — methods defined
on the `CtfPlayer` subprotocol of `Player` in `capture_the_flag/player.py`,
not on `Player` itself — assembles the initial `CtfPosition` via the
placement seam (`assemble_position`), and only then constructs and runs a
`StandardGame` for phase 2. `capture_the_flag/batch_runner.py` calls
`play_match` in a loop to run a batch, reimplementing the tallying
(`run_batch`'s win/black/draw counters) that `Tournament`/`TournamentResult`
already provide for phase-2-only games.

**Suggested shape:** give `Tournament` (or a sibling runner) a pre-play hook —
e.g. an optional `position_factory: Callable[[Player, Player], TPosition]`
overload, or a distinct `pre_play: Callable[[Player, Player], TPosition] |
None` constructor argument — invoked once per game with the two players about
to meet, so a game with a placement phase (or any other pre-play negotiation)
can build its own starting position from both players' own state before
`StandardGame` takes over. `Player` itself need not grow new methods; the
hook only needs to know how to ask each concrete player object for whatever
it needs, which is exactly what `CtfPlayer.get_placement` already does.

## 3. A separate logging/display ply format

**Motivation:** `StandardGame.run()` builds its game log as
`(str(ply), text_board)` pairs (`standard_game.py:38`), using `str(ply)` for
both the log entry *and*, implicitly, the ply's identity. For Capture the
Flag, `str(ply)` must stay the **simple** notation (`A4A5` — source then
destination, no separator) because it is what makes every legal ply's string
form unique in a position (see `capture_the_flag/ply.py`'s docstring and
`CtfPly.__str__`, `ply.py:19-20`) — a property Step 4's legal-move generation
tests rely on. But `doc/ruleset/rules.md`
[Section 4.4](ruleset/rules.md#44-recording-a-move) also documents a richer,
human-facing **combat** notation (`A4-A5`, `A4-A5x`,
`A4x-A5`, `A4x-A5x` — marking the attack result with `-`/`x`) that a score
sheet or a readable game log would want to show instead. There is currently
no way to log the combat form without changing what `str(ply)` returns, which
would break ply-string uniqueness.

**Current workaround:** this repo does not implement the combat notation at
all yet — `capture_the_flag/record.py`'s move sequence
(`_build_move_sequence`) uses the game log's plain `str(ply)` entries
unchanged. `doc/ruleset/technical-notes.md` ("Game notation and the record
file format") documents the combat form as "reserved for later use" pending
this upstream change.

**Suggested shape:** let `StandardGame` accept an optional per-ply log
renderer — e.g. `log_ply: Callable[[TPly, TPosition, TPosition], str] |
None = None` (given the ply, the position it was applied to, and the
resulting position, so a renderer can inspect combat outcome), defaulting to
`str(ply)` when omitted — and use its output for the game log entry instead
of `str(ply)` directly. The identity key (whatever `legal_plies`/`apply_ply`
compare on) stays `str(ply)`/the ply object itself; only the *logged* string
changes. This lets Capture the Flag supply a combat-notation renderer without
touching the simple notation's uniqueness guarantee.

# Required `game-engine-core` changes — RESOLVED

> **Status: all three resolved.** They were surfaced while implementing Capture
> the Flag (Story 00000004), recorded here as a persistent artifact, and closed
> by adopting `game-engine-core` **v0.1.1** (git tag `v0.1.1`, the v0.1.1-alpha
> release) in **Story 00000015**. `game-engine-core` did not implement them
> exactly as originally suggested below — the shapes that actually shipped are
> noted per item — but each closes the functionality gap. This document is kept
> as a record; the "Resolved in v0.1.1" notes are the current truth, and the
> original motivations/suggestions are preserved for context.

## 1. `GameResult.result_reason` — ✅ resolved

**Motivation:** `game_engine_core.models.game_result.GameResult` carried only
`outcome: Literal[1, 0, -1]` — no record of *why* the game ended. This is a
concept nearly every game needs (agreement, resignation, timeout, stalemate,
checkmate-equivalent, …), not something Capture the Flag–specific. Without it,
a consumer that only sees a `GameResult` could not distinguish a flag capture
from an inactivity loss from a no-progress draw.

**Original suggestion:** add a `result_reason: str | None` field to `GameResult`,
populated by `StandardGame.run()` from a new position-derived reason property.

**Resolved in v0.1.1:** `GamePosition` gained a **required** `outcome_reason:
str | None` property (non-`None` once `outcome` is set), and `GameResult` gained
a **required** `result_reason: str`, which `StandardGame.run()` reads off the
terminal position (raising if it is `None` when the game has ended). Non-optional,
no compatibility shim. This repo now implements `CtfPosition.outcome_reason`
(sharing branch logic with `compute_outcome` so the two can never disagree),
`write_record` stamps it into the `ResultReason` tag, and `run_batch` reports an
ending-category breakdown in the batch summary.

## 2. A match/tournament runner that accommodates a phase-1 pre-play step — ✅ resolved

**Motivation:** `game_engine_core.tournament.tournament.Tournament` took a bare
`position_factory: Callable[[], TPosition]` — a zero-argument callable with no
way to consult per-player state before building the initial position. Capture
the Flag has a secret, simultaneous phase-1 placement step: each side privately
arranges its pieces, and only *then* does phase-2 alternating play begin, so the
starting position is a function of both players' state. `Tournament`'s
round-robin scheduling, standings, and cross-table were all things this project
wanted to reuse unchanged — but there was no seam for a per-pairing pre-play step.

**Original suggestion:** an optional `pre_play` hook or an overloaded
`position_factory` taking `(Player, Player)`.

**Resolved in v0.1.1:** rather than a separate hook, `Tournament`'s existing
`position_factory` was **widened** to `Callable[[Player, Player], TPosition]`,
called once per game with the participants in side order (`side_one` first to
move) — one seam, no silent second path. Breaking change, no shim; zero-arg
factories become two-arg callables that ignore their arguments. This repo now
supplies `match.build_initial_position(side_one, side_other)` (downcasting each
`Player` to the `CtfPlayer` `get_placement` seam) and `run_batch` runs a
two-player round robin on `Tournament`; the former hand-rolled tallying is gone.

## 3. A separate logging/display ply format — ✅ resolved

**Motivation:** `StandardGame.run()` built its game log as `(str(ply),
text_board)` pairs, using `str(ply)` for both the log entry *and* the ply's
identity. For Capture the Flag, `str(ply)` must stay the **simple** notation
(`A4A5`) because that is what makes every legal ply's string form unique in a
position — a property the legal-move generation tests rely on. But `rules.md`
[Section 4.4](../../../ruleset/rules.md#44-recording-a-move) also documents a
richer, human-facing **combat** notation (`A4-A5`, `A4-A5x`, `A4x-A5`,
`A4x-A5x`) that a readable game log wants instead, and there was no way to log
it without changing what `str(ply)` returns.

**Original suggestion:** an optional per-ply `log_ply` renderer on `StandardGame`
defaulting to `str(ply)`.

**Resolved in v0.1.1:** logging was split into a new **`GameLogging`** protocol
(`text_board` plus `ply_annotation(from_position, ply, to_position) -> str`),
distinct from the now interactive-only `GameUI`; `StandardGame` and `Tournament`
take a required `GameLogging` and run headless with no UI. Breaking change, no
shim. This repo now implements `CtfGameLogging`, whose `ply_annotation` renders
the combat notation by reading survival off the resulting board, while
`CtfPly.__str__` stays the identity key. The combat form is no longer "reserved"
in the ruleset notes.

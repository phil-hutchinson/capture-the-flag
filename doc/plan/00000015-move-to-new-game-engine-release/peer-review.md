# Peer Review — Move to the new game-engine-core release

## Summary

The branch repins `game-engine-core` from a commit to the `v0.1.1` release tag
(in its own isolated commit, base + `learning` extra identical) and adopts the
release's three new seams: `CtfPosition.outcome_reason` feeds a real
`ResultReason` into records and an ending-category breakdown into the batch
summary; a new `CtfGameLogging` renders `rules.md` §4.4 combat notation in the
game log; and batch play now runs on the shared `Tournament` via the widened
`position_factory` (`build_initial_position`), retiring the hand-rolled
tallying. `pyright` reports **0 errors, 0 warnings**; `ruff check .` reports
**All checks passed**. Documentation (requirements record, technical notes,
README) is updated, and the plan's Step 6 covers README accuracy, so no
README-verification comment is warranted.

The implementation is faithful to the story and plan. The combat-notation
annotation, which reads piece survival off the resulting board, is sound because
`apply_ply` always advances a winning attacker onto the destination square (so
`ATTACKER_WINS`/`ATTACKER_LOSES`/`MUTUAL_LOSS` each map to a distinct
board state the annotator can distinguish). The `record.players[1]`/`[-1]`
indexing is correct — `GameRecord.players` is a `Mapping[Literal[1, -1], str]`
keyed by side, not a list. Two minor points were raised on first pass; after
discussion one is **Resolved** (the retained `play_match` helper is intentional
and now documented in story 00000005) and one is **Withdrawn** (record player
names were never lost — they are the tag values). Nothing is outstanding.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Resolved | Retention is intentional — `play_match`/`MatchResult` is kept as the single-game entry point that story 00000005's human-vs-human runner needs. Documented under a new "Notes from earlier stories" section in `doc/plan/00000005-text-ui-and-pvp-runner/story.md`, which flags that its retention should be reconsidered (removed or folded into the new runner) if that story's runner does not build on it. | [../../../capture_the_flag/match.py#L55](../../../capture_the_flag/match.py#L55) | Plan Step 2 said to "retire or trim the now-redundant single-match wrapper," but `play_match` is kept intact (updated to the new `game_logging`/optional-`game_ui` signature) and is no longer called by any production code — only tests exercise it now that the batch runs on `Tournament`. This is a defensible deviation (story 00000005's PvP runner will want a single-game entry point), but it leaves a second game-construction path alongside `Tournament._play_game` and the deviation isn't called out in the plan or commit. Confirm the intent to retain it, or drop it until 00000005 needs it. | Either keep it and note the retention rationale (future PvP runner), or remove `play_match`/`MatchResult` and have the record tests build a `GameResult` directly. | `def play_match(white_player, black_player, game_ui=None, render_final_board=True)` |
| 2 | Withdrawn | Not a defect. The record already stores player names as the *values* of the `[White "…"]`/`[Black "…"]` tags (PGN convention); the tag key names the side each player held that game. `Tournament`'s side alternation therefore writes each player under `White` or `Black` correctly per game, which is strictly better than the previous scheme where the players were literally named `"Random White"`/`"Random Black"` and the name redundantly encoded the colour. No change needed. | [../../../capture_the_flag/batch_runner.py#L114](../../../capture_the_flag/batch_runner.py#L114) | ~~Record player-name tags changed as a side effect of the `Tournament` migration~~ — withdrawn: player names are the tag values, the `White`/`Black` keys name the side, and per-game attribution is correct. | — | `white_name=record.players[1],`<br>`black_name=record.players[-1],` |

## Verification performed

- `pyright` — 0 errors, 0 warnings, 0 informations.
- `ruff check .` — all checks passed.
- Confirmed `GameResult.outcome` is absolute (`position.outcome * active_player_id`
  in `StandardGame.run`), so the batch runner's `outcome == 1 ⇒ White` mapping is
  correct.
- Confirmed `StandardGame.run` guards `render_final_board` with
  `self._game_ui is not None`, so `play_match`'s default `render_final_board=True`
  with `game_ui=None` is a safe no-op.
- Confirmed the pin bump is an isolated commit (`6866ae2`, `pyproject.toml` only),
  per `CONTRIBUTING.md`; CONTRIBUTING already permits release-tag pins.
- Confirmed the surviving "reserved for later use" wording in `technical-notes.md`
  refers to *mid-game records* (still deferred), not the combat notation (whose
  "reserved" status was correctly removed).

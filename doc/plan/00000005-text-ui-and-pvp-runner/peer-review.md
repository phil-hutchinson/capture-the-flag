# Peer Review — Text UI and PvP runner

## Summary

The branch adds the terminal human-vs-human experience the story asks for:
placement-file parsing/loading (`placement_file.py`), the full game view around
the shared position block (`game_view.py`), simple-notation ply parsing
(`parse_ply`) plus the deferred `CtfGameUI.get_next_ply` prompt, a
`HumanCtfPlayer`, and a runnable `pvp_runner` wiring both seats into the existing
`play_match`. All six implementation-plan steps are present (including the Step 6
README check, which was performed — the status paragraph and a new
"Playing a game in the terminal" section were added), the story/plan/diff are
consistent with one another, and both requested tools are clean: `pyright`
reports `0 errors, 0 warnings, 0 informations` and `ruff check .` reports
`All checks passed!`. The 30 new tests all pass. No correctness defects were
found; the findings below are minor robustness/DRY observations.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Resolved | Extracted the shared `PIECE_BY_SYMBOL` map into `pieces.py`; `rendering.py` and `placement_file.py` now import the single definition. `pyright`, `ruff`, and the full test suite (251 passed) stay clean. | [../../../capture_the_flag/pieces.py#L64](../../../capture_the_flag/pieces.py#L64) | `_PIECE_BY_SYMBOL = {piece.symbol: piece for piece in PieceType}` was defined identically in `placement_file.py` and `rendering.py`. Two independent copies of the symbol→piece map can drift. | Define the mapping once (e.g. export it from `pieces.py`) and import it in both modules. | `PIECE_BY_SYMBOL: dict[str, PieceType] = {piece.symbol: piece for piece in PieceType}` |
| 2 | Won't fix | Accepted as-is by the developer: harmless edge case, the reserved word `random` shadowing a same-named file is acceptable. | [../../../capture_the_flag/player.py#L116](../../../capture_the_flag/player.py#L116) | `get_placement` treats the typed word `random` (case-insensitively) as the random-placement request, so a placement file literally named `random`/`RANDOM` can never be loaded. Harmless edge case, but the reserved word silently shadows a valid filename. | Acceptable as-is; if worth closing, document the reserved word in the prompt/README, or gate the random request behind a sentinel that isn't a legal filename. | `if text.lower() == "random":` |
| 3 | Won't fix | Accepted as-is by the developer: out of the "re-prompt, don't crash" scope; an EOF/interrupt traceback at a prompt is acceptable. | [../../../capture_the_flag/game_ui.py#L45](../../../capture_the_flag/game_ui.py#L45) | `get_next_ply` and `HumanCtfPlayer.get_placement` call `self._input(...)` directly; an EOF (Ctrl-D) or `KeyboardInterrupt` at a prompt propagates as an uncaught traceback rather than an orderly exit. The "re-prompt, don't crash" requirement targets malformed input, so this is out of that scope, but a mid-game Ctrl-D ending in a stack trace is rough. | Optionally catch `EOFError`/`KeyboardInterrupt` at the runner boundary (`pvp_runner.main`) and print a clean "game abandoned" line. | `text = self._input(prompt).strip().upper()` |

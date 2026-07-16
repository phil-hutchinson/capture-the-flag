# Story: Conform to game-engine-core v0.1.3

## Summary

Move the pinned `game-engine-core` dependency from `v0.1.1` to `v0.1.3` and
bring this repo's code into conformance with the intervening breaking changes
that are actually load-bearing for the code as it exists on this branch: the
`Player` protocol's two new required methods, `observe_ply` and `reset`, are
missing from this repo's concrete player implementations, which is why `pytest`
currently fails to collect at all.

## Motivation

Upstream added `observe_ply` and `reset` to the `Player` protocol
(`game_engine_core/protocols/player.py`) in v0.1.2, so that `MCTSEngine` can
retain its search tree across plies — `AIPlayer` delegates both to the wrapped
engine, `HumanPlayer` no-ops both. `CtfPlayer` inherits `Player[CtfPly,
CtfPosition]`, so it picked up both new required methods automatically, but the
two concrete implementations in `capture_the_flag/player.py` —
`RandomCtfPlayer` and `HumanCtfPlayer` — were never updated to satisfy them.
Every test and script that constructs one of these players now fails, which is
why `pytest` cannot collect the suite at all.

v0.1.3 also changed `NeuralNetworkEvaluator`'s signature (dropping its `TPly`
type parameter, and changing `decode_policy` to take the full position instead
of `legal_plies`). That gap lives in `CtfNNEvaluator`, on a different branch's
scope, and is not addressed here — see the "Out of scope" section below.

## What we want

- **Repin to `v0.1.3`.** Move the pinned `game-engine-core` dependency from
  `v0.1.1` to the `v0.1.3` release tag — in both the base dependency and the
  `learning` extra, kept identical — and rebuild so the new version is
  actually installed and exercised (see `CONTRIBUTING.md`).
- **`RandomCtfPlayer` and `HumanCtfPlayer` satisfy the updated `Player`
  protocol.** Both gain `observe_ply(self, position: TPosition, ply: TPly,
  new_position: TPosition) -> None` and `reset(self) -> None`, matching
  upstream's `HumanPlayer` pattern: both methods are no-ops on both classes,
  since neither holds search state that needs to observe plies or be reset
  (`RandomCtfPlayer`'s wrapped `RandomEngine` is stateless per call).
- **The test suite collects and passes again.** The following fail only
  because they construct a `RandomCtfPlayer` or `HumanCtfPlayer` and hit the
  same missing-methods gap — no test logic changes are expected once the
  protocol conformance above is in place:
  - `tests/test_game_logging.py`
  - `tests/test_human_player.py`
  - `tests/test_record.py`
  - `capture_the_flag/pvp_runner.py` (not a test, but same root cause — it
    constructs these players too)
  - `tests/test_human_player.py`'s `_ScriptedPlayer` helper — check whether it
    implements `CtfPlayer`/`Player` directly (rather than reusing
    `RandomCtfPlayer`/`HumanCtfPlayer`) and, if so, needs the same two methods
    added.

## Out of scope

- **`CtfNNEvaluator`'s v0.1.3 signature change** (dropping `NeuralNetworkEvaluator`'s
  `TPly` type parameter and updating `decode_policy` to take the position
  instead of `legal_plies`). `decode_policy` is currently a stub on the
  AI-engine-scaffolding branch this depends on; that update belongs there, not
  here.
- **Stale-documentation cleanup in
  `doc/plan/00000008-ai-engine-scaffolding/implementation-plan.md`** (its
  "Fixed points verified against the code" section still names v0.1.1 and
  claims no pin bump is needed). That plan belongs to the AI-engine-scaffolding
  story and is corrected there, alongside the `CtfNNEvaluator` change above.

## Acceptance criteria

- The pinned `game-engine-core` dependency is `v0.1.3` in both the base
  dependency and the `learning` extra, and the installed package matches
  (verified via `direct_url.json`).
- `RandomCtfPlayer` and `HumanCtfPlayer` in `capture_the_flag/player.py` both
  implement `observe_ply` and `reset` as no-ops.
- `pytest` collects the full suite without error and passes.
- `ruff check .` and `pyright` are clean with respect to these changes (`pyright`
  may still report the pre-existing, out-of-scope `CtfNNEvaluator` errors from
  the v0.1.3 `NeuralNetworkEvaluator` signature change).

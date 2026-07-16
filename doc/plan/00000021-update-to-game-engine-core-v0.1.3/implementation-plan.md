# Implementation Plan: Conform to game-engine-core v0.1.3

This plan repins `game-engine-core` to `v0.1.3` and restores a green build on
top of it. Unlike story 00000015's adoption, this jump brings only one
load-bearing breaking change for this branch's code — the `Player` protocol's
two new required methods — so the whole story fits in a single conformance
step plus the standard README check.

## Step 1 — Repin to v0.1.3

Bump the pinned `game-engine-core` to `@v0.1.3` in **both** the base
dependency and the `learning` extra in `pyproject.toml` (kept identical), and
rebuild the container so the new version is actually installed.

**Already done:** this step has already been carried out on this branch —
`pyproject.toml` is bumped and the install was verified against
`direct_url.json` (commit `99dc2c6`, tag `v0.1.3`). It is recorded here as its
own step, per the story's acceptance criteria, and to keep it as a discrete
commit; no further action is needed before Step 2.

Why it comes here: nothing downstream can be verified against the real v0.1.3
protocols until the pin is actually in effect.

Verification (manual): confirm `pyproject.toml`'s base dependency and
`learning` extra both read `@v0.1.3`, and that the installed package's
`direct_url.json` reports the same tag/commit.

## Step 2 — Conform `RandomCtfPlayer` and `HumanCtfPlayer` to the updated `Player` protocol

Add `observe_ply` and `reset` to both `RandomCtfPlayer` and `HumanCtfPlayer`
in `capture_the_flag/player.py`, as no-ops on both classes, matching
upstream's `HumanPlayer` pattern (neither class holds search state that needs
to observe plies or be reset). Re-check `tests/test_human_player.py`'s
`_ScriptedPlayer` helper: if it implements `CtfPlayer`/`Player` directly rather
than reusing one of the two classes above, give it the same two no-op methods.

Why it comes here: this is the only conformance gap that is load-bearing for
the code as it exists on this branch (the `CtfNNEvaluator` signature change is
out of scope — see the story). It depends on Step 1's repin actually being in
effect, since the protocol's new required methods only exist on the v0.1.3
`Player` protocol.

Verification (automated): `pytest` collects the full suite without error and
passes, including `tests/test_game_logging.py`, `tests/test_human_player.py`,
and `tests/test_record.py`, which currently fail to collect; `python -m
capture_the_flag.pvp_runner` (or the relevant script) still constructs and
runs a player-vs-player game without error. `ruff check .` and `pyright` are
clean (`pyright` may still report the pre-existing, out-of-scope
`CtfNNEvaluator` errors from the v0.1.3 `NeuralNetworkEvaluator` signature
change).

## Step 3 — README accuracy check

Review whether the pin bump affects anything `README.md` describes (e.g. the
dependency version, if named). Update it if warranted, or confirm no update is
needed. The `/update-readme` command automates this against the branch diff.

Why it comes here: it verifies the repository's top-level documentation
against the completed change set, so it must come last.

Verification (manual): run `/update-readme`; confirm the README either needed
no change or now accurately reflects the `v0.1.3` pin.

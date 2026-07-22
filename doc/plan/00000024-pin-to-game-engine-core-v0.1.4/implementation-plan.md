# Implementation Plan: Pin to game-engine-core v0.1.4

This plan repins `game-engine-core` to `v0.1.4`. Unlike story 00000021's jump,
this one brings no load-bearing change for this repo's code — the only
upstream change is an additive, default-`None` `policy_transform` parameter on
`SelfPlayCollector` — so the whole story is the repin itself plus confirming
nothing broke.

## Step 1 — Repin to v0.1.4

Bump the pinned `game-engine-core` to `@v0.1.4` in **both** the base
dependency and the `learning` extra in `pyproject.toml` (kept identical), then
rebuild the container so the new version is actually installed. (Developer
will do the rebuild directly in VS Code.)

Why it comes here: nothing downstream can be verified against the real
v0.1.4 package until the pin is actually in effect. First step; nothing to
depend on.

Verification (manual): confirm `pyproject.toml`'s base dependency and
`learning` extra both read `@v0.1.4`, and that the installed package's
`direct_url.json` reports the matching tag/commit.

## Step 2 — Confirm the build is unaffected

Run the full check suite against the rebuilt container: `pytest`, `ruff check
.`, `pyright`. No source changes are expected — `v0.1.4`'s only change is the
additive `policy_transform` parameter on `SelfPlayCollector`, which nothing in
this repo currently calls.

Why it comes here: depends on Step 1's repin actually being in effect;
verifies the story's core claim (no refactor needed) rather than assuming it.

Verification (automated): `pytest` passes with zero failures, `ruff check .`
is clean, `pyright` is clean.

## Step 3 — README accuracy check

Review whether the pin bump affects anything `README.md` describes. The
README references `game-engine-core` generically (no pinned version number
called out), so no change is expected — confirm that rather than assuming it.

Why it comes here: verifies the repository's top-level documentation against
the completed change set, so it must come last.

Verification (manual): run `/update-readme`; confirm the README needs no
change (or update it if the review finds otherwise).

# Story: Pin to game-engine-core v0.1.4

## Summary

Move the pinned `game-engine-core` dependency from `v0.1.3` to `v0.1.4` in
`pyproject.toml` and rebuild the container so the new version is actually
installed and exercised.

## Motivation

`v0.1.4` adds an optional `policy_transform` hook to `SelfPlayCollector`
(`game_engine_learning/self_play_collector.py`): a capture-time callback,
applied while the collector still holds the `position`, that lets a
perspective-relative game re-key its MCTS visit distribution into the
policy head's frame before it is stored on a `TrainingSample`. This is
exactly the fix proposed in the working notes captured while implementing
story 00000009's phase-2 policy loss
(`.local/game-engine-core-policy-loss-perspective-gap.md`): Capture the
Flag's action space is side-to-move relative, so aligning a `target_policy`
with its logit column requires `active_player_id`, which is only in scope
at capture time, not later at loss computation.

The new parameter defaults to `None` (identity — the raw `str(ply)`
distribution is stored unchanged), so the bump itself is additive and
behaviour-preserving: nothing in this repo currently passes
`policy_transform`, so no existing code path changes. Adopting the hook to
actually resolve the perspective gap for the phase-2 policy loss is
separate follow-up work under story 00000009, not part of this story.

## What we want

- **Repin to `v0.1.4`.** Move the pinned `game-engine-core` dependency from
  `v0.1.3` to the `v0.1.4` release tag — in both the base dependency and the
  `learning` extra, kept identical — and rebuild the container so the new
  version is actually installed (see `CONTRIBUTING.md`).
- **No source changes required.** `v0.1.4`'s only change is the additive,
  default-`None` `policy_transform` parameter on `SelfPlayCollector`; no
  existing call site in this repo is affected.

## Out of scope

- **Adopting `policy_transform`.** Wiring up a Capture the Flag-specific
  transform to resolve the perspective gap documented in
  `.local/game-engine-core-policy-loss-perspective-gap.md` belongs to story
  00000009 (phase-2 self-play training), where the policy loss is being
  implemented. This story only makes the hook available.

## Acceptance criteria

- The pinned `game-engine-core` dependency is `v0.1.4` in both the base
  dependency and the `learning` extra, and the installed package matches
  (verified via `direct_url.json`).
- `pytest`, `ruff check .`, and `pyright` are all clean with no code changes
  beyond the pin bump.

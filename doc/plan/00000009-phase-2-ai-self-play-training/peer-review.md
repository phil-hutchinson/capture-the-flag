# Peer Review — Phase 2 AI self-play training (Story 00000009)

## Summary

This branch stands up the self-play → train → checkpoint machinery on top of the
story-8 play engine: a capture-time policy transform + player-independent policy
loss (Step 1), a random-placement position factory (Step 2), self-play collection
wiring (Step 3), single-generation training glue (Step 4), weights-only resumable
checkpoints (Step 5), a multi-generation orchestrator with a run-config record and
a `python -m capture_the_flag.training_runner` entry point (Step 6), and resume
support (Step 7). The re-scoped story (measuring strength deferred to a follow-up)
matches the delivered surface, and the implementation plan **does** include the
required README-freshness step (Step 8), which was actioned (README updated).

**Static checks.** As originally reviewed, `pyright` reported **3 errors** (all in
`tests/engines/neural_network/test_ctf_self_play.py` — attribute access on a value
typed `object`; issue #1) and `ruff check .` reported **8 findings** (5 × `I001`
import-ordering, 3 × `F401` unused imports; issues #2–#3). **All three are now
fixed** — `pyright` and `ruff` both pass clean. The `slow` tests (excluded from the
default run by `addopts = "-m 'not slow'"`) were subsequently executed and pass:
full suite is **231 passed** (3 `slow` included).

The frame math is correct and consistent: the collector stores targets already
rotated into the network frame via `transform_policy_to_white_perspective`, and
`ctf_policy_loss` maps them with `policy_logit_location_for_ply(ply, 1)`, which
composes to the same column `decode_policy` reads back — the story's "sharpest
correctness constraint" is satisfied and is well covered by tests.

## Comments

### Major

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Resolved | Fixed — typed `captures` as `list[tuple[CtfPosition, ...]]` and annotated `spy_transform`'s params (added the `CtfPosition` import). `pyright` now reports 0 errors. | [tests/engines/neural_network/test_ctf_self_play.py#L81-L83](../../../tests/engines/neural_network/test_ctf_self_play.py#L81) | `pyright` reports 3 errors: `captures` is typed `list[tuple[object, ...]]`, so `c[0].active_player_id` (L96–97) and `position.legal_plies` (L109) are flagged as unknown attributes on `object`. Test-only, but the review is required to run clean or record the findings. | Type the captured position as `CtfPosition` instead of `object` (e.g. `captures: list[tuple[CtfPosition, dict[str, float], dict[str, float]]]` and annotate `spy_transform`'s `position` parameter), which resolves all three errors. | `captures: list[tuple[object, dict[str, float], dict[str, float]]] = []` |

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 2 | Resolved | Fixed via `ruff check --fix .`. `ruff` now passes clean. | [capture_the_flag/engines/neural_network/ctf_policy_target.py#L1](../../../capture_the_flag/engines/neural_network/ctf_policy_target.py#L1) | `ruff` `I001` (import-block un-sorted) in five files: `ctf_policy_target.py:1`, `ctf_self_play.py:15`, `ctf_training.py:18`, `test_ctf_policy_target.py:1`, `test_ctf_self_play.py:9`. | Run `ruff check --fix .` (all are auto-fixable). | `from .ctf_nn_evaluator import rotate_ply, policy_logit_location_for_ply` |
| 3 | Resolved | Fixed — the three unused imports removed. | [tests/engines/neural_network/test_ctf_policy_target.py#L3](../../../tests/engines/neural_network/test_ctf_policy_target.py#L3) | `ruff` `F401` (unused imports): `torch.nn` (L3), `CtfNNEvaluator` (L6), and `NeuralCtfPlayer` (L7) are imported but never used in this test module. | Remove the three unused imports (`ruff check --fix .` handles these too). | `import torch.nn as nn` / `from ...ctf_nn_evaluator import CtfNNEvaluator` / `from ...neural_ctf_player import NeuralCtfPlayer` |
| 4 | Resolved | Fixed — `CtfPositionFactory` now takes an optional `rng` (held across calls); `train_generations` builds a `Random(seed)`-backed factory and threads it through `_run_generations` → `train_one_generation` when a seed is set, so seeded runs draw reproducible placements. Resumes stay unseeded by design. `--seed` help text updated. Verified: two `Random(0)` factories yield identical placement sequences while successive draws still differ. | [capture_the_flag/engines/neural_network/ctf_position_factory.py#L9-L13](../../../capture_the_flag/engines/neural_network/ctf_position_factory.py#L9) | `CtfPositionFactory.__call__` constructs a fresh, unseeded `Random()` on every call, so self-play placements are never derived from `config.seed`. `train_generations` seeds `random`/`torch`, and `--seed`'s help text advertises reproducibility, but the games (and thus the training data) differ run-to-run regardless of seed. The `train_generations` docstring honestly discloses this ("not bit-for-bit in the games played"), but the factory offers no seam to close the gap, which undercuts the AC "recorded well enough to reproduce the run." | Let the factory accept an optional `rng: Random` (defaulting to a module-level or injected instance) so a seeded run is fully reproducible, and align the `--seed` help text with the documented limitation. | `def __call__(self) -> CtfPosition:` `    rng = Random()` |
| 5 | Resolved | Fixed, and broadened per developer guidance: story/step references are a convention violation, so all "story 0000…"/"Step N" mentions were removed from comments and docstrings across the changed source and test files (not just the "Step 9" ones). | [capture_the_flag/engines/neural_network/ctf_training.py#L15](../../../capture_the_flag/engines/neural_network/ctf_training.py#L15) | Two docstrings reference "Step 9" as where the real training recipe is found (L15 and L55: "finding the real recipe is Step 9"), but the re-scoped plan has no Step 9 — the tuned training run was moved to "Deferred to follow-up work". The step number is stale and misleads a reader following the plan. | Reference "the deferred tuned training run (see the plan's 'Deferred to follow-up work')" instead of "Step 9". | `not a training recipe — finding the real recipe is Step 9.` |
| 6 | Deferred | No code change now (CPU-only path). Documented for GPU enablement in `.local/policy-loss-target-device-gpu.md`. | [capture_the_flag/engines/neural_network/ctf_policy_target.py#L35](../../../capture_the_flag/engines/neural_network/ctf_policy_target.py#L35) | `ctf_policy_loss` allocates the `targets` tensor with the default device/dtype and never moves it to `policy_logits.device`. Harmless on the current CPU-only path, but it will raise a device-mismatch if the network is ever moved to GPU. | Build `targets` with `device=policy_logits.device` (dtype is already fixed at float32). | `targets = torch.zeros((len(target_policies), *ACTION_SPACE_SHAPE), dtype=torch.float32)` |
| 7 | Won't fix | Confirmed intentional by developer — the `/learning-assistant` glossary is a standard artifact to update within a PR; no change required. | [doc/general-vocabulary.md#L1](../../../doc/general-vocabulary.md#L1) | `doc/general-vocabulary.md` (272 lines) is added on this branch but is not mentioned by the story or the implementation plan (it is a `/learning-assistant` byproduct, and `ctf_checkpoint.py` cites it). Reasonable to keep, but it is an artifact outside both reference documents — worth an explicit note so it is a deliberate inclusion rather than an accidental one. | Confirm the glossary is intended to ship with this story; if so, a one-line mention in the story records is enough. No code change needed. | `see doc/general-vocabulary.md, "Optimizer state"` |

_Note (not a finding): the branch diff against `main` also contains story
00000024's docs and the v0.1.3→v0.1.4 pin bump (commit 7abdb3c, PR #25), which are
the upstream capture-time-hook dependency this story builds on rather than part of
story 9's own scope — expected, not a defect._

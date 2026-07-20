# Peer Review — AI engine scaffolding (Story 00000008)

## Summary

This branch delivers an untrained learned play engine end to end: position
encoding (board + inactivity clock, side-to-move relative), a value/policy
residual network (`CtfCrn`), a policy decoder that masks to exactly the legal
plies, a `PositionEvaluator` composing the three, an `AICtfPlayer`, and runner
wiring — a shared `make_player` factory feeding an any-vs-any `game_runner`
(replacing `pvp_runner`) and machine-kind selection in `batch_runner`. The
deliverable is met: the engine plays complete legal games in both colours
through the shared library, verified by unit tests, a `play_match` integration
test, and manual batch runs. `pyright` reports **0 errors** and `ruff check .`
reports **all checks passed**. The core correctness constraints hold — the
8-delta action space provably covers the ruleset's orthogonal ±1/±2 movement
(rules.md 4.2), and the encoder/decoder share one rotation so perspective is
consistent — so all findings below are Minor.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Fixed | Lifted the rotation and the two pure index helpers to module-level functions `rotate_square` / `tensor_position` / `policy_logit_location_for_ply` in `ctf_nn_evaluator.py`; the encoder, decoder, and tests now import and call them (no more reaching into private methods). | [../../../capture_the_flag/engines/neural_network/ctf_nn_evaluator.py#L52](../../../capture_the_flag/engines/neural_network/ctf_nn_evaluator.py#L52) | The Step 3 plan note (implementation-plan.md L157) directs lifting the 180° rotation "to a shared module-level helper … have the encoder and the test fixtures use it." It shipped instead as an instance method (`_rotate_square`, alongside `_get_tensor_position` / `_get_policy_logit_location_for_ply`), none of which use `self`. Functionally correct and tested, but a documented deviation, and the test reaches into a private method (`evaluator._rotate_square`) rather than a public helper. | Either lift `_rotate_square` (and the pure index helpers) to module-level functions the encoder, decoder, and tests import, or update the plan note to record the decision to keep them as stateless methods. | `def _rotate_square(self, square: Square) -> Square:` |
| 2 | Fixed | Renamed `AICtfPlayer` → `NeuralCtfPlayer`, `build_ai_player` → `build_neural_player`, and the module/test to `neural_ctf_player.py` / `test_neural_ctf_player.py`; the library base class `AIPlayer` is (necessarily) still inherited, noted in the module docstring. | [../../../capture_the_flag/engines/neural_network/neural_ctf_player.py#L36](../../../capture_the_flag/engines/neural_network/neural_ctf_player.py#L36) | Mixed vocabulary for one concept: the user-facing kind token is `"neural"` (`PLAYER_KINDS`, CLI `--white neural`), while the internals say "AI" — `AICtfPlayer`, `build_ai_player`, `ai_ctf_player.py` — under a `neural_network` package. A reader grepping "neural" won't find the class; grepping "ai" won't find the CLI. | Pick one term. Simplest is to keep the `neural_network` package but note the `AI`≡`neural` equivalence in a docstring; or rename to `NeuralCtfPlayer` / `build_neural_player` for consistency with the token. | `class AICtfPlayer(AIPlayer[CtfPly, CtfPosition], CtfPlayer):` |
| 3 | Fixed | Documented the gap in the plan's "Reference opponents" bullet: machine seats use random placement only, reference-placement seating for a machine player is deferred to the placement stories (00000010–00000012), recorded as a known accepted gap. No placement feature added (out of scope for this story). | [../../../doc/plan/00000008-ai-engine-scaffolding/implementation-plan.md#L65](implementation-plan.md#L65) | Story acceptance calls for legal games at volume "against random **and reference** opponents." Machine seats (`random`, `neural`) always draw a random placement; no runner path seats a *reference* placement file for a machine player, so the "reference opponents" half of the criterion isn't reachable at volume. Consistent with the plan scoping placement intelligence out (stories 00000010–00000012), but the gap should be tracked, not silently closed. | Note the partial coverage in the story/plan closeout, or add a small follow-up allowing a machine seat to load a placement file from `placements/` (the human seat already can). | `return random_placement(side, self._rng)` |
| 4 | Resolved | No change needed — confirmed intentional: the `/learning-assistant` command and the story-9 stub were deliberately committed on this branch. | [../../../.claude/commands/learning-assistant.md#L1](../../../.claude/commands/learning-assistant.md#L1) | The branch carries changes outside the story's deliverable: `.claude/commands/learning-assistant.md` (workflow tooling, commit `e42162e`) and a stub for a *different* story, `doc/plan/00000009-phase-2-ai-self-play-training/story.md`. Neither is described in this story's `story.md` or `implementation-plan.md`. Harmless, but it muddies the branch's scope and the eventual PR. | Confirm both are intended to ride with story 8; if not, move them to a separate change. At minimum, mention them in the story closeout so they aren't a surprise in review. | `.claude/commands/learning-assistant.md`, `doc/plan/00000009-phase-2-ai-self-play-training/story.md` |
| 5 | Fixed | Replaced `run_batch`'s `rng` parameter with a single `seed: int \| None` that seeds all three sources itself (placement, process-global `random`, and `torch` for a neural seat); `main()` just forwards `--seed`. Verified: two seeded neural batches now produce byte-identical records. | [../../../capture_the_flag/batch_runner.py#L87](../../../capture_the_flag/batch_runner.py#L87) | `run_batch` seeds neither the process-global `random` (for `RandomEngine`) nor `torch` (for an untrained net's weights); it relies on `main()` to do both. A direct caller of `run_batch` with a `neural` seat — e.g. a future test wanting a reproducible neural batch — gets non-deterministic net weights despite passing a seeded `rng`. This matches the pre-existing pattern for `random`, and the docstring documents it, so it is a documentation/ergonomics nit rather than a bug. | Consider accepting an optional integer seed that `run_batch` applies to `random` and `torch` itself, so reproducibility isn't split between the function and its CLI wrapper. | `context = PlayerContext(rng=rng)` |

## Notes

- **README-check step present.** The implementation plan includes Step 8 ("README
  check") and it was carried out (status block updated, runner sections revised),
  so the plan-hygiene requirement is satisfied — no comment filed.
- **Story ↔ plan alignment.** The one substantive plan deviation — collapsing
  `pvp_runner` into an any-vs-any `game_runner` and dropping the lazy-`torch`
  constraint (torch is now a hard dependency) — is explicitly recorded in the
  plan (Step 7 deviation note; the hard-dependency bullet in "Context and
  constraints"), so it is a documented, justified departure rather than a silent
  one.

# Peer Review — Revamp the Ruleset (Story 00000018)

## Summary

This branch converts Capture the Flag from the 12-type / dual-counter ruleset to
the simplified 6-rank army with a single shared inactivity counter, replacing all
piece-specific abilities with a uniform movement (encumbrance) and combat
(formation bonus) model, enforcing the Tower non-adjacency placement constraint,
deleting the Unbreachable-Flag / breachability machinery, and restamping records
as `1.2:PRE-RELEASE`. The implementation faithfully follows the 7-step plan; the
rules, technical-notes, and changelog documents are all updated consistently, and
Step 7 (README check) is present in the plan. `pyright` reports **0 errors, 0
warnings**; `ruff check .` reports **All checks passed**; the full `pytest` suite
is **170 passed**. Only two Minor findings surfaced — both cosmetic/documentation.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Resolved | Docstring reworded to "near-uniformly random" and now states that only non-Tower arrangements are uniform while the Tower layout is approximately uniform. | [../../../capture_the_flag/placement.py#L51](../../../capture_the_flag/placement.py#L51) | The plan (Step 4) asks `random_placement` to "produce a uniformly-random *legal* placement," and the docstring summary still headlines "A uniformly random legal placement." The greedy Tower-first sampler is **not** uniform over legal placements: placing six Towers by sequential uniform choice over the shrinking candidate set biases the Tower configuration (edge/corner-heavy layouts are over-represented relative to a true uniform draw). The body docstring is honest that only "every non-Tower arrangement [is] equally likely," so the summary line and the plan's promise overclaim. Functionally the output is always legal, so impact is low — but the uniformity claim should be corrected (or the sampler reworked, e.g. rejection sampling, if true uniformity is actually needed). | Soften the summary line to "A random legal placement" (Towers are not uniformly sampled), or note explicitly that Tower layouts are only approximately uniform; alternatively reconcile the plan wording. | `"""A uniformly random legal placement for `side`: pieces dropped onto the` |
| 2 | Resolved | Partial-sacrifice example list now includes the formation-bonus draw against a one-rank-higher piece. | [../../../doc/ruleset/rules.md#L155](../../../doc/ruleset/rules.md#L155) | The "Partial sacrifice" definition's illustrative list — "any mutual-loss result you initiate — an equal-rank attack or a tower attack" — omits the formation-bonus case: a weaker attacker that draws against a piece one rank higher also initiates a mutual loss (both removed). The general clause "any mutual-loss result you initiate" is correct, but the two named examples could lead a reader to think a formation-bonus draw is not a partial sacrifice. | Add the formation-bonus draw to the example list, e.g. "— an equal-rank attack, a formation-bonus draw against a one-rank-higher piece, or a tower attack." | `- **Partial sacrifice** — the attacker is removed and so is the defender (any` |

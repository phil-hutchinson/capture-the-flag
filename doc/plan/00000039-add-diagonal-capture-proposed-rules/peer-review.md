# Peer Review — Story 39: Add Diagonal-Capture Proposed Rules

## Summary

This is a documentation-only change adding two proposed rule flags —
`DIAGONAL_ATTACKABLE` and `DIAGONAL_ATTACK_PATH` — to
`doc/ruleset/proposed-variants.md`, exactly as scoped by `story.md` and
executed per `implementation-plan.md`'s two steps. The diff touches only
`proposed-variants.md` (44 insertions replacing the `*(none)*` placeholder),
matching both documents' stated scope with no stray edits, no code, and no
`RULE_FLAGS`/`rules.md` changes. `pyright` and `ruff check .` both report zero
findings (0 errors/warnings/informations; "All checks passed!"), which is
expected for a change with no Python files touched. The implementation plan
includes the required README-accuracy step (Step 2); the review confirmed
`README.md` does not reference rule flags or `proposed-variants.md`, so no
update was needed there either.

No discrepancies were found between the story, the implementation plan, and
the actual diff — the proposal text in `proposed-variants.md` is a direct,
accurate transcription of `story.md`'s Specification section, and both new
entries carry every element the sandbox document's "Proposal format" section
requires (identifier, value labels, default, per-value behavior, why, status).
Only minor wording/formatting points remain, below.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Closed | fixed | [doc/ruleset/proposed-variants.md#L63-L72](../../ruleset/proposed-variants.md#L63-L72) | The `open_path` cell reads "be both unoccupied ... and not a lake," where "both" is meant to bind the two *conditions* (unoccupied, non-lake) on a single flanking square — but sits right next to "at least one of the two squares," inviting a misread where "both" refers to the two squares instead. | Reword to something like "be unoccupied (by a piece of either side) and not a lake" for the one flanking square, dropping "both" entirely, since "at least one of the two squares" already scopes it to a single square. | `A diagonal attack additionally requires that **at least one** of the two squares flanking the diagonal ... be both unoccupied ... and not a lake.` |
| 2 | Closed | skipped | [doc/ruleset/proposed-variants.md#L63-L87](../../ruleset/proposed-variants.md#L63-L87) | The new entries use a condensed "**Values:** `a` (default) \| `b`" line plus a behavior table, which differs from the labeled-paragraph style (`**Identifier.**`, `**Value labels.**`, `**Default.**`, `**What X does.**`, `**Why.**`, `**Status.**`) used by the only other proposal this file has ever carried (`TOWER_PLACEMENT`, see git history). The sandbox's "Proposal format" section doesn't mandate either style, and the new style actually mirrors published Appendix A entries in `rules.md` more closely — but it's worth a deliberate call rather than an incidental one, since a future proposal added without checking history could pick a third style. | No change required if the condensed/table style is the preferred house style going forward; otherwise note the choice, or align with the `TOWER_PLACEMENT` precedent. | `**Values:** \`movable_only\` (default) \| \`all\`` |


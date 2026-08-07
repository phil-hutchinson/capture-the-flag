# Peer Review — Story 41: Add 10×10 Board ("Clash") Proposed Rule

## Summary

This is a documentation-only change adding two proposed rule-flag values —
`BOARD_LAYOUT`'s `asymmetric_100` and `ARMY_COMPOSITION`'s `standard_clash` —
to `doc/ruleset/proposed-variants.md`, plus a joint note tying them together
as the "Clash" ruleset. The diff touches only `proposed-variants.md` for the
implementation step (96 insertions), matching both `story.md` and
`implementation-plan.md`'s stated scope: no code, no `RULE_FLAGS` entry, no
`rules.md`/`changelog.md`/`record.py` change. `pyright` reports `0 errors, 0
warnings, 0 informations` and `ruff check .` reports "All checks passed!",
both expected for a change touching no Python files. `README.md` was checked
against the diff directly (an allowed alternative per the plan's own wording)
and confirmed to need no update, since it references neither
`proposed-variants.md` nor any rule flag.

The proposal content is a faithful transcription of `story.md`'s
Specification section — the squeeze-unreachability argument, the
`TOWER_PLACEMENT` reasoning, the piece counts, and the lake-pattern table all
carry across correctly, with only cosmetic rewording. Two small transcription
slips remain, both Minor and both structural/traceability rather than
substantive.

## Comments

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Closed | fixed | [doc/ruleset/proposed-variants.md#L138](../../ruleset/proposed-variants.md#L138) | `story.md` gives "Together: the `CLASH` ruleset" a `###` heading, a peer of the `BOARD_LAYOUT` and `ARMY_COMPOSITION` sections above it. In `proposed-variants.md` it was transcribed as `####`, which nests it under `ARMY_COMPOSITION` in the document's heading hierarchy even though its content (the `TOWER_PLACEMENT` note especially) applies jointly to both entries, not just to `ARMY_COMPOSITION`. | Change `#### Together: the \`CLASH\` ruleset` to `### Together: the \`CLASH\` ruleset` to match `story.md` and keep it a peer section rather than a subsection of `ARMY_COMPOSITION`. | `#### Together: the \`CLASH\` ruleset` |
| 2 | Closed | fixed | [doc/ruleset/proposed-variants.md#L145](../../ruleset/proposed-variants.md#L145) | `story.md`'s `TOWER_PLACEMENT` paragraph cites where the tollbooth reasoning comes from: `"the mouth of every lane (`technical-notes.md`, "the geometric definition")"`. The transcription into `proposed-variants.md` drops that inline citation, leaving the claim unsourced where the rest of the document's new entries otherwise link out to `technical-notes.md` for their supporting reasoning (see the squeeze-case paragraph immediately above it). | Restore the citation, e.g. `"...the mouth of every lane (technical-notes.md, "the geometric definition")."`, or link directly to that section as the squeeze paragraph does. | `the mouth of every lane. \`asymmetric_100\` has a buffer row between each home` |


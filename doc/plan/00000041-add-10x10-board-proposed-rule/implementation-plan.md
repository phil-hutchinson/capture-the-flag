# Implementation Plan — Story 41: Add 10×10 Board ("Clash") Proposed Rule

## Step 1 — Enter both proposals in `proposed-variants.md`

Add two entries under "Proposals" in
[`doc/ruleset/proposed-variants.md`](../../ruleset/proposed-variants.md):
`BOARD_LAYOUT`'s new candidate value `asymmetric_100`, and `ARMY_COMPOSITION`'s
new candidate value `standard_clash`. Content for both is fully specified in
[`story.md`](story.md)'s Specification section — this step is a direct
transcription into the sandbox document, not new design work. Each entry notes
that it adds a value to an already-published flag rather than introducing a new
flag identifier, since that's a shape this document hasn't carried before.

Depends on: nothing — this is the story's only substantive step.

Verification (manual): Open `doc/ruleset/proposed-variants.md` and confirm:
- The "Proposals" section lists both entries, each identifying the existing
  flag it extends, the new value label, the layout/army detail, a "Why," and a
  "Status" of proposed.
- The `BOARD_LAYOUT` entry's squeeze-case note is present and matches
  `technical-notes.md`'s reserved-decision reasoning.
- No other section of the document changed.
- `git diff` touches only this one file.

## Step 2 — README check

Confirm `README.md` needs no update. This story adds no code, no new module, no
new CLI surface, and no change to setup or usage — only a documentation-only
addition to `proposed-variants.md`, which `README.md` does not reference.

Depends on: Step 1 (the diff must exist to check against).

Verification (manual): Run the `/update-readme` command (or review `README.md`
against the Step 1 diff directly) and confirm it reports no change needed.

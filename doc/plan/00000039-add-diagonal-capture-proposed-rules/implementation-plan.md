# Implementation Plan — Story 39: Add Diagonal-Capture Proposed Rules

## Step 1 — Enter both proposals in `proposed-variants.md`

Replace the `*(none)*` placeholder under "Proposals" in
[`doc/ruleset/proposed-variants.md`](../../ruleset/proposed-variants.md) with two
entries, `DIAGONAL_ATTACKABLE` and `DIAGONAL_ATTACK_PATH`, each following the
document's stated proposal format (identifier and value labels, default, what
each non-default value does, why, status). Content for both is fully specified
in [`story.md`](story.md)'s Specification section — this step is a direct
transcription into the sandbox document's format, not new design work.

Depends on: nothing — this is the story's only substantive step.

Verification (manual): Open `doc/ruleset/proposed-variants.md` and confirm:
- The "Proposals" section lists both `DIAGONAL_ATTACKABLE` and
  `DIAGONAL_ATTACK_PATH`, each with identifier, values, default, per-value
  behavior, a "Why," and a "Status" of proposed.
- No other section of the document changed except removing `*(none)*`.
- `git diff` touches only this one file.

## Step 2 — README check

Confirm `README.md` needs no update. This story adds no code, no new module, no
new CLI surface, and no change to setup or usage — only a documentation-only
addition to `proposed-variants.md`, which `README.md` does not reference.

Depends on: Step 1 (the diff must exist to check against).

Verification (manual): Run the `/update-readme` command (or review `README.md`
against the Step 1 diff directly) and confirm it reports no change needed.

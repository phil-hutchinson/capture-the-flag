# Implementation Plan: Rulesets, editions, and rule flags

See [story.md](story.md) for full context. This plan replaces the single mutable
`<version>:<name>` ruleset identifier with the ruleset / edition / flag model,
across four surfaces: the project vocabulary, the rules document, the record
writer, and the checkpoint + run-config stamps. It defines no rule flag and
implements no rule variation — the machinery only.

## Approach

**The registry is data, and it lives with the record writer.** The edition table
(edition id → piece distribution + flag values) and the flag registry go in
`capture_the_flag/record.py`, replacing `RULESET_NAME` / `RULESET_VERSION`, with
`ctf_checkpoint.py` importing the edition id and the comparison helper from
there. That gives the training side a dependency on the record-writer module,
which is the cost of keeping one home for the table rather than two.

**The comparison is torch-free; the rejection is not.** Structural comparison of
two configurations — and the diff that produces a message naming the offending
flag — sits beside the table in `record.py`, so it is unit-testable without
touching torch or building a network. `ctf_checkpoint.py` keeps only the
`raise`, alongside the spec and architecture checks it already performs.

**Documents before code.** The edition id the code stamps (`1-2:PRE-RELEASE`)
and the flag-permanence conventions are defined in `doc/ruleset/`, which is the
source of truth for the separate front-end repository. The code then reflects
what those documents publish, not the reverse. The one exception is the policy
rewrite (Step 7): it names the constants Steps 3–6 introduce, so it lands after
them rather than describing code that does not yet exist.

**Distribution as explicit data, cross-checked.** An edition entry spells out
its piece distribution rather than pointing at `pieces.py`'s `ARMY_ROSTER`,
since an edition that silently follows the live roster is not immutable. A test
asserts the active edition's distribution equals `ARMY_ROSTER`, so the duplicate
is a checked one. This narrows — but does not close — the story's documented
risk that the stamp is asserted rather than measured; flag values remain
unverified against play.

**Every local checkpoint becomes unresumable.** The 14 checkpoints currently
under `training-runs/` carry no `ruleset` key, and per the story a missing key is
a rejection, not a default. The run directories are machine-local and
gitignored, so nothing checked in is affected, but any in-flight training run on
this machine must be restarted from generation 1 after Step 5. This is the
story's stated intent, noted here so it is not a surprise mid-plan.

**Assumption — no minor bump.** The rules themselves do not change, so the
active edition stays at minor 2 (`1-2:PRE-RELEASE`), carrying the current `1.2`
forward. Step 7 still adds a changelog entry, because the restructure changes
the conventions the front-end repository tracks even though it changes no rule.

---

### Step 1 — Vocabulary

Add **Ruleset**, **Edition**, and **Rule flag** to the Vocabulary section of the
root `CLAUDE.md`, with the dash-not-dot rationale for the edition id (it reads as
a compound label, and minor 10 must not sort before minor 2). Note that a rule
flag is always enum-valued and always defaults to the pre-flag behavior.

Depends on: nothing. Every later step, in documents and in code comments alike,
uses these three terms with these meanings, so fixing them first keeps the
wording consistent rather than converging on it.

Verification (manual): read the new Vocabulary entries and confirm each of the
three terms is defined without reference to the others' internals, and that
nothing in the existing "Ply" entry or the `rules.md` "move" exception has been
disturbed.

---

### Step 2 — Rules document restructure

Add two appendices to `doc/ruleset/rules.md` and one new sibling file:

- **Appendix A — Variants.** Permanent and append-only, one entry per
  *published* flag in player-facing prose carrying flag id, value labels, and
  default. It has no entries yet; the appendix states its own conventions
  (labels are never redefined, defaults preserve pre-flag behavior) and the
  graduation rule — a flag arrives here only when its implementing branch
  merges.
- **Appendix B — Rulesets.** Two tables with identical fields, **Active** and
  **Historical**. Active holds one row, `1-2:PRE-RELEASE`, with its piece
  distribution and its (empty) flag values. Historical is empty, and documents
  its two labels, *superseded* and *retired*, and that all editions are equally
  immutable regardless of table.
- **`doc/ruleset/proposed-variants.md`.** The mutable sandbox, explicitly marked
  as such: entries are added, reworked, and deleted freely, and carry no
  permanence promise.

Also amend the "keep developer-facing material out of `rules.md`" rule in
`doc/ruleset/CLAUDE.md` with a carve-out for these two appendices, so the
restructure does not land in contradiction with a live convention. The rest of
that file's policy rewrite waits for Step 7.

Depends on: Step 1 (uses the three terms as defined there). Steps 3–6 stamp the
edition id this step publishes, and Step 7's policy rewrite points at these
appendices as the place rule changes now land.

Verification (manual): read `rules.md` Sections 1–6 and confirm they are
unchanged — this step adds appendices and touches no core rule. Section 7 (the
glossary) gains *Ruleset*, *Edition*, and *Variant*, without which the appendices
would use terms the rulebook never defines; confirm that is the only change to
it, and that `changelog.md` says the same. Then confirm
Appendix B's Active row gives the distribution 3 each of ranks 1–6, 6 Towers,
1 Flag (matching `rules.md` Section 2.2), that Appendix A and Historical are
present-but-empty rather than absent, and that `proposed-variants.md` is
reachable from `rules.md`.

---

### Step 3 — The edition table and the resolved configuration

In `record.py`, replace `RULESET_NAME` / `RULESET_VERSION` / `_RULESET_TAG_VALUE`
with:

- the **flag registry** as data (flag id → value labels + default), empty for
  now, since no flag is defined by this story;
- the **edition table**, edition id → piece distribution + explicit flag values,
  holding `1-2:PRE-RELEASE`, and a constant naming the active edition;
- a **resolved configuration** — an edition id plus only the flags deviating
  from it — with the two-level resolution the story specifies: an absent flag
  takes the edition's value, falling back to the flag's own default only when
  the edition predates the flag;
- a **deterministic string rendering** for the record's text medium, ordering
  flags alphabetically by flag id;
- a **structural comparison** yielding, for two configurations, what differs and
  in which direction — including the case of a flag the running code does not
  know at all, which is what makes a message like "flag `MOVABLE_TOWERS`:
  checkpoint says `on`, running code has no such flag" possible.

The writer is left calling the old tag path in this step; only the data and
helpers are introduced. With the registry empty, the known-flag set is empty, so
any flag named in an incoming configuration is by definition unknown — that is
the branch the comparison must handle correctly, not a corner case to defer.

Depends on: Step 2 (the edition id and flag conventions it publishes). Steps 4,
5, and 6 all consume these helpers; the checkpoint check in Step 5 is the
comparison's first real caller.

Verification (automated): `pytest tests/test_record.py`. The behavior here is
pure data manipulation with no runtime surface a manual test could exercise, so
tests are the appropriate level. Cover: rendering is alphabetical by flag id and
stable across insertion orders; a configuration with no deviating flags renders
as the bare edition id; resolution returns the edition's value for an absent
flag and the flag default only for a pre-flag edition; comparison of a
configuration against itself is empty, and against one naming an unknown flag
reports that flag as unknown rather than as a value mismatch; the active
edition's distribution equals `pieces.ARMY_ROSTER`.

---

### Step 4 — The record writer stamps the edition

Switch `write_record`'s mandatory `Ruleset` tag to the rendered configuration
from Step 3: the full edition id, never a bare name, plus any deviating flags.
Delete the superseded constants and update `record.py`'s module docstring and
`write_record`'s docstring, both of which currently describe the
`VERSION:NAME` form and the "latest version only" policy. Update
`tests/test_record.py`, which imports the deleted constants and asserts the
literal `1.2:PRE-RELEASE`. Export whatever a caller legitimately needs (the
active edition constant) from `capture_the_flag/__init__.py`, alongside the
existing `write_record` export.

Depends on: Step 3 (the table and the rendering). Nothing depends on this step —
the record path terminates here, since this repository writes records and never
reads them.

Verification (manual): run
`python -m capture_the_flag.batch_runner -n 3 -o /tmp/records` and confirm every
written file's header carries `[Ruleset "1-2:PRE-RELEASE"]` — dashes, full
edition id, no flags listed — with the surrounding `Result` / `ResultReason` tags
and the position block unchanged in form.

---

### Step 5 — Checkpoints pin the configuration

Have `save_checkpoint` stamp the resolved configuration as a nested mapping under
a `ruleset` key, following the precedent the architecture stamp sets, and have
`load_network` check it before rebuilding the network. Three outcomes, mirroring
how the existing spec and architecture stamps are already handled differently
from one another:

- **absent** `ruleset` key → rejection, with a message saying the checkpoint
  predates ruleset stamping, as the unstamped-spec case already does;
- **present and implementable** → adopted, so the run continues under the
  tagged configuration rather than under current defaults, exactly as the
  architecture already is;
- **present and not implementable** by the running code → rejection naming the
  offending flag, using Step 3's comparison.

Update the module docstring, which currently enumerates the two stamps and the
reasoning for treating them differently; the ruleset stamp is a third with its
own rationale (`ENGINE_SPEC_NAME` names the tensor-shape contract, so a
rules-only change leaves it untouched and the checkpoint would otherwise load
cleanly into a network evaluating under rules it never saw).

Depends on: Step 3 (the configuration representation and comparison). Step 6
cross-checks the run config against the stamp this step writes, so the stamp has
to exist first.

Verification (automated, then manual): `pytest tests/engines/neural_network/test_ctf_checkpoint.py`
covering the three outcomes — a save/load round trip preserves the
configuration; a checkpoint written without the key is rejected with a message
naming ruleset stamping; a checkpoint carrying an unknown flag is rejected with a
message naming that flag. Automated because constructing the middle two cases
means hand-writing checkpoint dictionaries, which the existing tests in that file
already do. Then manually: `python -m capture_the_flag.training_runner --generations 1 --games 1`
and confirm it completes and its checkpoint reloads — the round trip through the
real training path, not a synthetic dictionary.

---

### Step 6 — The run config records the ruleset

Add the resolved configuration to what `_write_run_config` records alongside the
hyperparameters, architecture, and seed, and have `resume_generations` adopt the
configuration from the checkpoint stamp while cross-checking it against the run
config — the same division `_check_architecture_agrees` already draws: the stamp
attached to the weights is authoritative, the run config is checked against it,
and a disagreement means the run directory is inconsistent and is refused rather
than silently resolved.

Depends on: Step 5 (the checkpoint stamp is what the cross-check compares
against). Nothing depends on this step.

Verification (manual): run
`python -m capture_the_flag.training_runner --generations 1 --games 1`, confirm
the new run's `run-config.json` carries the edition and flags in structured
form, then run
`python -m capture_the_flag.training_runner --resume --generations 1 --games 1`
and confirm the resume completes and appends a second checkpoint. Then, to
exercise the refusal, hand-edit the copied `run-config.json`'s edition to a
different id and confirm a further resume is refused with a message naming both
recorded values.

---

### Step 7 — Policy rewrite

Rewrite the policy in `doc/ruleset/technical-notes.md` and `doc/ruleset/CLAUDE.md`:

- **Retire "latest version only."** Replace it with the two-tier guarantee:
  view-only replay is guaranteed for all records by notation-schema stability
  alone; validated replay is guaranteed for published editions.
- **Rules changes land as flags with preserving defaults**, not as edits to core
  rules text. Restate the changelog/version-bump rule accordingly — a minor bump
  is registry growth, not a semantic break — and replace the instruction to bump
  `RULESET_VERSION` in `record.py`, which no longer exists, with the edition
  table it became.
- **Add the major-bump trigger list.** The notation marks survival on exactly the
  two squares of a ply, so the tape can express any combat outcome,
  distribution, or source→destination movement rule, but *not* a third-square
  side effect, a multi-piece ply, or a board-size change. Those require a major
  bump.
- **Record the documented risk:** nothing verifies that the rules the engine
  played match the flags it stamped. The stamp is asserted, not measured;
  Step 3's distribution cross-check narrows this to flag values only. Closing it
  means building the record reader this story excludes, and the natural
  mitigation — a replay corpus of kept records as regression tests — is deferred
  to a later story.
- Update the record-format section's `Ruleset` description, which currently
  specifies `VERSION:NAME` with a dot, to the edition form plus deviating flags,
  and note that flags render in alphabetical order.
- Add a `changelog.md` entry recording the convention change, the story number,
  and the date, stating explicitly that the minor is not bumped because no rule
  changed.
- **State that the document leads and the code follows.** The army composition is
  necessarily duplicated in three places (`rules.md` §2.2 and its Appendix B row,
  `pieces.py`, and the edition table), so `doc/ruleset/CLAUDE.md` names which of
  them is the definition and rules out the specific wrong move the duplication
  invites: editing the edition table to make the distribution test pass, which
  would retroactively falsify every artifact stamped with that edition.
- **Record how a composition flag composes with an edition's distribution** in
  `technical-notes.md`: the edition's distribution is the baseline and the flag
  deviates from it. This settles a question the story left out of scope
  (*defining* a flag) rather than answering it — no flag is defined here — but
  the two-claims-on-the-army problem is created by this story's model, and
  leaving the first implementer to improvise an answer is how an edition stops
  being immutable.

Depends on: Steps 3–6 (it names the constants and stamps they introduce) and
Step 2 (it points at the appendices as where rule changes now land).

Verification (manual): grep `doc/` for `RULESET_VERSION`, `latest version only`,
and the dotted `1.2:` form and confirm every surviving hit is either a
deliberate historical reference or corrected. Then read the record-format
section against the actual header a Step 4 record carries and confirm they
agree.

---

### Step 8 — README check

Run `/update-readme` to review the branch diff against `README.md` and update it
if warranted. The README describes the engine, the batch runner's record output,
and the training runner's run directory — all three surfaces this story touches —
so an update is likely rather than pro forma, in particular anywhere it describes
what a record or a run directory contains.

Depends on: Steps 1–7 (the diff it reviews is theirs).

Verification (manual): read the resulting `README.md` diff, or the statement that
no change was warranted, and confirm it matches what the branch actually changed.

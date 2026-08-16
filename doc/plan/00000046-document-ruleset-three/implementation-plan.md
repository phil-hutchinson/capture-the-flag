# Story 46 — Implementation Plan

Documentation only. There is no code in this story, so every step produces a
document and every verification is a read-through or a short improvised check.
The ordering is still bottom-up: each document depends on the ones before it
being settled, because each restates decisions the earlier ones fixed.

**Status: all steps complete.** Recorded here so the story has the plan the
repository convention expects.

---

### Step 1 — Shadow folder and its status statement

Create `doc/ruleset/proposed-3/` and its `README.md`, stating that everything in
the folder is a proposal, that nothing outside it may depend on it, and that the
published documents one level up are untouched. Include the reading order and the
rank-inversion hazard, since that is what a consumer needs before anything else.

Depends on: nothing.

Why it comes first: every later document inherits the "carries no promises"
framing from this one. Written last, there is a window in which a complete-looking
ruleset sits in the tree with nothing marking it as unpublished.

Verification (manual): read `README.md`, then run `git status --short` and confirm
the change set is additions only — no published document appears.

---

### Step 2 — The ruleset text

Write `proposed-3/rules.md`: the complete major 3 ruleset, player-facing,
self-contained, following the structure and the "move" terminology of the
published `rules.md`.

Depends on: Step 1 (the folder and its status statement).

Why it comes here: it is the definition. The start-position document, the notes
and the changelog all restate parts of it, so it has to be settled before any of
them can be written without risking drift.

Verification (manual): read end to end and confirm the game could be implemented
from this document alone, without opening the major 2 rules. Check specifically
that the five worked notation examples in §4.5 cover every combat outcome, that
the rank table reads 5-strongest, and that no rule anywhere refers to a piece by
name.

---

### Step 3 — The start-position document

Write `proposed-3/start-position.md`: the constrained set and its size, the
generation procedure, the strength rule that chooses between reflection and
half-turn, and the position-ID encoding.

Depends on: Step 2 (`rules.md` §3 states the same procedure at player level; this
is the implementer's copy and the two must agree).

Verification (improvised): a short script covering two things.

1. Recompute from first principles the three arrangement counts, and the
   43.17% / 56.83% branch split over all 6,435 piece splits weighted by
   arrangement count. A passing result is the same numbers as the document.
2. Confirm the `S ≥ 22` threshold and the strongest-seven formulation select
   identical positions. A passing result is zero disagreements across all splits.

The position-ID encoding needs no verification step of its own, which is the
point of choosing it: it is a per-square transcription rather than an algorithm,
so there is nothing to get subtly wrong and nothing an implementation could
compute differently. Confirm only that sixteen hexadecimal digits is 64 bits, and
that the document says to carry an ID as a string rather than as a number — a
JavaScript `Number` cannot hold one exactly.

---

### Step 4 — Technical notes

Write `proposed-3/technical-notes.md`: why this is a major bump, the rank
reduction design and its risks, the notation design, the encumbrance and
first-ply analyses, the attrition argument, and the edition and naming wrinkles.

Depends on: Steps 2 and 3 (it explains decisions those two documents make).

Verification (manual): read and confirm every claim either traces to a rule in
`rules.md` or is derived in place. The three arguments worth checking closely are
the no-floor property of rank reduction, the impossibility of being boxed in, and
the parity effect of the restricted first ply — each is stated as a derivation
rather than an assertion and should hold up when read as one.

---

### Step 5 — Changelog entry

Write `proposed-3/changelog.md`: the entry major 3 would publish, in the form the
front-end application tracks.

Depends on: Steps 2, 3 and 4 (it is the delta, so it can only be complete once
the ruleset is).

Why it comes here rather than being folded into the notes: the changelog has a
different audience and a different job. It is the only document written for
someone who already implements major 2 and wants the difference.

Verification (manual): read it as a major 2 implementer would and confirm it
lists every behavioural difference, and that the two changes which fail *silently*
rather than erroring — the reversed rank numbering and the reuse of piece names at
different ranks — are the first thing the entry says.

---

### Step 6 — Cross-document consistency

Check the five documents against each other: the constant 22, the arrangement
counts, the notation examples, and the piece table should agree everywhere they
appear, and every internal link should resolve.

Depends on: Steps 1–5.

Verification (improvised): a link-resolution script over all five documents in
`proposed-3/`, plus a
grep for the shared constants. A passing result is zero broken links and no
disagreement between documents.

---

### Step 7 — README check

Confirm whether `README.md` needs updating for this story.

Depends on: Steps 1–6.

**Outcome: no change needed, and none was made.** `README.md` describes the engine
this repository implements and the rulesets it publishes — three rulesets sharing
one rules text, runners taking `--ruleset battle|clash|skirmish`, records stamped
with a major 2 edition, and a two-phase game. This story publishes nothing,
implements nothing, and changes no published document, so every one of those
statements is still true. Major 3 becomes a README concern only if it is adopted
and implemented, which is explicitly out of this story's scope.

Verification (manual): re-read `README.md` against the branch diff and confirm no
statement in it is falsified. `/update-readme` reviews the same diff and should
reach the same conclusion.

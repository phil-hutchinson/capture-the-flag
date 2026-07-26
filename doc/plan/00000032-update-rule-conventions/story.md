# Story 32: Update Rule Conventions — Rulesets, Editions, and Rule Flags

## Summary

Replace the single mutable `<version>:<name>` ruleset identifier with a
**ruleset / edition / flag** model, so that rule variation becomes cheap and
every game record unambiguously states the rules it was played under.

A ruleset reduces to a **piece distribution plus a set of rule flags**. An
**edition** (`1-7:Standard`) is an immutable pairing of a ruleset name with
specific flag values; a **ruleset name** (Standard, Berserker, PRE-RELEASE) is
a mutable pointer to its current edition. Immutability attaches to published
labels — flag names, flag value labels, edition ids — rather than to frozen
copies of rules text or engine code.

This story covers the base repository's side: vocabulary, the rules document
restructure, record stamping, and checkpoint pinning. Because `doc/ruleset/` is
the source of truth for the separate front-end player application, whatever
this story establishes becomes that repository's standard too — the conventions
defined here are not local to this repo.

## Motivation

The current policy — every rules change bumps a version, and only the latest
version is supported — protects nothing pre-release while making rule
experimentation expensive: each tweak spawns a near-duplicate frozen version.
At the same time it under-protects the things that matter, because a trained
network carries no record of the rules it was trained under.

Under this model:

- Testing a variant requires a flag, not a version. Because every new flag's
  default is the behavior that was standard before the flag existed, adding a
  flag is a no-op for every existing edition and every existing record.
- Records become self-describing. A record states its edition id and its
  resolved flag values, so the rules it was played under are recoverable from
  the record alone.
- Trained networks pin an exact rules configuration and refuse to load against
  a different one.

The relationship with the front-end repository is **one-way**: this repo
*produces* records that application consumes; it does not consume records. That
bounds the scope sharply — this repo needs an accurate record *writer*, not a
reader, a parser, or a version-dispatch layer. Its whole obligation is to stamp
accurately what it actually played.

## Specification

### Vocabulary (root `CLAUDE.md`)

- **Ruleset** — a mutable name (Standard, Berserker, PRE-RELEASE).
- **Edition** — an immutable id, `<major>-<minor>:<Ruleset>`, resolving to a
  piece distribution plus explicit flag values.
- **Rule flag** — an enum-valued, behavior-preserving-by-default rules
  parameter.

Dashes rather than dots in the edition id (`1-2:` not `1.2:`), so the id reads
as a compound label rather than a decimal — and so minor 10 does not sort
before minor 2.

### Rule flags

- Always enum-valued, even when currently binary (`TOWER_MOVEMENT = on | off`),
  so a third value can be added later without a type change.
- Published flag names and value labels are permanent and never redefined; new
  behavior always gets a new label.
- Every flag's default is the pre-flag standard behavior, so retrofitting a
  flag never alters an existing edition or record.
- Created lazily — standard behavior stays unflagged until someone wants to
  test a variant of it.

### Rules document restructure (`doc/ruleset/`)

1. **Core rules** — unchanged in character: player-facing, no flag machinery.
2. **Variants appendix** — permanent and append-only. One entry per *published*
   flag in player-facing prose, carrying flag id, value labels, and default.
3. **Rulesets appendix** — two tables with identical fields:
   - **Active** — the current edition per ruleset name. `PRE-RELEASE` goes here
     now, and its edition is bumped as needed.
   - **Historical** — editions no longer pointed to, each labelled with why:
     *superseded* (a newer edition of the same ruleset exists) or *retired*
     (the ruleset name itself is no longer offered). Retirement is how
     `PRE-RELEASE` exits at release, with `STANDARD` (or whatever it is called)
     taking its place in Active.

   All editions are equally immutable regardless of which table they sit in;
   only the active pointers move.
4. **Proposed variants index** — the mutable sandbox. Entries are added,
   reworked, and deleted freely.

**Graduation rule:** a flag moves from the proposed index to the Variants
appendix only when its implementing branch merges. This makes it safe to land a
proposed flag in the rules document while its implementation lives in an
unmerged branch — an abandoned experiment deletes its proposed entry and
violates no permanence promise.

### Representing a resolved configuration

One representation serves both the record header and the checkpoint stamp: an
**edition id plus the flags that deviate from it**.

**Structured, not concatenated.** In the checkpoint the configuration is a
nested mapping, following the precedent the architecture stamp already sets:

```python
"ruleset": {
    "edition": "1-2:PRE-RELEASE",
    "flags": {"MOVABLE_TOWERS": "on"},
}
```

A concatenated string would need canonical flag ordering or two identical
configurations compare unequal — and structured comparison is what produces a
useful rejection message ("flag `MOVABLE_TOWERS`: checkpoint says `on`, running
code has no such flag") rather than two opaque strings differing somewhere. The
record file needs a string rendering because it is a text medium; that rendering
orders flags deterministically (alphabetically by flag id) so it is stable.

**Omit flags at their resolved value.** `1-2:PRE-RELEASE` with no flags listed
has a clear, well-defined meaning, and that is the standard used everywhere else
in this model. Omission is safe rather than merely tidy: because every default is
behavior-preserving by construction, an absent flag can never mean "something
happened that this code does not understand." It means the behavior the code
already implements. So the compatibility check only ever runs over the flags
explicitly listed — a small check, and no weaker for the omission.

**Resolution is two-level: absent is not the same as flag-default.** An edition
sets flag values, so a later edition may set `MOVABLE_TOWERS=on` as its edition
value while the flag's own default remains `off`. An absent flag therefore
resolves to *the edition's value*, falling back to the flag's default only when
the edition predates the flag's existence. A flag introduced after `1-2` (say
`DIAGONAL_ATTACK`, default `no` to preserve current behavior) hits the second
case and reads like a one-level lookup; a flag baked into a newer edition hits
the first.

**The edition is always present, even when no flags are listed.** Otherwise a
configuration meaning "all defaults" is indistinguishable from an artifact
written before stamping existed — both carry no flag information — yet the two
must be treated differently, and `ctf_checkpoint.py` already rejects unstamped
checkpoints rather than guessing. So `{"edition": "1-2:PRE-RELEASE", "flags":
{}}` is valid and means all-defaults, while a missing `ruleset` key is a
rejection.

### Record format (`capture_the_flag/record.py`)

- Replace the `RULESET_NAME` / `RULESET_VERSION` constants with an edition
  table (edition id → distribution + flag values) held as data.
- Stamp the edition id in full (`1-2:PRE-RELEASE`), never a bare name.
- Emit deviating flags per the representation above.

The first edition is `1-2:PRE-RELEASE`, carrying the current minor forward: this
story restructures the rules *document* without changing the rules themselves,
so there is no semantic change for a new minor to mark.

### Checkpoint pinning

Checkpoints must be tagged with the same identifiers as everything else here:
the edition id plus the resolved flag values. A trained network is only valid
for the rules it was trained under, so the tag is what makes that checkable.

This is a different and stricter statement than an engine spec's
compatible-rulesets list. That list is the **set** of rulesets an I/O contract
can serve — a lower bar, and many-to-one. A checkpoint's tag is the single
**point** in that set its weights actually occupy.

Checkpoints already stamp the engine I/O spec (`ENGINE_SPEC_NAME`) and the
architecture, so this is aligning identifiers rather than inventing a mechanism.
The spec stamp does not cover it: `ENGINE_SPEC_NAME` names the tensor *shape*
contract, so a rules-only change leaves it unchanged and the checkpoint loads
cleanly into a network evaluating under rules it never saw.

On resume, the tagged configuration is what the run continues under — adopted
from the stamp rather than taken from current defaults, exactly as the
architecture already is. A checkpoint trained with a flag on resumes with that
flag on even if the current default is off. Rejection is for the case where the
running code cannot implement the tagged configuration at all.

Backward compatibility is not the goal. The goal is **knowing** whether the
network matches the variant in play, and failing clearly when it does not,
instead of running silently against rules it was not trained for. The same
applies to the run config a resume rebuilds from, which currently records
hyperparameters, architecture, and seed but no ruleset.

### Policy rewrite (`doc/ruleset/technical-notes.md`, `doc/ruleset/CLAUDE.md`)

- Retire "latest version only." Replace with the two-tier guarantee: view-only
  replay is guaranteed for all records by notation-schema stability alone;
  validated replay is guaranteed for published editions.
- Rules changes land as flags with preserving defaults, not as edits to core
  rules text. Restate the changelog/version-bump rule accordingly — a minor
  bump is registry growth, not a semantic break.
- Add an explicit **major-bump trigger list**. The current notation marks
  survival on exactly the two squares of a ply, so the tape can express any
  combat outcome, distribution, or source→destination movement rule — but *not*
  a third-square side effect, a multi-piece ply, or a board-size change. Those
  require a major bump. Writing this down is what keeps a future story from
  breaking the front-end's review-only contract by accident.

### Documented risk: no check that play matches the stamp

Nothing verifies that the rules the engine actually played match the flags it
stamped into the record. The stamp is asserted, not measured. This is accepted
for now and recorded in `technical-notes.md` as a known gap rather than closed,
because closing it means building the reader this story deliberately excludes.

The natural mitigation — a replay corpus of kept records replayed as regression
tests — is deferred to a later story.

## Out of scope

- Any record reader, parser, or replay-validation path in this repo.
- The replay corpus as a regression suite (deferred; see the documented risk
  above).
- Actually defining or implementing any specific rule flag. This story builds
  the machinery; the first real flag comes later.
- The machine-readable form of the flag registry (document appendices only, vs.
  also a data file engines consume) — deferred.
- Supporting multiple simultaneously-live rulesets. The model permits it, but
  each live ruleset costs a separately trained network, so the practical limit
  here is training budget rather than code. Not exercised by this story.

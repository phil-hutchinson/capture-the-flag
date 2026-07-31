# Capture the Flag — Proposed Variants

**This document carries no promises.** Entries here are added, reworked, and
deleted freely. Nothing in it is published, nothing in it is permanent, and
nothing outside this file may depend on it — not the engine, not a record, not a
trained network, not the front-end player application. A proposal that is
abandoned is simply deleted, leaving no trace and breaking nothing.

Contrast [`rules.md`](rules.md) Appendix A, the **Variants** appendix, which is
the opposite in every respect: append-only, and its flag names and value labels
permanent once written.

**Terminology.** This file uses **rule flag**, the project's term (root
`CLAUDE.md`). `rules.md` says **variant** for the same thing, because it is
written for players — the same one-off audience exception that makes it say
"move" where everything else says "ply." One rule flag = one variant.

## The graduation rule

A rule flag moves from this file to Appendix A **when its implementing branch
merges** — not when it is designed, not when it is agreed to be a good idea, and
not while its implementation sits in an unmerged branch.

This is what makes the sandbox safe. A flag can be specified here in full detail,
reviewed, and iterated on while its implementation is still in progress, without
any of that provisional wording landing in a document that promises permanence.
An experiment that does not work out deletes its entry here and violates no
promise. Only a merge — the point at which the engine actually implements the
flag and can stamp it into a record — moves an entry across.

At graduation, the entry is rewritten for Appendix A's audience: player-facing
prose, no implementation detail, no rationale. Its identifier and value labels
carry across unchanged and become permanent at that moment, so those are worth
settling here rather than at the last minute.

## Proposal format

An entry should carry enough to be argued about and enough to be implemented
from:

- **Identifier** and its **value labels** — becoming permanent on graduation, so
  choose them as if they already were.
- **Default** — which value preserves current behavior. Every flag has one; a
  proposal whose default would change existing play is not a flag proposal, it is
  a rules change (see [`technical-notes.md`](technical-notes.md)).
- **What each non-default value does**, in enough detail to implement.
- **Why** — what the variant is meant to test or improve. This is the part
  Appendix A will not carry, so this file is the only place it is recorded.
- **Status** — free-form: under discussion, being prototyped, branch open,
  parked.

## Proposals

*(none)*

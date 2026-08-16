# Proposed Major 3 — shadow documents

**Nothing in this folder is published, and nothing outside it may depend on it.**
These are *shadow* copies: proposed replacements for the documents one level up,
written so that a proposal can be read, argued about and prototyped without
touching a single published document. No edition is published, no ruleset
pointer moves, and `2-0:BATTLE`, `2-0:CLASH` and `2-1:SKIRMISH` are entirely
unaffected. When and if major 3 is adopted, these documents are merged into or
replace their counterparts; if it is abandoned, this folder is deleted and
nothing breaks.

| Shadow document | Counterpart | What it holds |
|---|---|---|
| [`rules.md`](rules.md) | [`../rules.md`](../rules.md) | the complete proposed ruleset, player-facing and self-contained |
| [`start-position.md`](start-position.md) | *(new)* | how a starting position is generated, and how a position ID encodes one |
| [`technical-notes.md`](technical-notes.md) | [`../technical-notes.md`](../technical-notes.md) | design rationale, derivations, and consumer-facing hazards |
| [`changelog.md`](changelog.md) | [`../changelog.md`](../changelog.md) | the entry this change *would* publish, in the form consumers track |

## If you are implementing this

Read [`rules.md`](rules.md) and [`start-position.md`](start-position.md). Those
two are complete: everything needed to build and play the game is in them, and
neither requires reading the major 2 rules first.

Read [`changelog.md`](changelog.md) if you already implement major 2 and want the
delta rather than the whole ruleset.

[`technical-notes.md`](technical-notes.md) explains *why*, and is not needed to
implement anything — with one exception worth calling out here, because it is the
change most likely to break an existing renderer silently:

> **Rank numbering is reversed at major 3, and piece names are reused at
> different ranks.** At major 2, rank 1 is the *strongest* piece and is named
> Master-of-Arms. At major 3, rank **5** is the strongest and rank 1 the weakest,
> and "Foot Soldier" — rank 5 in `2-0:BATTLE` — is rank **3** here. A consumer
> that keys artwork or strength off a rank digit alone, or off a piece name, will
> be wrong in both directions without erroring. **Key off the pair
> `(major, rank digit)`, never off a name.**

## Status

Proposed. Story
[00000046](../../plan/00000046-document-ruleset-three/story.md). This story is
documentation only: no code, no engine change, no published edition.

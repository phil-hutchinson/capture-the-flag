# Story 34: Rule Change — Diagonal Attack and Board Sizing

## Summary

Publish **major 2** of the ruleset. Three things land together, because the
first of them forces a major bump and the others are worth spending it on:

1. **The notation becomes size-parametric.** A record's board is a rectangular
   grid whose dimensions are read from its position block, rather than a fixed
   12 × 12 with the coordinate frame baked in. This is the break the front-end
   player application cannot absorb, and it is what a major bump is *for*.
2. **Diagonal attack enters the baseline rules.** A piece may attack a square on
   its immediate diagonal, but only when the occupant is a movable piece.
3. **Board layout and army composition become rule flags**, and two rulesets are
   published in parallel: `2-0:BATTLE` on the current 12 × 12 board and
   `2-0:SKIRMISH` on a new 8 × 8 board with a 16-piece army. `PRE-RELEASE` is
   retired.

Alongside these, the **edition** model itself is adjusted: an edition stops
carrying a piece distribution as its own axis and becomes a major baseline plus
a complete set of flag values.

**This story is documents only. It contains no code.** See
[Scope and the merge constraint](#scope-and-the-merge-constraint) — the branch
must not reach `main` until the rules it publishes are actually implemented.

## Motivation

### Board sizing

A smaller board serves two purposes at once, for closely related reasons:

- **Training.** An 8 × 8 board with 16 pieces per side is a materially smaller
  problem than 12 × 12 with 25. Self-play should reach a competent engine sooner,
  which means usable results sooner and a shorter feedback loop on everything
  downstream.
- **Human play.** The same reduction makes the game easier for a new player to
  absorb. A shorter game on a smaller board with four ranks instead of six is the
  better introduction, and is worth having as a real, maintained ruleset rather
  than a teaching aid.

Whether a network trained on the small board can be reused on the large one is an
open and desirable question, not a requirement. Convolutional layers are
size-agnostic in principle; whether this project's architecture actually
transfers is unexamined and out of scope here.

### Diagonal attack

The intent is to make play **more direct**. Under orthogonal-only attacks a piece
can evade an approaching attacker by stepping off its line, and the attacker must
spend plies re-establishing contact — pressure leaks away and the game slows.
Adding the diagonal closes those escapes: a piece adjacent to an enemy is
adjacent for attack purposes in all eight directions, so shuffling away from a
threat stops being cheap.

The expected secondary effect is that **stronger pieces can corner and capture
weaker ones more readily**. Under orthogonal-only movement a weaker piece has
diagonal escape squares that no adjacent attacker can contest; removing them
makes material superiority easier to convert.

Restricting the diagonal to *attacks on movable pieces* is what keeps this from
being a general mobility increase. Diagonal movement without an attack would
change the whole geometry of maneuvering rather than the geometry of contact,
and excluding the Flag and Towers means the Flag's defensive perimeter — the
thing the tower-adjacency placement rule was shaped around — is unchanged.

### Why now, and why together

`technical-notes.md` names a board-size change as one of exactly three things
the notation cannot express, so any variable board size costs a major bump and a
coordinated front-end change. That cost is the reason to spend it well:

- Version 2's notation is written to be **size-parametric from the outset**, so
  the major is paid once. Any future board — different dimensions, different
  lake pattern, different home-zone depth — is a new flag value, not a new major.
  This does not mean anything goes: a new layout still has to be named as a flag
  value before it can be played or stamped.
- **Diagonal attack rides along as baseline** rather than as a flag. It would
  otherwise have to be a flag with a preserving default, per the standing rule
  that new behavior lands as a flag; but a major bump is already republishing the
  baseline rules text, so the simpler outcome is available and worth taking. On
  its own, diagonal attack would not have justified a major — the notation
  absorbs it without change.

Note that story 18 deliberately *avoided* a major bump for breaking changes on
the grounds that pre-release protects nothing. That reasoning no longer applies:
story 32 redefined a major as specifically a **notation** break, whose cost is
borne by an external consumer. This bump is being taken because the notation
genuinely changes, not because the rules do.

## Specification

### 1. Major 2 — size-parametric notation

The current notation fixes a 12 × 12 grid, columns `A`–`L` and rows `1`–`12`.
Version 2 generalizes it:

- A board is a **rectangular grid** whose dimensions are read from the record's
  position block. The block already renders one fixed-width cell per square, one
  line per row, so both dimensions follow from counting.
- **Lake layout is likewise recoverable** from the block, which already
  distinguishes lake (`XXX`) from empty (`---`).
- The coordinate frame extends unchanged: **letters across, numbers up**, row 1
  being White's back rank. This supports up to 26 columns before it needs
  rethinking, which is well beyond any layout contemplated here.
- Ply strings are unaffected in form — still source-then-destination, with
  survival marked per square in the extended form.

**What does not come free.** The **home-zone row count is not recoverable** from
a position block, because a mid-game position does not reveal where home zones
were. This is fine for a review-only viewer, which needs to render and step
through a record rather than validate placement, but the position block must not
be described as fully self-describing. Anything needing home zones reads them
from the configuration's `BOARD_LAYOUT` value.

**No document fork.** A major bump does *not* create a new set of rules
documents. `rules.md` is rewritten in place. Story 32 settled the principle —
immutability attaches to the published label, not to a frozen copy of rules text
or engine code — and `technical-notes.md` already states that validating a record
written under a historical edition means checking out the build that implemented
it. Retention is the Appendix B row plus the commit history.

### 2. Diagonal attack

Added to the baseline rules text (`rules.md` §4.2/§4.3), not behind a flag.

- A piece may attack a square on its **immediate diagonal** — one square only.
- **Only when the occupant is a movable piece.** A Flag or a Tower may not be
  attacked diagonally.
- **Diagonal movement without an attack is not allowed.** The diagonal is an
  attack direction only.
- **Both sacrifice types are permitted** for a diagonal attack: complete
  (attacker removed, defender survives) and partial (both removed).

**Consequences, all intended, and to be stated where a player will find them:**

- The **Flag can still only be captured orthogonally.** This is a strategic
  consequence, not a technicality, and belongs near the win condition as well as
  in the combat section.
- **Tower attacks remain orthogonal-only**, so the partial sacrifice a tower
  attack produces is not available on the diagonal.
- A piece making a diagonal attack is **by definition encumbered** — its target
  occupies one of its eight surrounding squares — so the unencumbered two-square
  bonus can never interact with a diagonal attack. No wording is needed to hold
  them apart.
- The **formation bonus is direction-independent** (a friendly piece of equal
  rank within one square, checked before the attacker's move and at the moment a
  defender is attacked) and therefore applies unchanged to diagonal attacks.
- The **notation is unaffected**. A diagonal attack is a source and a
  destination with survival marked per square, exactly as an orthogonal one.
- The **inactivity counter** treats a diagonal attack like any other: any removal
  resets it.

Both published rulesets get diagonal attack — it is baseline behavior at major 2,
not a per-ruleset setting.

### 3. Editions redefined

**An edition is a major baseline plus a complete set of flag values.**

This replaces story 32's "a piece distribution plus explicit rule flag values."
Two changes:

- **Piece distribution stops being an axis of an edition.** It becomes the
  resolved value of a flag like anything else. The consequence is that the
  `ARMY_COMPOSITION` flag and the edition no longer both have a claim on the
  army.
- **The `technical-notes.md` carve-out is removed.** The paragraph under "Flags
  over army composition" that resolves the two-claims problem — "the edition's
  distribution is the baseline, and the flag deviates from it" — has nothing left
  to arbitrate and should go rather than sit as dead reasoning. The surrounding
  point it was making (that a composition change is the sharpest case for the
  checkpoint pin, because it changes what per-rank quantity features *mean*
  while leaving the tensor shape and `ENGINE_SPEC_NAME` untouched) is still true
  and should be kept.

**The major names the baseline, and flags parameterize within it.** This
qualification is load-bearing: diagonal attack is baseline at major 2 with no
flag distinguishing it from major 1, so `1-2:PRE-RELEASE` and `2-0:SKIRMISH` are
*not* two points in one flag space. Without the qualification the vocabulary
would claim something the model does not deliver.

**Minor is namespaced per ruleset; major is global.** `2-0:BATTLE` and
`2-0:SKIRMISH` share a major because they share a notation and a baseline. Their
minors advance independently — `BATTLE` moving to `2-1` does not disturb
`SKIRMISH` at `2-0` — while a future notation break moves both to major 3.

**Appendix B's fields change shape.** The table currently carries an "Army
composition" column alongside "Variant values"; army composition is now one of
the variant values. The table should still render a player-readable statement of
board and army rather than making a reader resolve flag names, but it does so as
a presentation of flag values, not as a separate field with independent
authority.

Root `CLAUDE.md`'s **Edition** entry is updated to match, as is the
corresponding paragraph in `technical-notes.md`.

### 4. The first two published flags

Both are published to `rules.md` Appendix A. Identifiers and value labels become
permanent on publication.

#### `BOARD_LAYOUT = standard_144 | standard_64`

Default: **`standard_144`**.

A value names a **complete layout**, not merely a size: grid dimensions, the
home-zone row count, and the lake pattern. This is what keeps board geometry from
needing several independent axes — an 8 × 8 board with two home rows instead of
three is a *different value* (`small_home_zone_64` or similar), not a second
parameter.

| Value | Grid | Rows | Lakes |
|---|---|---|---|
| `standard_144` | 12 × 12 | 4 home / 1 buffer / 2 lake / 1 buffer / 4 home | `O L L O O L L O O L L O` (§2.1) |
| `standard_64` | 8 × 8 | 3 home / 2 lake / 3 home | two 2 × 2 lakes, single lane at each edge, double lane through the middle |

#### `ARMY_COMPOSITION = standard_battle | standard_skirmish`

Default: **`standard_battle`**.

| Value | Army |
|---|---|
| `standard_battle` | 3 each of ranks 1–6, 6 Towers, 1 Flag — 25 pieces |
| `standard_skirmish` | 3 each of ranks 1–4, 3 Towers, 1 Flag — 16 pieces |

#### Defaults and the permanence promise

Both defaults are what `1-2:PRE-RELEASE` played. This is not cosmetic: the
standing promise is that introducing a flag alters no existing edition and no
existing record, and it holds here only because the defaults reproduce the
pre-flag behavior exactly.

Neither flag will ever appear as a deviation in a record or a checkpoint, since
both published editions set both values explicitly and a flag at its resolved
value is omitted. `technical-notes.md`'s canonicalization rule means even a stamp
that did write one out is normalized back to omission. **A flag that exists, is
authoritative, and never appears in any artifact is a well-formed outcome under
this model**, and Appendix A should not imply otherwise.

#### Invalid combinations

The two flags are independent, so combinations exist that cannot be played — most
obviously `standard_battle` on `standard_64`, where 25 pieces do not fit 24 home
squares. **Such a configuration is invalid for play** and Appendix A should say
so where it introduces the flags.

This constrains *playing*, not *viewing*. A viewer renders from the record's
position block, which may be a mid-game position that never had a placement phase
to be valid or invalid — so a viewer needs no notion of a legal army/board
pairing.

### 5. Rulesets and editions published

**Active**

| Edition | `BOARD_LAYOUT` | `ARMY_COMPOSITION` |
|---|---|---|
| `2-0:BATTLE` | `standard_144` | `standard_battle` |
| `2-0:SKIRMISH` | `standard_64` | `standard_skirmish` |

**Historical**

| Edition | Status |
|---|---|
| `1-2:PRE-RELEASE` | retired |

`PRE-RELEASE` exits exactly as story 32 anticipated: the ruleset *name* is no
longer offered, so its edition is marked **retired** rather than superseded, and
stable names take its place in Active.

**Two rulesets are live simultaneously.** Story 32 explicitly listed this as out
of scope, on the grounds that each live ruleset costs a separately trained
network. That constraint is real and unchanged — it is accepted here rather than
dissolved, because the training plan is sequential: `SKIRMISH` first, precisely
because it is the smaller problem. This story supersedes that scope exclusion and
should say so rather than leave the two documents in silent contradiction.

### 6. The SKIRMISH board and army

Specified here because it is new; `BATTLE` is the current board and army
unchanged.

**Board — 8 × 8.** Rows, from one player's side to the other:

| Rows | Region |
|---|---|
| 3 | Player A home zone |
| 2 | Lakes |
| 3 | Player B home zone |

There is **no neutral buffer row**. Home zones sit directly against the lake
rows.

**Lakes.** Across the 8 columns, where `O` is open and `L` is lake:

```
O L L O O L L O
```

Two separate 2 × 2 lakes, single-column lanes at the two far edges and a
double-column lane through the interior — structurally the same shape as the
12 × 12 pattern, scaled down.

**Army — 16 pieces.**

| Rank | Piece | Qty |
|---|---|---|
| 1 | Master-of-Arms | 3 |
| 2 | Champion | 3 |
| 3 | Knight | 3 |
| 4 | Halberdier | 3 |
| — | Tower | 3 |
| — | Flag | 1 |

Ranks 5 and 6 (Foot Soldier, Militia) do not appear.

**Coordinates:** columns `A`–`H`, rows `1`–`8`; row 1 is White's back rank.

**Placement rules are unchanged**, including the prohibition on placing two
towers adjacent to each other (orthogonally or diagonally). Three towers in 24
home squares leaves ample room.

**This is a sharper game, not merely a smaller one**, and the rules should not
pretend otherwise:

- The home zone is 3 × 8 = **24 squares for 16 pieces — 67% filled**, against
  48 squares for 25 pieces (52%) on `BATTLE`.
- With no buffer rows, the two front ranks are **3 rows apart instead of 4**, and
  front-rank pieces start adjacent to the lake rows.

Contact therefore happens sooner and there is less room to maneuver. This is
deliberate and part of what makes it the faster game.

### 7. `rules.md` §2 — two boards presented in parallel

§2.1 and §2.2 currently state the grid, the lake pattern, the row layout, and the
25-piece army as flat facts: the game *is* those things. With two boards this is
no longer true.

**Both layouts are presented as parallel statements, as equals** — not one
primary with the other as a variant, and not a parametric §2 that bounces the
reader to an appendix on first contact.

**`SKIRMISH` is recommended as the entry point for a new player.** This is a
recommendation in the surrounding prose, not a claim of primacy in the structure:
the smaller board with four ranks is the easier game to learn, which was part of
the point of building it.

### 8. A build implements every Active edition

`technical-notes.md` currently states flatly that **"a build implements exactly
one edition: `ACTIVE_EDITION`."** With two Active editions this is false, and the
statement is load-bearing — it is the stated justification for rejecting a
checkpoint stamped with a historical edition.

Replace it: **a build implements every Active edition, and the configuration is
selected at run time.** A training run or a game is launched against `BATTLE` or
`SKIRMISH`, and every artifact it writes is stamped with the configuration it was
actually playing.

**The historical-edition rejection survives intact**, with its reasoning
corrected: a historical edition is rejected because it is *not Active* — the
rules changed, so a run resuming from it would train under rules its weights
never saw — not because a build can only hold one edition.

**What a checkpoint's stamp is compared against changes**: no longer a single
build-level constant, but the configuration the run is playing.

The engine-side consequence, for the implementation story rather than this one:
`pieces.py`'s single `ARMY_ROSTER`, and the `tests/test_record.py` assertion that
the active edition's distribution equals it, both become **per-edition**. This is
the sharpest code implication of this story and is noted so it is not discovered
late.

### 9. Documents to change

| Document | Change |
|---|---|
| `doc/ruleset/rules.md` | §2 parallel layouts; diagonal attack in §4.2/§4.3 and §5.1; glossary; Appendix A gains its first two entries; Appendix B publishes the two editions and retires `1-2:PRE-RELEASE` |
| `doc/ruleset/technical-notes.md` | size-parametric notation and the revised major-bump list; edition redefinition; remove the composition carve-out; replace the single-edition-per-build statement; note the home-zone/position-block limit |
| `doc/ruleset/changelog.md` | one entry per published edition, newest first, recording story 34 and the date |
| `doc/ruleset/CLAUDE.md` | the "document leads, code follows" table still names the army in three places; realign to the new model |
| `CLAUDE.md` (root) | the **Edition** vocabulary entry |

`doc/ruleset/proposed-variants.md` is **unchanged**, including its graduation
rule — see below.

## Scope and the merge constraint

**This story changes documents only. It contains no code.**

That leaves the repository temporarily describing a game it does not implement:
`record.py` would stamp a retired edition, `pieces.py` holds one army, and the
engine plays 12 × 12 orthogonal-only. `doc/ruleset/CLAUDE.md`'s "the document
leads; the code follows" sanctions the documents moving first, but this gap is
wider than that rule was written for.

**The constraint that resolves it: this branch does not merge to `main` until the
rules it publishes are implemented.** The implementation is expected to be a
separate story, landing on top of this one before either reaches `main`.

This is also what keeps the **graduation rule** intact rather than amended. That
rule — a flag reaches Appendix A when its implementing branch merges — exists so
no provisional wording lands in a document that promises permanence. Publishing
`BOARD_LAYOUT` and `ARMY_COMPOSITION` to Appendix A on an unmerged branch honors
it exactly, because graduation is merge to `main`, and that will not happen
before implementation. The rule is left alone.

Everything this story publishes is nevertheless a **permanent go-forward
change**: the flag identifiers, the value labels, and the two edition ids are
chosen as if already permanent, because on merge they will be.

## Out of scope

- **All code.** No engine, record, checkpoint, or test changes.
- **Tuning the inactivity counter per edition.** 50 plies was set for 25 pieces
  on 144 squares and plausibly means something different on `SKIRMISH`, where
  contact comes sooner and there is less board to maneuver on. Diagonal attack
  pushes the same way on both boards, since evading a threat gets harder and
  non-capturing sequences should get shorter. Deliberately left alone until games
  have been watched; it remains the natural first candidate for a tuning flag.
- **Network architecture and cross-board transfer.** Whether a `SKIRMISH`-trained
  network can be reused or grown onto `BATTLE` is desirable but unexamined, and
  nothing here depends on the answer.
- **Rank-selection schemes for transfer training** — e.g. training `SKIRMISH` on
  four *consecutive* ranks chosen at random from the six, so the small board
  exercises all of them. Noted as a future direction; not part of this story, and
  not reflected in `standard_skirmish`, which fixes ranks 1–4.
- **Any third board layout**, and any layout flag value beyond the two published
  here.
- **A record reader, parser, or replay-validation path**, still absent by design
  and unchanged by this story.

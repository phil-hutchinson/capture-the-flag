# Capture the Flag — Ruleset Technical Notes

Companion to [`rules.md`](rules.md). `rules.md` is deliberately kept clean enough
to hand to a player as-is, so anything that is really a developer- or
design-facing annotation lives here instead. Nothing in this file changes how the
game is played; it records metadata, provisional values, and cross-references to
the rest of the project.

Terminology follows the project standard: this file says **ply** where
`rules.md` says **move**, for the same player-audience reason. One move = one
ply.

## Rulesets, editions, and flags

- **Active edition:** `3-0:PRE-RELEASE`. The full list, active and historical, is
  [`rules.md`](rules.md) Appendix; the revision history is
  [`changelog.md`](changelog.md).
- `rules.md` is the **single source of truth** for the ruleset: the engine
  implementation, tests, evaluators, and any external consumer are checked against
  it. If code and `rules.md` disagree, that is a bug, and `rules.md` is the
  reference.
- A **ruleset** is a mutable name (`PRE-RELEASE`); an **edition**
  (`<major>-<minor>:<Ruleset>`) is an immutable pairing of that name with a major
  baseline and a complete set of flag values; a **rule flag** is an enum-valued
  parameter whose default is always the behavior that predated it. The root
  [`CLAUDE.md`](../../CLAUDE.md) carries the definitions; `rules.md` says
  *setting* where this file says *flag*, for the same player-audience reason it
  says *move* where this file says *ply*.
- **Major 3 publishes no flags**, so `3-0:PRE-RELEASE` is defined entirely by its
  baseline rules text — the zero-flags case of the same rule that made piece
  distribution the resolved value of `ARMY_COMPOSITION` at major 2: nothing but
  the major's own definition ever has a claim on what an edition means.
- The rules are also consumed by a separate front-end player application, which
  tracks the changelog to know when and how to update — a reason the edition
  registry and changelog are load-bearing, not decorative.

### What is guaranteed, and to whom

Two guarantees govern every artifact, at different strengths:

- **View-only replay is guaranteed for all records, forever.** A record can be
  read, its position block rendered, and its move sequence stepped through by
  notation-schema stability alone — no rules knowledge required. This holds for
  every record ever written, under any edition, and survives every minor bump
  and every major bump alike.
- **Validated replay is guaranteed for published editions.** Confirming that each
  move in a record was *legal*, and that the outcomes it marks are the ones the
  rules produce, requires implementing that edition. That is guaranteed for
  editions published in `rules.md`'s Appendix, which is why editions are
  immutable and are never removed from the table once published.

The second guarantee is about the *edition* staying implementable, not about any
one build implementing every edition ever published. **A build implements every
edition in the Active table.** With one Active edition, that table has one row;
the mechanism does not depend on that, and held two rows at major 2.

The edition table also retains **historical** editions, so that a stamped
artifact still names something meaningful and the row it names is still there to
be read — not because the running code can play them. Validating a record written
under a historical edition therefore means checking out the build that
implemented it, and for a historical edition at an earlier *major* that build
also implemented different rules text, since `rules.md` carries only the current
major.

This is why a checkpoint stamped with a historical edition is *rejected* rather
than accepted on the strength of the table containing its id. `2-0:BATTLE`,
`2-0:CLASH` and `2-1:SKIRMISH` fail this way now: the edition is **not Active**,
so a run resuming from one of them would train under rules its weights never
saw. A stamp from major 2 in fact fails on two counts — a historical edition, and
flags this build no longer carries at all — and both are worth reporting, since
either is enough on its own to explain the refusal to whoever is holding the
artifact.

### How a rules change lands

**Rule changes land as flags with preserving defaults**, not as edits to the core
rules text. A flag is proposed in
[`proposed-variants.md`](proposed-variants.md), implemented behind a flag whose
default is the current behavior, and graduated to `rules.md`'s Appendix when its
branch merges. Because the default preserves existing behavior, adding a flag is
a no-op for every existing edition and every existing record. Major 3 currently
has none; the first one to be proposed has an empty Appendix to land in.

Editing the core rules text directly is still correct for a **clarification** —
better wording, a worked example, a resolved ambiguity. The test is behavioral:
if every game legal under the old wording is still legal under the new one and
resolves the same way, it is a clarification. If not, it is a rules change and
needs a flag or a new edition.

The one exception is a **major bump**, which republishes the baseline rules text
and can therefore carry a behavior change unflagged — see "What forces a major
bump" below. Diagonal attack landed this way at major 2, and rank reduction,
the generated start, and the retirement of major 2 itself landed this way at
major 3. Do not read this as a general escape hatch: a major bump is justified by
a notation break, not by a wish to avoid a flag, and behavior only rides one that
is already happening.

### What forces a major bump

A major bump is a break in the **notation**, not in the rules — it is what the
front-end application cannot absorb, so it is worth stating exactly.

The notation marks the fate of a piece on each square it touches, on a
rectangular grid whose dimensions are read from the record's position block.
Within that envelope, the tape can express anything:

- any combat outcome, including new ones, and now a survivor's new rank (`=N`);
- any piece distribution, including new ranks or symbols;
- any source→destination movement rule, however exotic the path — diagonal
  attacks needed no notation change at all, and neither did rank reduction;
- **any board size**, up to 26 columns, which is where the single-letter column
  names run out.

None of those force a major bump. These do, because the tape has nowhere to put
them:

- **A third-square side effect** — a ply that changes a square other than its
  source and destination (an area attack, a piece pushed to a third square, a
  bystander removed).
- **A multi-piece ply** — one ply moving two pieces (castling-like, or a
  formation advancing together).
- **More than 26 columns** — the column names would need a second character, and
  every coordinate in every ply string changes width.
- **Redefining what a symbol already published means** — inverting the rank
  numbering, as major 3 did, redefines what every digit in every existing record
  means. That is not expressible by adding to the notation; it can only be done
  by declaring a new major and leaving old records under the old one.

Any of those needs a new notation, a new major, and a coordinated front-end
change. Writing this down is what keeps a later story from breaking the
review-only contract by accident.

**A major bump also republishes the baseline rules text**, which is a second
thing it does and worth separating from the notation break. `rules.md` carries
one major at a time, so a behavior change can ride a major bump as baseline
rather than as a flag. That is the *only* circumstance under which new behavior
legitimately lands unflagged; absent a major bump, "How a rules change lands"
above applies without exception.

### Where a configuration is stamped

One representation serves every artifact: **an edition id plus the flags that
deviate from it**. It is written three places, in two forms.

| Artifact | Form | Purpose |
|---|---|---|
| Game record, `Ruleset` tag | rendered string | states the rules a stored game was played under |
| Checkpoint, `ruleset` key | nested mapping | pins the rules a network's weights were trained under |
| `run-config.json`, `ruleset` key | nested mapping | reproduces the rules a training run was conducted under |

The string form exists only because a record file is a text medium; everywhere
else the configuration is structured, following the precedent the architecture
stamp already set. Structure is what makes a rejection legible, and it removes
any need for canonical ordering when comparing.

**A checkpoint's stamp is a stricter statement than a compatible-rulesets list.**
Such a list is the *set* of rulesets an I/O contract can serve, many-to-one; a
checkpoint's tag is the single *point* in that set its weights actually occupy. A
network is only valid for the rules it was trained under, and the engine spec
stamp does not cover this — it names the tensor *shape* contract, so a rules-only
change leaves it untouched and the weights would load cleanly into a network
evaluating under rules they never saw.

On load, a checkpoint's configuration is **adopted** where there is something to
adopt it for: a resumed run reads the stamp first and continues under it rather
than under current defaults, so a run trained with a flag on resumes with it on
even if the default has since changed. Adoption reaches the artifacts, not just
the decision to proceed — the checkpoints a resume appends are stamped with the
configuration it adopted, so a run's later generations are never re-tagged with
an edition they were not trained under.

Rejection covers three cases. A configuration the running code **cannot
implement** at all, which includes a *historical* edition, per the guarantee
above. A configuration that is **missing** — an unstamped artifact cannot say
what it was trained under, and defaulting it would assert something unknown. And
a configuration that is implementable but **not the one being played** — the
build's single Active edition does not by itself guarantee a checkpoint was
trained under it, once more than one edition is Active again. That last check is
against the run's own configuration, not a build-level constant.

A configuration is also **canonicalized when read**: a stamp that lists a flag at
the value it would resolve to anyway is normalised to one that omits it. The two
mean the same thing, but only the canonical one renders as the same string and
compares equal, and this code reads stamps it did not write.

### Known gap: nothing checks that play matches the stamp

**The stamp is asserted, not measured.** Nothing verifies that the rules the
engine actually played match the edition and flags it stamped into a record or a
checkpoint. If the engine's implementation drifts from `rules.md`, or a flag is
read in one code path and ignored in another, the artifacts will say so anyway.

This is accepted for now rather than closed, because closing it means building a
record *reader* — a parser and replay-validation path — which this repository
deliberately does not have: it produces records for the front-end application and
never consumes them. The natural mitigation is a corpus of kept records replayed
as regression tests, deferred to a later story.

---

## Why this was a major bump

Most of what major 3 changes could have been expressed within major 2's existing
model, as rule flags with behaviour-preserving defaults: an open board with no
lakes is a `BOARD_LAYOUT` value, a five-rank tower-less army is an
`ARMY_COMPOSITION` value, and the direction-relative encumbrance, the generated
start and the opening restriction are all ordinary flags. None of those forces
anything.

**Two changes did.**

### 1. The rank numbering is inverted

Major 2 published rank `1` as the strongest piece. Major 3 makes `5` the
strongest and `1` the weakest. A rank digit is not an internal detail: it is the
symbol written in every position block of every record. Making `1` mean the
opposite of what it had always meant **redefines a published symbol**, which
major 2's permanence promise existed to forbid.

It could not be a flag either. A flag would make the meaning of a glyph depend on
a setting, so a renderer would have to resolve a flag value before it could draw
a board — worse than the break it was avoiding. Inverting the numbering is only
coherent as a property of a rules text, which is what a major is.

**Why invert it at all?** Only that "bigger number is stronger" is what people
expect, and the cost of being counter-intuitive is paid forever by every new
player and every new consumer. There is no mechanical argument either way. It was
worth doing precisely because it could only be done at a major bump, so a bump
happening anyway was the moment to spend it.

### 2. Rank reduction breaks replay-by-schema

Major 2 guaranteed that view-only replay works for every record, forever, by
notation-schema stability alone — a reader steps a record by moving a piece
from the source square to the destination and applying the survival marks, with
no knowledge of the rules required.

Rank reduction breaks that. The piece arriving at the destination is a *different
rank* from the one that left the source, and nothing in the major 2 tape says so.
A consumer stepping such a record would render every post-combat board wrong, and
would do it silently.

The fix is to put the resulting rank in the notation — the `=N` mark — which is a
notation change, and a notation change is exactly what a major is for. The
guarantee then survives intact: a reader still needs no rules knowledge, because
the tape now states the outcome rather than implying it.

### What did *not* force it

For the record, since it constrains what may ride a future bump: removing the
lakes and the Towers, changing the army, changing the board's home-zone depth,
and adding the generated start would all have been expressible under major 2's
notation without any change at all. They rode this bump because it was
happening, not because they required it.

---

## Rank numbering, and why names are not anchored

**The number is normative; the name is flavour.** Every rule in `rules.md` is
stated in rank numbers, and nothing — not the notation, not the position block,
not any rule — refers to a piece by name. The names exist so players have
something to say.

**The name set is not anchored at either end.** A future rank could take the top
of the order, the bottom, or be inserted in the middle, and existing names could
be reused, moved or replaced. This is not an oversight to be tidied up later: it
is the point of making numbers normative. Anchoring the names — promising that
the strongest is always the Master-of-Arms, or that rank 1 is always the Peasant
— would create a second thing with a claim on what a piece *is*, and the whole
reason for the rule is that there should only be one.

The practical consequence, which belongs in front of anyone building a consumer:

> **Piece names carry no permanence guarantee.** They are not part of the
> notation, they are not stable across editions, and the same name may denote
> different ranks in different editions. `Foot Soldier` is rank 5 in
> `2-0:BATTLE` and rank 3 in `3-0:PRE-RELEASE`.

Combined with the inversion, this gives consumers a single rule: **key off
`(major, rank digit)`, never off a name, and never off a digit alone.**

---

## Rank reduction

### The design

Every piece that survives a fight is reduced by one rank. Three things follow
that are worth having stated rather than discovered.

**Strength decays monotonically.** Total army strength only ever falls, so
material converges over the course of a game and the major 2 endgame in which one
surviving top-rank piece mops up an exhausted opponent cannot occur. This is the
main reason for the mechanic.

**Using your best piece costs you.** Winning with the weakest sufficient piece is
strictly correct, so top-rank pieces become assets to be held back rather than
driven forward. That is a real and intended tension — power carries a running
cost — but it is also the mechanic's clearest risk: it may produce passivity from
exactly the pieces that ought to be creating threats. It is the first thing to
watch when the game is played.

**Cheap pieces become erosion tools.** Throwing a rank 1 at a rank 5 costs a rank
1 and leaves the opponent a rank 4. Three such sacrifices grind a 5 down to a 2.
This makes the complete sacrifice — very nearly a dead move at major 2 — into a
core tactic, and it is **intended**, not a side effect to be designed against.
How often it is actually advantageous is a question for play rather than for
argument.

### No floor rule is needed, and this is a theorem

`rules.md` states that no piece can be reduced below rank 1, and states it as an
observation rather than as a rule, because it is one:

> The winner of a decisive combat is always the stronger piece, so a survivor is
> always rank 2 or higher. A rank 1 draws against another rank 1 and loses to
> everything stronger; the formation bonus only ever converts a loss into a mutual
> removal, so it produces no survivor either. **A rank 1 never survives combat.**

Do not add a defensive "minimum rank 1" clause. It would be unreachable, and it
would obscure the fact that the property is guaranteed rather than clamped.

**The Flag capture carve-out is part of this theorem, not a detail beside it.**
Any piece may capture the Flag, a rank 1 included, and a rank 1 that captured it
*would* be a survivor at rank 1 — the one case the argument above does not cover,
because the Flag does not fight and so cannot be the stronger piece that wins.
Ruling that capturing the Flag is not combat is what closes it. Without that
ruling the theorem is false, and the rule would have to be written with a floor
after all.

This is inconsequential for play, since the game ends on that ply. **It is not
inconsequential for an implementation**, which must resolve the win before
applying any reduction. Reducing first and checking the win condition afterwards
produces a rank 0 piece — briefly, and in a position nobody will look at, but on
a code path that any assertion about valid ranks will trip over.

### Interactions

- **A draw reduces nothing**, since a draw leaves no survivor. Equal-rank fights
  and formation-bonus draws both remove both pieces.
- **The formation bonus is re-evaluated after a reduction.** A piece that drops a
  rank may match a neighbour it did not match before, gaining a bonus, or stop
  matching one it did, losing it. This is emergent rather than designed, and it is
  coherent — but an implementation must recompute formations after every combat
  rather than caching them per piece.
- **A reduced piece is that rank in every respect** — it fights as it, forms up as
  it, and is written as it. There is no memory of what a piece used to be, and
  nothing in the game can ask.
- **The Flag is not a combatant**, so capturing it is not combat and the capturing
  piece is not reduced. This carries the notation's Flag-capture form (below) and
  the no-floor theorem (above) between them; the game being over anyway is the
  least of what it settles.

---

## Direction-relative encumbrance

An enemy directly behind or diagonally behind a piece does not encumber it. Only
the five squares ahead of or beside it, relative to the direction of travel, do.

Note that the square directly ahead is listed among the five for completeness but
does no work: an enemy standing there blocks the two-square move by occupying the
intermediate square in any case, and would be attacked rather than passed. The
rule produces the same legal-ply set whether that square is counted or not.

### What it does to a pursuit

The interesting consequence is not that fleeing gets easier in general, but that
**contact from behind stops holding a piece in place**:

| Pursuer's position | Effect |
|---|---|
| directly behind | neither piece is encumbered on its own ply — the quarry because the pursuer is behind it, the pursuer because the quarry has already moved out of contact. Both advance two. **Distance holds.** |
| diagonally behind | the same, for the same reason: both advance two and **distance holds**. But the pursuer stays one column off, and can only line up by spending a ply on the correction — during which the quarry advances two and the pursuer none. |
| directly beside | the quarry is encumbered and manages one; the pursuer, still in contact after the quarry's ply, is encumbered too and also manages one. **Lockstep, and contact is kept.** |

A straight-line chase therefore neither closes nor breaks — the same as at major
2, except that it now crosses the board twice as fast and so resolves sooner
rather than never. What changed is *why*: at major 2 the two pieces encumbered
each other and crawled; here neither encumbers the other and both run.

Note what the table does **not** say: there is no geometry from which a pursuer
closes on an equally fast quarry in the open. A pursuer that wants more than to
follow has to be **beside or ahead of** its quarry, which is where the two-square
move is actually denied — and getting there costs the tempo the middle row
charges for it. That is a positional task rather than a matter of having more
speed.

### Encumbrance is a property of the origin square only

A piece may advance two squares into a cluster of enemies; only its own eight
surrounding squares at the start of the ply are consulted. This is consistent
with major 2, where a piece may always step into contact, and it is worth stating
explicitly because the two-square move now reaches contact far more often.

---

## The starting position — where its rationale lives

The design reasoning for the generated start is **not** in this file. It is in
[`start-position.md`](start-position.md), alongside the specification, because
that rule is one where the two are hard to separate usefully: the threshold that
chooses between a reflection and a half-turn cannot be stated without saying what
it is for, and cannot be justified without the counts.

That document carries, and this one deliberately does not duplicate:

- why the Flag is confined to the back row, and what the alternatives would have
  cost — including that the restriction is what fixes the opening branching factor
  at exactly 8 for every generated position;
- the derivation of the threshold, its general form, and the warning to recompute
  the constant if the army ever changes;
- why both branches are fair, and what each one does to the shape of the game;
- how often each branch occurs, and the equivalent formulation that explains the
  intent the bare threshold does not;
- why mirror-equivalent positions are counted but never collapsed at generation
  time.

## White's restricted first ply

White's opening ply is limited to one square. Two things about it.

### It cannot backfire in direction

Removing options from a player in a perfect-information game weakly reduces that
player's value, so the restriction can only reduce White's advantage, never
increase it. The only case in which it changes nothing is one where White would
have advanced a single square anyway.

### It converts a uniform advantage into a parity-dependent one

The effect is sharper than a general reduction. Consider a race over a distance
of `D` squares:

- **Unrestricted:** both sides need `⌈D/2⌉` plies, always equal, and White moves
  first — so **White wins every race**.
- **Restricted:** White needs `⌈(D+1)/2⌉`. For odd `D` the two are still equal and
  White wins on turn order. For **even `D` Black arrives a full ply sooner and
  wins the race**.

With a generated starting position, the relevant distances are themselves
effectively randomised, so the advantage alternates rather than sitting with White
every game. That is a substantially better property than a blanket reduction, and
it is not visible from the rule's wording — which is why it is recorded here.

### It is not a rule setting

Whether it is *needed* has not been measured, and measuring it would be the
natural use of a rule flag. It is baked into the baseline anyway, deliberately:
the decision is too structural to leave floating, and the monotonicity argument
above guarantees it cannot over-correct in direction. If it proves to have been
the wrong call, that is what a rule setting can be introduced for later.

A **stronger variant was considered and parked**: the game stays at one square
per ply until Black plays a two-square move. That version is genuinely
path-dependent — the same board can arise with the two-square move unlocked or
still locked — where the adopted rule is a pure function of the position, since
the opening array can never recur once a piece has left the home rows. The
adopted rule is the one that keeps the position self-describing.

---

## Attrition replaced "no legal move"

Major 2 lost the game for a player who could not move. Major 3 loses it for a
player with no numbered pieces, checked after every ply.

### It fixes a real asymmetry, not just an interface annoyance

Under the major 2 rule, a player whose last piece dies in a mutual trade passes
the turn to an opponent who also has nothing — and the *opponent* loses, for
having no legal move. The player who moved last wins with no army. Making mutual
attrition a draw is the correct answer to that, and dropping the delayed check
removes the pointless shuffling ply in the one-sided case.

### Dropping "boxed in" costs nothing, and here is why

The reframing also drops major 2's other clause, for a player whose pieces all
survive but cannot move. In major 3 that state is unreachable:

> Take any numbered piece. It is stuck only if every orthogonal neighbour is
> off-board or friendly — an empty neighbour is a move, and an enemy neighbour is
> always a legal attack, since there are no Towers and the Flag is orthogonally
> attackable. For *every* numbered piece to be stuck, the set of squares holding
> them would need its whole on-board boundary covered by friendly pieces that are
> not themselves numbered — and there is exactly one such piece, the Flag. But
> the 8 × 8 grid has no cut square: removing any single square leaves the rest
> connected, so a non-empty set of fewer than 64 squares always has **at least
> two** on-board boundary squares. One Flag can never cover them.

**This argument depends on there being no lakes.** At major 2 a pocket sealed by
lakes and the board edge really could box a player in, which is why the clause
existed there. Anyone who later reintroduces impassable terrain to this major
must restore the clause with it — the terrain removal is load-bearing, not
incidental.

### Result reasons

`ResultReason` is free text. Major 3 uses `Attrition` and `Mutual Attrition`
where major 2 used `No Legal Move`, and adds `Resignation` (below). `Result`
values are unchanged.

---

## Resignation, and outcomes that are not in the position

Major 3 adds resignation: a player may concede at any point and the opponent wins
immediately. It is standard in turn-based games and costs the ruleset nothing —
no interaction with any other rule, no position in which it is unavailable, and
no acceptance to negotiate, which is what distinguishes it from a draw offer.

What is worth recording is the category it belongs to. **Every other way a major 3
game ends is a function of the position** — Flag capture, attrition, mutual
attrition and the inactivity counter can all be computed from the board and the
counter by something that has never seen the players. Resignation cannot, and
neither can a draw by agreement. They are *declared*, not derived.

Two consequences follow:

- **A record can state these outcomes but nothing can validate them.** A reader
  replaying a resigned game reaches a position that is not terminal and then stops,
  because the record says so. That is correct, not a malformed record, and a
  validator must not treat an early stop with a `Resignation` reason as an error.
  Note this is not a new situation — `Draw by Agreement` has always had exactly this
  property — but resignation makes it a *win* rather than a draw, so anything that
  assumed decisive results were position-derived needs revisiting.
- **Engine play may simply never use it.** Resignation is a courtesy between human
  players and a way to save time; an engine that plays every position to the end
  loses nothing by ignoring it. If engine play does adopt a resignation threshold,
  that is an engine policy and not a rule — the rules say only that resigning is
  permitted, never when it is appropriate.

---

## The inactivity counter — design

The intended resolution of a well-played game, in order:

1. **Flag capture** — the primary win condition.
2. **Attrition** — an opponent left with no numbered pieces.
3. **Draw** — by agreement in human play (Section 5.6), or by the inactivity
   counter (Section 5.4) in engine play.

The **inactivity counter** (Section 5.4) is *not* meant to be how a good game
ends in practice. It is pressure to force resolution and a safety bound against
infinite play, not an outcome to play for. The counter resets on any attack that
removes a piece; non-attacking plies increment it.

### 40 plies, and why it moved from 50

Major 2 used 50, chosen for 25 pieces on 144 squares. Major 3 sets **40**. The
considerations pull in both directions, which is why the number is a judgement
rather than a derivation:

- **Toward a shorter limit:** 15 movable pieces on 64 fully open squares, no
  terrain to manoeuvre around, two-square movement that is now much easier to
  obtain, and strength that decays monotonically so positions resolve rather than
  circling.
- **Toward a longer one:** the strength rule for the starting position
  deliberately removes the fastest way for a game to end, and the shield-wall
  defence around a Flag is genuinely hard to break. The half-turn branch in
  particular sets each player advancing into the opponent's strongest pieces.

**40 is provisional**, in the same sense that 50 was always provisional at major
2, and it is the first thing to revisit once games have been played. If it turns
out to need tuning rather than a single correction, it is the most natural
candidate in the whole ruleset for the first rule flag.

## The Fair Play Rule (Section 6)

Deliberately left undefined in the rulebook. It is primarily a **human-vs-human**
sportsmanship backstop: the inactivity counter bounds game length mechanically,
but a player who knows they are lost can still drag things out within it, and no
crisp definition of "unproductive" is worth the complexity for casual play.

For **engine play** we cannot lean on a fuzzy rule, and must keep the AI from
dithering *without* degrading its strength. The failure mode to watch (visible in
public chess engines): a repetition and its non-repeating alternative are
*value-equivalent* to the evaluator, so evaluation noise tips the choice either
way. The intended remedy is to give non-progress a *tiny, strictly negative*
signal so there is a gradient away from dithering — feeding the inactivity count
to the network as an input feature, and/or a small shaping term — without
distorting genuine position evaluation. This is a learned-engine concern,
recorded here so it is not lost; it is not a rule.

## Clarifications trimmed from the rulebook

Statements removed from `rules.md` to keep it declarative, retained here:

- *Sacrificial attacks (4.3):* typical uses are clearing a path for another
  piece, freeing a piece from a bad square, or resetting the inactivity counter
  to prevent a draw.

---

## No rule settings at launch

Major 3 publishes no rule flags. `3-0:PRE-RELEASE` is defined entirely by the
rules text, and a record's ruleset tag always renders as a bare edition id with
no deviations.

This is a deliberate choice rather than an omission. Two candidates were
identified during design and both were resolved into the baseline instead: the
Flag's permitted columns in the generated start (settled as the whole back row)
and White's opening restriction. Introducing a setting to defer either decision
would have bought measurement at the cost of shipping an undecided game.

The mechanism remains available, and the rules for it are unchanged: a new
setting's first value is always the behaviour that preceded it, so introducing one
never alters what `3-0:PRE-RELEASE` means.

### The two diagonal-attack proposals are withdrawn

[`proposed-variants.md`](proposed-variants.md) proposed two flags against major
2: `DIAGONAL_ATTACKABLE`, widening diagonal attack to immobile targets, and
`DIAGONAL_ATTACK_PATH`, requiring an open path for one. Major 3 adopts **both
behaviours as baseline** ([`rules.md`](rules.md)
[Section 4.4](rules.md#44-diagonal-attacks)) rather than as a flag, which is what
"no rule settings at launch" means in their case specifically.

With major 2 retired, there is no longer a ruleset for either proposal to be a
variant *of* — both entries are withdrawn from `proposed-variants.md` rather than
graduated. Neither ever became a major 2 flag, and major 3 has no rule settings
of its own for them to land in either.

---

## Editions, and the retirement of major 2

### A notation break moves what shares the break, not everything ever published

The root [`CLAUDE.md`](../../CLAUDE.md)'s scoping sentence — "a notation break
moves every live ruleset to the next major together" — describes how rulesets
sharing a rules text advance together at the moment of the break. It is not an
obligation on a new major to re-publish or retire the rulesets of the previous
one; that is a separate decision, made per major rather than implied by the
notation rule.

### Major 3 replaces major 2, by decision rather than by mechanism

Story 00000049 decided that major 3 **replaces** `2-0:BATTLE`, `2-0:CLASH` and
`2-1:SKIRMISH` rather than joining them: `3-0:PRE-RELEASE` is the only Active
edition, and the three move to the Historical table, retired. They keep their
rows — a record or checkpoint already stamped with one still names something real
— but no code path can set one up any longer, and none of the three names is
offered. This was a choice, not a consequence of the major bump: nothing about
publishing a new major forces the rulesets under the old one out of print. See
[story 00000049](../plan/00000049-implement-ruleset-three/story.md) for the
reasoning.

### The `PRE-RELEASE` name is reused, deliberately

`1-2:PRE-RELEASE` already existed in the major 2 Historical table, marked
**retired**. Naming the major 3 ruleset `PRE-RELEASE` reuses that pointer, so two
unrelated editions now share a name across two majors: `1-2:PRE-RELEASE` and
`3-0:PRE-RELEASE` are permanent, distinct labels that happen to print the same
ruleset name.

Nothing is violated by this: editions are immutable and `1-2:PRE-RELEASE` still
means exactly what it always meant, and a ruleset name is a mutable pointer by
definition — `PRE-RELEASE` now points at the major 3 edition. The reuse is
deliberate rather than a wrinkle inherited from a draft: the name says what is
still true, which is that the game is not finished.

---

## Terminology: "move" in the rules, "ply" everywhere else

`rules.md` is written for a non-technical player audience and uses **"move"** for a
single player's action throughout. Everywhere else in this project — code, tests,
plans, and design documents — the term is **"ply"**, per the project vocabulary in
the root `CLAUDE.md`. The two are the same concept: **one move = one ply.**
`rules.md` is the *only* document that prefers "move."

## Game notation and the record file format

The move notation in `rules.md` [Section 4.5](rules.md#45-recording-a-move) and
this file format share one coordinate frame and a common position-block
rendering. The engine emits the result-marking (extended) move form and the
from-generation record shape described below; mid-game records remain documented
as reserved for later use.

### Player colours

The first player to move is **White**; the second is **Black**, regardless of
the colour the tokens are physically rendered as (tokens are often **Red** for
White and **Blue** for Black). White and Black are the labels used in record
header tags and to identify the two sides in the position block.

### Marks describe the piece that *started* on a square

Both the `x` and `=N` marks attach to a square and describe the piece standing
there **when the ply began**. `A2x-A4` means the piece that began on A2 did not
survive, even though it was the piece that moved; `A2=3-A4x` means the attacker
that began on A2 survived and is now rank 3, while the defender on A4 did not.

This is why `=N` sits on the source square when the attacker survives and on the
destination square when the defender survives. The alternative — attaching the
mark to wherever the survivor ends up standing — would put it on the destination
square in both cases, which reads naturally but requires the reader to hold a
different convention for `=N` than for `x`.

**The exhaustiveness invariant.** In a combat ply, each of the two squares
carries exactly one mark, `x` or `=N` — never both, never neither. Every
participant in a fight either dies or survives and is reduced; there is no third
outcome. This makes malformed records detectable, and gives a parser a strong
assertion to check rather than a set of cases to enumerate.

**Flag capture is self-identifying.** The one ply that looks like combat and is
not is a Flag capture, written `A2-A4x`: the Flag's square is marked, the
attacker's is bare. Because no real combat can leave a source square unmarked,
`A2-A4x` always and only means a Flag capture, and a consumer can detect the
terminal ply from the tape alone without tracking board state.

### The position block

The full board, rendered from White's perspective: row 8 at the top, row 1 at
the bottom, column A at the left. Every square is a fixed-width, 3-character
cell, cells separated by a single space, one board row per line. Because a
position need not be a game start, a piece's side cannot be inferred from which
half of the board it stands on, so side is encoded explicitly per cell:

- **White piece:** `[R]` — e.g. `[1]`, `[4]`, `[5]`, `[F]`
- **Black piece:** `*R*` — e.g. `*3*`, `*5*`, `*F*`
- **Empty square:** `---`

`R` is the piece symbol from `rules.md` [Section 2.2](rules.md#22-the-pieces):
`1`–`5` for the numbered ranks, `F` Flag. The alphabet is smaller than at major
2: there is **no `T`** (there are no Towers) and, more usefully for a renderer,
**never any `XXX`**, since there are no lakes. A consumer may rely on that for
major 3 records specifically, and must not generalise it to any other major.
This is the same string the engine's `render_position_block` produces and the
library-facing `text_board` reuses.

**The block is size-describing, not fully self-describing.** A reader recovers
**dimensions** by counting lines and cells; it does **not** need the home-zone
row count, because rendering and stepping a record never consults home zones — a
mid-game position does not reveal where home zones were in any case.

### Record file format

A record file has three sections, in order, separated by one or more blank
lines:

1. **Header tags**
2. **Position block** (the record's starting board)
3. **Move sequence**

**Header tags** use PGN tag syntax, `[Name "value"]`, one per line. The record
reuses PGN's Seven Tag Roster plus `ResultReason` and `Ruleset`, and — new at
major 3 — an optional `StartPosition`: `Event`, `Site`, `Date`, `Round`, `White`,
`Black`, `Result`, `ResultReason`, `Ruleset`, `StartPosition`. `Result`,
`ResultReason`, and `Ruleset` are always written; the roster tags (`Event`…
`Black`) are optional/best-effort, and `StartPosition` is optional. **A reader
must ignore any header tag it does not recognise** rather than rejecting the
record — major 2's roster was closed and never needed this, but the roster can
grow now, so a later tag needs the same tolerance `StartPosition` does.

`Ruleset` records **which rules the game was played under**: the edition id,
followed by one `FLAG=value` token per flag deviating from that edition, space
separated, ordered alphabetically by flag id. Since major 3 publishes no flags,
every major 3 record renders as a bare edition id, `3-0:PRE-RELEASE`, with no
deviations. The edition id is always written in full and never abbreviated to a
bare ruleset name, which would only name a moving pointer.

`StartPosition` carries the 16-character position ID specified in
[`start-position.md`](start-position.md). It is redundant for replay — the
position block that follows already carries the full starting board — and a
reader must not require it.

`Result` uses PGN's values: `1-0` (White wins), `0-1` (Black wins), `1/2-1/2`
(draw), `*` (ongoing/unknown). `ResultReason` is free text (e.g. `Flag Captured`,
`Attrition`, `Mutual Attrition`, `Inactivity`), sourced from the terminal
position's outcome reason (`GamePosition.outcome_reason`, threaded through
`GameResult.result_reason`). `Date` uses PGN's `YYYY.MM.DD` form (`????.??.??`
when unknown). Tag *values* are escaped as in PGN — a literal `\` is written
`\\` and a literal `"` is written `\"` — so a value containing either stays
inside its quotes; writers also collapse any newline in a value to a space,
since a tag occupies a single line.

**Position block** is exactly the format specified above: the generated starting
position for a game started from generation; for a mid-game record, the
resumption board.

**Move sequence**: rounds numbered from 1, each `N. WhiteMove BlackMove`,
multiple rounds one per line (or wrapped freely — parsing is
whitespace-insensitive within this section). A game ending on White's move
shows that round with only White's move.

Each move may use **either** notation form from `rules.md` Section 4.5: the
plain form (`A2A4`, source-then-destination, no separator) or the extended
result-marking form (`A2-A4`, with `x` or `=N` marking each square involved in
combat). **The plain form must not be used for major 3 records**, since it
cannot carry `=N` and a game written that way cannot be replayed correctly; a
reader must still accept it for a major 2 record, per the view-only-replay
guarantee. The reference engine emits the extended form (rendered by
`CtfGameLogging.ply_annotation`), so a record it produces looks like:

```
20. A2=3-A4x B7-B6
21. C3-C2
```

**Mid-game records** (format-reserved, not yet implemented): a record whose
starting position has Black to move opens the move sequence with
`N... <blackmove>`. Side-to-move and the inactivity counter for a non-start
resumption would be carried in additional header tags (names TBD). The current
engine only produces from-generation starts (White to move, counter at 0), so
this is documented but unused for now.

**File conventions:** UTF-8 encoding. Files are *written* with `\n` (LF) line
endings; *readers* must accept both LF and CRLF. The header, position, and move
sections are separated by one or more blank lines.

## Rules history

- **The Tower, the lakes, and phase 1 (major 3)** left the game at story
  00000049. Major 2's technical notes carried extensive Tower- and lake-specific
  material — placement restrictions, diagonal-attack interactions, board-layout
  derivations — none of which has a subject any longer; see
  [`changelog.md`](changelog.md) for what changed and
  [story 00000049](../plan/00000049-implement-ruleset-three/story.md) for why.
- **"Unbreachable Flag" (Story 1.1)** was a win condition based on Flag enclosure
  and Sapper availability. It was removed in Story 1.2 as part of a broader
  simplification (removal of Sappers and special piece abilities). References to
  this rule in pre-1.2 design notes are obsolete.
- **Orthogonal-only attacks (major 1)** were the rule through
  `1-2:PRE-RELEASE`. Diagonal attack was added to the baseline at major 2 to make
  play more direct: under orthogonal-only attacks a threatened piece could step
  off the attacker's line and force it to spend plies re-establishing contact,
  which bled pressure out of the game.
- **The single 12×12 board (major 1)** was the only board through
  `1-2:PRE-RELEASE`. Design notes written before major 2 treat the board
  dimensions, the lake pattern, and the 25-piece army as fixed properties of the
  game rather than as configurable values.

## Related design background

Deeper rationale for these rules — why the piece counts, combat asymmetries, and
win conditions are shaped the way they are — lives in the offline design notes
(retained as history, not authoritative). Where those notes disagree with
`rules.md`, `rules.md` governs.

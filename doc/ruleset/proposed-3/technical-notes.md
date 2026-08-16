# Capture the Flag — Technical Notes, Major 3 (Proposed)

> **Draft.** Companion to [`rules.md`](rules.md), which is kept clean enough to
> hand to a player. Anything developer- or design-facing lives here. See
> [`README.md`](README.md).

Terminology follows the project standard: this file says **ply** where
`rules.md` says **move**, for the same player-audience reason the major 2
documents split them. One move = one ply.

**Scope.** This story describes a ruleset. Engine, evaluator and training
implications are deliberately out of scope and are not analysed here.

---

## Why this is a major bump

Most of what major 3 changes could have been expressed within major 2's existing
model, as rule flags with behaviour-preserving defaults: an open board with no
lakes is a `BOARD_LAYOUT` value, a five-rank tower-less army is an
`ARMY_COMPOSITION` value, and the direction-relative encumbrance, the generated
start and the opening restriction are all ordinary flags. None of those forces
anything.

**Two changes do.**

### 1. The rank numbering is inverted

Major 2 publishes rank `1` as the strongest piece. Major 3 makes `5` the
strongest and `1` the weakest. A rank digit is not an internal detail: it is the
symbol written in every position block of every record. Making `1` mean the
opposite of what it has always meant **redefines a published symbol**, which
Appendix A's permanence promise at major 2 exists to forbid.

It cannot be a flag either. A flag would make the meaning of a glyph depend on a
setting, so a renderer would have to resolve a flag value before it could draw a
board — worse than the break it was avoiding. Inverting the numbering is only
coherent as a property of a rules text, which is what a major is.

**Why invert it at all?** Only that "bigger number is stronger" is what people
expect, and the cost of being counter-intuitive is paid forever by every new
player and every new consumer. There is no mechanical argument either way. It is
worth doing precisely because it can only be done at a major bump, so a bump
happening anyway is the moment to spend it.

### 2. Rank reduction breaks replay-by-schema

Major 2 guarantees that **view-only replay works for every record, forever, by
notation-schema stability alone** — a reader steps a record by moving a piece
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

### What does *not* force it

For the record, since it constrains what may ride a future bump: removing the
lakes and the Towers, changing the army, changing the board's home-zone depth,
and adding the generated start would all have been expressible under major 2's
notation without any change at all. They ride this bump because it is happening,
not because they require it.

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

## The notation

### Marks describe the piece that *started* on a square

Both marks attach to a square and describe the piece standing there **when the
ply began** — this is the convention major 2 already uses for `x`, and `=N`
follows it. `A2x-A4` means the piece that began on A2 did not survive, even
though it was the piece that moved.

This is why `=N` sits on the source square when the attacker survives
(`A2=3-A4x`) and on the destination square when the defender survives
(`A2x-A4=2`). The alternative — attaching the mark to wherever the survivor ends
up standing — would put it on the destination square in both cases, which reads
naturally but requires the reader to hold a different convention for `=N` than for
`x`.

### The exhaustiveness invariant

> **In a combat ply, each of the two squares carries exactly one mark, `x` or
> `=N`.** Never both, never neither.

Every participant in a fight either dies or survives and is reduced; there is no
third outcome. This makes malformed records detectable, and gives a parser a
strong assertion to check rather than a set of cases to enumerate.

### Flag capture is self-identifying

The one ply that looks like combat and is not is a Flag capture, written
`A2-A4x`: the Flag's square is marked, the attacker's is bare. Because no real
combat can leave a source square unmarked, **`A2-A4x` always and only means a
Flag capture**, and a consumer can detect the terminal ply from the tape alone
without tracking board state.

### The plain form must not be used for records

Major 2 permits either the plain form (`A2A4`) or the extended, result-marking
form in a record, and requires a reader to accept both. **At major 3, records must
use the extended form.** The plain form cannot carry `=N`, so a plain-form record
cannot be replayed correctly — which is the exact guarantee the notation change
was made to preserve.

The plain form survives only as a move-*entry* convenience in a text interface,
which is what `rules.md` already says it is for.

### The position block

The alphabet shrinks. A major 3 position block contains only `1`–`5`, `F`,
and `---`; it has **no `T`** (there are no Towers) and, more usefully for a
renderer, **never any `XXX`**, since there are no lakes. A consumer may rely on
that for major 3 records specifically, and must not generalise it to any other
major.

### The header tag roster gains `StartPosition`

Major 2's header roster is closed — PGN's Seven Tag Roster plus `ResultReason`
and `Ruleset`, and nothing else is defined. Major 3 adds one tag,
**`StartPosition`**, carrying the position ID specified in
[`start-position.md`](start-position.md). It is **optional**: the record already
holds its full starting board in the position block, so the ID is redundant for
replay and a reader must not require it.

Because the roster can now grow, one obligation has to be stated that the major 2
spec never needed: **a reader must ignore header tags it does not recognise**
rather than rejecting the record. Without that, `StartPosition` would be a
breaking change for every existing reader, and any later tag would be one again.

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

Major 2 loses the game for a player who cannot move. Major 3 loses it for a
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
lakes and the board edge really can box a player in, which is why the clause
exists there. Anyone who later reintroduces impassable terrain to this major must
restore the clause with it — the terrain removal is load-bearing, not incidental.

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

## The inactivity counter — 40 plies

Major 2 uses 50, chosen for 25 pieces on 144 squares. Major 3 sets **40**.

The considerations pull in both directions, which is why the number is a judgement
rather than a derivation:

- **Toward a shorter limit:** 15 movable pieces on 64 fully open squares, no
  terrain to manoeuvre around, two-square movement that is now much easier to
  obtain, and strength that decays monotonically so positions resolve rather than
  circling.
- **Toward a longer one:** the strength rule for the starting position
  deliberately removes the fastest way for a game to end, and the shield-wall
  defence around a Flag is genuinely hard to break. The half-turn branch in
  particular sets each player advancing into the opponent's strongest pieces.

**40 is provisional**, in the same sense that 50 has always been provisional at
major 2, and it is the first thing to revisit once games have been played. If it
turns out to need tuning rather than a single correction, it is the most natural
candidate in the whole ruleset for the first rule setting.

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

### The two diagonal-attack proposals are absorbed, not graduated

[`../proposed-variants.md`](../proposed-variants.md) proposes two flags against
major 2: `DIAGONAL_ATTACKABLE`, widening diagonal attack to immobile targets, and
`DIAGONAL_ATTACK_PATH`, requiring an open path for one. Major 3 adopts **both
behaviours as baseline** ([`rules.md`](rules.md)
[Section 4.4](rules.md#44-diagonal-attacks)) rather than graduating either as a
flag, which is what "no rule settings at launch" means in their case
specifically.

Their entries in that file are **unaffected** and remain live proposals against
major 2, where they would still need behaviour-preserving defaults — major 3
adopting a behaviour says nothing about whether major 2 should offer it. If major
3 is adopted, `proposed-variants.md` should gain a pointer here, so the overlap
is visible from the major 2 side too.

---

## Editions, and what this major does not disturb

### A major does not drag the other rulesets with it

Major 2's technical notes state that a notation break "moves every live ruleset to
the next major at once." That sentence should be read as scoped **within** a
major — describing how rulesets sharing a rules text advance together — and not
as an obligation on a new major to re-publish or retire the rulesets of the
previous one.

`2-0:BATTLE`, `2-0:CLASH` and `2-1:SKIRMISH` are therefore untouched by this
proposal. They keep their rules text, their numbering, and their pointers. Whether
they continue to be offered alongside major 3 is a separate decision that this
story does not make and does not prejudge.

If major 3 is adopted, that sentence in the major 2 notes should be reworded, so
the scoping is stated rather than inferred.

### The `PRE-RELEASE` name is reused, and this is a known wrinkle

`1-2:PRE-RELEASE` already exists in the major 2 Historical table, marked
**retired** — which that table defines as "the ruleset name itself is no longer
offered." Naming the major 3 ruleset `PRE-RELEASE` therefore reuses a retired
pointer, and leaves two unrelated editions sharing a name across two majors.

Nothing is actually violated: editions are immutable and `1-2:PRE-RELEASE` still
means exactly what it always meant, and ruleset names are explicitly mutable
pointers rather than permanent labels. But **un-retiring is a status transition
the edition table has no vocabulary for**, and the shared name is a genuine
opportunity for confusion.

The name is a working one, chosen because major 3 is a proposal rather than a
product. If it is adopted, giving the ruleset its own name is the tidier outcome,
and the reuse should be a deliberate decision at that point rather than something
inherited from a draft by default.

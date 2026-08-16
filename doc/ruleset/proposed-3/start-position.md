# Capture the Flag — The Starting Position (Major 3)

> **Draft.** Companion to [`rules.md`](rules.md). See [`README.md`](README.md).

Major 3 has no placement phase. Every game begins from a **generated starting
position**, and this document specifies how one is built, how many there are, and
what a position ID means.

[`rules.md`](rules.md) [Section 3](rules.md#3-the-starting-position) states the
same procedure in the form a player needs at the table. This document is the
implementer's copy: the same rules, plus the counts, the general form of the
strength rule, and the identification scheme.

---

## 1. The constrained set

A starting position is fully determined by **White's arrangement alone**. Black's
army is derived from it (Section 3), so generating a position means generating
White's half and turning it.

White's 16 pieces — three each of ranks 1–5, plus the Flag — fill White's two
home rows completely: 16 pieces into 16 squares, rows 1 and 2, columns A–H.
One restriction applies:

> **The Flag must stand on row 1**, White's back row.

Every arrangement satisfying that restriction is **equally likely**. Nothing else
is constrained: any rank may sit anywhere, ranks may be adjacent or spread, and
no arrangement is excluded for being lopsided.

### How many there are

| Constraint | Count |
|---|---|
| Flag anywhere in the home rows | 2,690,688,000 |
| **Flag on row 1 (the rule)** | **1,345,344,000** |
| Flag on the middle four columns of row 1 | 672,672,000 |

The middle row shows the size of the set actually in use. The other two rows are
included because they are the obvious variations and it is useful to know what
they would cost: the flag restriction is inexpensive, and even the tightest of
the three leaves the set far beyond anything a player or an engine could learn by
position.

Roughly **half** of these are strategically duplicate, since an arrangement and
its left–right mirror image play identically on a board with no terrain. That
does not affect generation — see Section 4.

### A useful side effect of the row-1 restriction

At the start, both home areas are completely full, so a back-row piece is
enclosed by its own army on every orthogonal side and no enemy is within reach of
a diagonal. **Only front-row pieces can move, and only forwards.** With the Flag
confined to row 1, all eight front-row pieces are numbered pieces, so White has
exactly **8 legal opening moves** — one per front-row piece, advancing a single
square under the first-move restriction
([`rules.md`](rules.md) [Section 4.1](rules.md#41-turn-order)) — and that count is
the same for every generated position. Allowing the Flag onto row 2 would make it
7 for some positions and 8 for others.

---

## 2. Generating White's arrangement

Draw uniformly from the set in Section 1. Any method uniform over that set is
acceptable; the direct one is:

> Place the Flag on a uniformly chosen square of row 1, then shuffle the 15
> numbered pieces uniformly into the remaining 15 squares.

**Do not attempt to generate a position by drawing a random position ID.** The ID
(Section 5) is an encoding of the board rather than an index into the set, so the
overwhelming majority of values are not positions at all. Generate the
arrangement, then encode it.

---

## 3. Deriving Black's arrangement

Black's army is White's, turned. Which turn is used depends on where White's Flag
sits relative to the strength of the army around it.

### The strength rule

Split the board into a **left half** (columns A–D) and a **right half**
(columns E–H). Each half holds 8 of White's 16 squares, so the half containing
the Flag holds exactly **7 numbered pieces**.

> **Sum the ranks of the seven numbered pieces in the Flag's half.** Call it
> `S`.
>
> - `S ≥ 22` — **half-turn.** Black's army is White's rotated 180°: column `c`
>   maps to column `9 − c` (A↔H, B↔G, C↔F, D↔E) and row `r` to row `9 − r`. The
>   two Flags end up in **opposite halves**.
> - `S ≤ 21` — **reflection.** Black's army is White's mirrored across the middle
>   of the board: column `c` is unchanged and row `r` maps to row `9 − r`. The two
>   Flags end up in the **same column**, facing each other.

### Why 22

The fifteen numbered ranks total `3 × (1+2+3+4+5) = 45`. An even share for seven
of them is `45 × 7 / 15 = 21`, so `S ≥ 22` means the Flag's half is carrying more
than its share of the army's strength — the Flag is on the **stronger** half — and
`S ≤ 21` means it is on the weaker half or exactly even.

**The threshold is derived, not fundamental.** Written generally:

```
half-turn  ⟺  S × (total numbered pieces)  >  (pieces in the Flag's half) × (total rank)
           ⟺  S × 15  >  7 × 45
           ⟺  S  >  21
```

If the army composition ever changes, **recompute the constant** rather than
carrying 22 across. It is correct only for three each of ranks 1–5.

### What the rule achieves

Both turns produce a fair position: in each case the whole position is invariant
under "swap the two players, then apply the same turn," so neither side has
better pieces, better ground, or a better shape. Fairness does not depend on
which branch is taken, and so is not what the rule is choosing between.

What it chooses is **which part of the enemy army each Flag faces**, and both
branches choose the same answer: the weaker part.

| Flag sits on | Turn | Flag is defended by | Flag is faced by |
|---|---|---|---|
| the stronger half | half-turn | its own strong pieces | the enemy's weak pieces |
| the weaker half | reflection | its own weak pieces | the enemy's weak pieces |

The excluded combination is a Flag **defended by weak pieces and charged by
strong ones** — the case that reduces a game to a race at the Flag which one side
is structurally better equipped to win. It cannot arise.

The two branches produce structurally different games, which is the second reason
for the rule:

- **Half-turn** — the Flags sit on opposite halves, each defended by its owner's
  strength and approached by the opponent's weakness. Two separate theatres, each
  player advancing into the opponent's best pieces.
- **Reflection** — both Flags sit on the same half and both strong wings on the
  other. The main battle happens away from the Flags, and whoever wins it
  converts.

### How often each branch occurs

Computed over all 6,435 ways the fifteen numbered pieces can split across the two
halves, weighted by the number of arrangements each split represents:

| Branch | Share of positions |
|---|---|
| Half-turn (`S ≥ 22`) | 43.17% |
| Reflection (`S ≤ 21`) | 56.83% |

### An equivalent formulation, and why the threshold form is preferred

The rule is sometimes easier to motivate as a comparison: *sum the strongest
seven pieces on each half, and half-turn if the Flag's half is at least as
strong.* That formulation and the threshold above select **exactly the same
positions** — verified exhaustively over all 6,435 splits, with zero
disagreements. It is stated here because it explains the intent, which "22" alone
does not.

The threshold form is what an implementation should use, because it needs only
one sum and one comparison: no selecting a subset, no examining the other half,
no division, and no tie case to resolve. The comparison form's only tie is
`S = 22` against a half whose weakest piece is a rank 1, and directing that tie to
the half-turn is precisely what turns `S > 22` into `S ≥ 22`.

---

## 4. Mirror-equivalent positions are not collapsed

An arrangement and its left–right mirror image play identically, so the
1,345,344,000 positions comprise roughly 672 million strategically distinct
pairs.

**They are deliberately not merged.** Collapsing each pair to a single
representative would mean the generator only ever emits one member of it, and if
the canonical representative is (say) the one with the Flag further left, then
every game in the game's history would have the Flag in columns A–D. The bias
would be plainly visible at the board.

Mirror-equivalence is therefore an analysis fact, and not something the generator
may act on. An implementation may expose a `mirror_of` helper for study or for
pairing positions; it must not apply one while generating.

---

## 5. The position ID

Every startable position is named by a **position ID**: a 16-character
hexadecimal code spelling out White's arrangement. Black's follows from it by
Section 3, so the ID names the whole position.

### What it is for

- Setting up a particular position again deliberately, to replay or study it.
- **Playing the same position twice with the sides reversed**, which cancels both
  the first-move advantage and any luck in the arrangement. This is the reason to
  have an ID at all rather than relying on the recorded board.

### The encoding

Read White's 16 squares in a fixed order — **row 1 from A to H, then row 2 from A
to H** — and write each square as one hexadecimal digit:

| The square holds | Digit |
|---|---|
| a numbered piece of rank 1–5 | `1`–`5` |
| the Flag | `F` |
| nothing | `0` |

The first eight characters are row 1 and the last eight are row 2.

**The ID is the board.** There is no index, no ordering and no algorithm to get
wrong: writing one is transcribing sixteen squares, reading one is transcribing
them back, and a person can read the arrangement off the code by eye.

```
[StartPosition "2542333F54415211"]

  row 1   A1 … H1     2 5 4 2 3 3 3 F
  row 2   A2 … H2     5 4 4 1 5 2 1 1
```

Two conventions:

- **Always exactly 16 characters**, one per square and never trimmed. The fixed
  width is what lets two codes be compared and sorted as plain strings. At major 3
  a code cannot begin with `0` — every home square is occupied — but under a later
  ruleset where `0` can occur (see [Reserved digits](#reserved-digits)) a leading
  `0` would be significant, and dropping it would silently shift every square.
- **Write uppercase, and upper-case on input.** Comparison, sorting and storage
  are all defined on the upper-cased form. A reader may accept a lowercase code
  but must normalise it before doing anything else: `F` is `0x46` and `f` is
  `0x66`, so a lowercase code neither compares equal to its uppercase twin nor
  sorts alongside it.

### It is a string, not a number

**Treat a position ID as a 16-character string.** It is a code, and no arithmetic
is ever performed on it: two positions are the same when their upper-cased codes
match as strings.

This matters in practice. Sixteen hexadecimal digits is 64 bits, and the largest
valid code exceeds 1.7 × 10¹⁹ — far past the 2⁵³ limit within which a JavaScript
`Number`, an IEEE double, holds integers exactly. A front-end that parses an ID
into a `Number` will corrupt it silently. Keep it a string; use `BigInt`, or a
pair of 32-bit halves, only if something genuinely needs the numeric value.

An implementation that wants one may of course pack the code into a `uint64` —
sixteen nibbles fit exactly, with row 1 in the high 32 bits — but that is a local
convenience and not the interchange form.

Because the codes are fixed-width uppercase hexadecimal, they also **sort as
strings in the same order they would as numbers**, so an implementation can order
or index positions without parsing anything. This is the second reason to
normalise case on input rather than merely tolerating it.

### Reserved digits

`0` and `6`–`E` are unused at major 3 — every home square is occupied and there
are only five ranks — and they are reserved rather than forbidden. A later
ruleset with a sixth rank, or one whose home area is not filled completely,
encodes in this same scheme with no rework and without renumbering anything
already written. That extensibility, and the readability, are why this is
preferred to a compact index over the 1,345,344,000 valid positions.

### Not every code is a position

The encoding is deliberately sparse: of the 16¹⁶ codes the format can express,
only 1,345,344,000 are startable positions — a density of about 7 × 10⁻¹¹. That
is the price of an encoding that is readable, extensible and algorithm-free, and
it has two consequences an implementation must respect.

- **A reader must validate, not merely decode.** A code names a legal major 3
  starting position only if its digits are exactly three each of `1`–`5` and
  exactly one `F`, with that `F` among the first eight characters.
- **A position cannot be generated by drawing a random code.** Generate the
  arrangement as in Section 2, then encode it.

Valid codes run from `1112223F33444555` to `F555444333222111`.

### Recording it

The ID is carried in an **optional** header tag on a game record. It is redundant
for replay — a record already carries its full starting board in the position
block — so a record without it is complete and a reader must not require it.

Because the encoding is fixed, an ID written by one implementation names the same
position in every other: an engine and a front-end can agree on a position
without exchanging a board.

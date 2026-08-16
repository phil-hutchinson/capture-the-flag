# Capture the Flag — Proposed Rules, Major 3

> **Draft.** This is a proposed ruleset, not a published one. It does not change
> `2-0:BATTLE`, `2-0:CLASH` or `2-1:SKIRMISH`, which remain exactly as they are.
> See [`README.md`](README.md).

---

## 1. Overview

Capture the Flag is a two-player battlefield board game. Every piece is visible
to both players from the very first move: there is no hidden setup, no secret
placement, and nothing to deduce about what your opponent is holding. Everything
that decides the game happens in the open.

The primary object is to **capture the opposing Flag**. There are other ways to
win or end the game — see [Section 5](#5-ending-the-game).

Each game begins from a **generated starting position** rather than a fixed
array. Both players receive congruent armies arranged the same way, so the
position is even, but the arrangement itself differs from game to game — there
are over a billion of them. See [Section 3](#3-the-starting-position).

Throughout these rules, a **move** is a single action taken by one player on
their turn. (One full round is two moves: one per player.)

The two sides are **White** and **Black**. White moves first. Columns and rows
are named from White's point of view (see
[Section 4.5](#45-recording-a-move)); the side assignment is settled before the
starting position is generated.

### One ruleset

Major 3 offers a single ruleset on an 8 × 8 board with a 16-piece army. There are
no board or army options, and no rule settings to choose between: this document
describes the game completely.

---

## 2. Components

### 2.1 The board

The board is **8 × 8**. Every square is open — there is no impassable terrain of
any kind, and no square that a piece may not enter.

Reading from White's side to Black's, the rows are:

| Rows | Region |
|---|---|
| 2 | White's home rows (rows 1–2) |
| 4 | Open ground (rows 3–6) |
| 2 | Black's home rows (rows 7–8) |

Each home area is 2 rows × 8 columns = **16 squares** — exactly the size of an
army. Both armies therefore fill their home rows completely at the start, with no
empty square in either.

The board's **left half** is columns A–D and its **right half** is columns E–H.
Each half is four columns wide, so each player has 8 of their 16 home squares in
each half. These halves are referred to only when generating the starting
position ([Section 3](#3-the-starting-position)); they have no meaning during
play.

### 2.2 The pieces

Each player commands an army identical to their opponent's: **15 numbered pieces
and one Flag**, 16 in all.

| Rank | Qty | Name |
|---|---|---|
| 5 | 3 | Master-of-Arms |
| 4 | 3 | Champion |
| 3 | 3 | Foot Soldier |
| 2 | 3 | Militia |
| 1 | 3 | Peasant |
| — | 1 | Flag |

**Rank 5 is the strongest and rank 1 the weakest.** The numbered pieces form a
strict strength order, and a higher number always beats a lower one.

**The number is the rule; the name is decoration.** Every rule in this document
is stated in numbers, and nothing anywhere depends on what a rank is called. The
names are supplied so that players have something to say out loud, and may be
changed without changing the game.

The Flag cannot move and cannot attack, but it can be attacked. It is the only
immobile piece. Every numbered piece follows the same movement and combat rules;
none has a special ability.

---

## 3. The starting position

There is no placement phase. Each game begins from a starting position generated
before play, visible to both players in full.

Both armies fill their home rows completely — 16 pieces in 16 squares — so no
player chooses *which* squares to occupy. What varies from game to game is the
arrangement.

The position is built in two steps.

### Step 1 — White's army

White's 16 pieces are arranged over White's two home rows (rows 1 and 2), subject
to one restriction:

- **The Flag must stand on row 1**, White's back row.

Every arrangement satisfying that restriction is equally likely. There are
1,345,344,000 of them.

### Step 2 — Black's army

Black's army is built by turning White's, so that the two are congruent. Which
turn is used depends on where White's Flag sits relative to the strength of the
army around it:

> **Add up the ranks of the seven numbered pieces standing in the same half of
> the board as the Flag.**
>
> - **22 or more** — the Flag is on the army's *stronger* half. Black's army is
>   White's turned a **half-turn** (rotated 180°): columns reverse, so A becomes
>   H, B becomes G, and so on. **The two Flags end up in opposite halves.**
> - **21 or less** — the Flag is on the army's *weaker* half. Black's army is
>   White's **reflected** across the middle of the board: columns are unchanged.
>   **The two Flags end up in the same column, facing each other.**

The Flag's half always holds exactly 7 numbered pieces (the Flag occupies the
eighth square), and the ranks of all 15 numbered pieces total 45, so an even
share for seven of them would be 21. A total of 22 or more therefore means the
Flag's half is carrying more than its share of the army's strength.

**Either way the position is even.** Black's army is an exact copy of White's,
turned; whichever turn is used, the whole position is unchanged if you swap the
two players and turn the board the same way. Neither player has better pieces,
better ground, or a better shape.

**What the rule is for** is that each Flag ends up facing the *weaker* part of
the enemy army, whichever half it sits in. A Flag defended by weak pieces and
charged by strong ones cannot occur.

### The position ID

Every startable position can be named by a short code that spells out White's two
home rows one square at a time, so that a particular position can be set up again
deliberately — to replay it, or to play it twice with the sides reversed. See
[`start-position.md`](start-position.md). Recording it is optional and nothing in
play depends on it.

---

## 4. Play

### 4.1 Turn order

- Play strictly alternates: one move per player, back and forth.
- **White's first move of the game is limited to one square.** Every other move
  in the game, for either player, follows the ordinary rules below. This offsets
  part of the advantage of moving first.
- **Passing is never allowed.** A player who still has at least one numbered
  piece always has at least one legal move, so this never leaves a player stuck:
  a player with no numbered pieces has already lost (see
  [Section 5.2](#52-loss--attrition)).

### 4.2 Movement

- **Baseline.** On a move, a piece steps **one square orthogonally** (up, down,
  left, or right). It may move into an empty square, or attack an enemy piece by
  moving onto its square (see [Combat](#43-combat)).
- **Diagonal attacks only.** A piece may also move **one square diagonally, but
  only to attack** — see [Section 4.4](#44-diagonal-attacks). A piece may never
  move diagonally onto an empty square.
- **The two-square move.** A piece may move **two squares in a straight
  orthogonal line** if it is *unencumbered in the direction it is moving*, and if
  the square it passes through is empty.
- **Encumbrance.** A piece is encumbered in a given direction if an enemy piece
  stands on any of the **five squares ahead of or beside it** in that direction.
  For a move north, those are the squares to the **north-west, north, north-east,
  west and east**. The three squares **behind** it — south-west, south and
  south-east — do not encumber it.

  Encumbrance is judged **only from where the piece is standing** when the move
  begins, and only from its own eight surrounding squares. What stands near the
  square it is moving *to* does not matter.

  Because the five squares are measured from the direction of travel, the same
  piece may be free to move two squares one way and restricted to one square
  another way. An enemy behind you does not slow you down.
- **The two-square move may attack.** If the far square holds an enemy piece and
  the square passed through is empty, the move is an attack on it, resolved
  normally.
- **The two-square move is orthogonal only.** There is no two-square diagonal
  move, and no two-square diagonal attack.
- **Immobile pieces.** The Flag never moves.
- A piece may never move onto a square occupied by a **friendly** piece.

### 4.3 Combat

**How an attack works.** The only way to attack is to move a piece onto an
enemy-occupied square. Resolve the result immediately:

- **Attacker wins** — the defender is removed and the attacker advances onto the
  square.
- **Attacker loses** — the attacker is removed; the defender stays where it is.
- **Draw** — both pieces are removed and the square is left empty.

**Rank.** When two numbered pieces fight, the **higher-numbered (stronger) piece
wins** and the lower-numbered piece is removed.

**Equal rank.** When two pieces of the *same* rank fight, the result is a
**draw** — both are removed.

**Formation bonus.** A piece receives a formation bonus when it has a friendly
piece of **equal rank** within one square (orthogonal or diagonal). The bonus is
checked:

- for an attacking piece: before its move;
- for a defending piece: at the moment it is attacked.

**Formation bonus effect.** A piece with the formation bonus **draws** against a
piece one rank stronger, rather than losing. Both pieces are removed.

#### Rank reduction

**Any piece that survives combat is immediately reduced by one rank.** This
applies to the attacker and the defender alike — whichever of them is still
standing when the combat is resolved.

A rank 5 that wins a fight becomes a rank 4, in every respect and for the rest of
the game. It fights as a 4, forms up with other 4s, and is written as a 4. There
is no memory of what it used to be.

Three consequences are worth stating:

- **A draw reduces nothing**, because a draw leaves no survivor.
- **No piece can ever be reduced below rank 1.** A rank 1 draws against another
  rank 1 and loses to everything stronger, so a rank 1 never survives combat and
  the question never arises.
- **Capturing the Flag is not combat.** The Flag does not fight, so a piece that
  captures it is not reduced. (The game ends at that moment in any case.)

#### Sacrificial attacks

Any piece may attack **any** enemy piece it can reach, regardless of relative
strength — attacking a piece you know will beat you is always legal. What a piece
can *reach* is set by [Movement](#42-movement) and
[Diagonal attacks](#44-diagonal-attacks); relative strength never restricts an
attack. An attack in which the **attacking piece does not survive** is a
**sacrificial attack**, and comes in two forms:

- **Complete sacrifice** — the attacker is removed and the defender survives. You
  lose your piece and remove nothing. Note that the defender is still reduced a
  rank for having survived, so this is not the empty gesture it appears: a cheap
  piece can be spent to weaken an expensive one.
- **Partial sacrifice** — the attacker is removed and so is the defender: an
  equal-rank attack, or a formation-bonus draw against a piece one rank stronger.
  You trade your piece for the defender's.

Sacrificial attacks are legal and reset the inactivity counter (see
[Section 5.4](#54-draw--inactivity)).

### 4.4 Diagonal attacks

A piece may attack an enemy piece standing on any of its **immediate diagonal
squares** (up to four, fewer at board edges), moving onto that square exactly as
it would for an orthogonal attack. Combat resolves by the ordinary rules above:
rank, equal rank, the formation bonus and rank reduction all apply unchanged, and
none of them depends on the direction the attack came from.

**Any enemy piece may be attacked diagonally, the Flag included.** Unlike earlier
versions of this game, the Flag has no immunity to diagonal attack and may be
captured from a diagonally adjacent square.

Two restrictions apply:

- **An open path is required.** At least one of the two squares that are
  orthogonally adjacent to *both* the attacker and the target must be **empty**.
  If both of those squares are occupied — by pieces of either side, friendly or
  enemy — the diagonal attack is illegal.

  For example, a piece on C3 attacking a piece on D4 requires that C4 or D3 be
  empty. If both are occupied, the attack cannot be made.
- **One square only, and never without an attack.** There is no two-square
  diagonal attack, and a piece may never step diagonally onto an empty square. The
  diagonal is an attacking direction and nothing else.

The open-path restriction gives the Flag its defence: **pieces packed
orthogonally around a Flag close the diagonals into it**, since each diagonal
approach needs one of its two flanking squares empty. A tightly held Flag can
only be reached head-on — and the pieces holding it can themselves be attacked
orthogonally.

### 4.5 Recording a move

Every square has a unique name: columns are **lettered A–H, left to right**, and
rows are **numbered 1–8**, where **row 1 is White's back row** and row 8 is
Black's — regardless of which physical side of the board White sits at. White's
near-left corner is A1 and Black's far corner is H8.

A move is recorded by writing the square the moving piece started from, `-`, and
the square it moved to. Two marks may be added **immediately after a square**,
and both describe the piece that was standing on that square **when the move
began**:

| Mark | Meaning |
|---|---|
| `x` | that piece did not survive the move |
| `=N` | that piece survived and is now rank `N` |

**In any move involving combat, each of the two squares carries exactly one
mark** — never both, never neither. Every piece in a fight either dies or
survives and is reduced, so there is no third case.

- `A2-A4` — a move with no combat.
- `A2=3-A4x` — the attacker won. The defender on A4 is removed; the attacker,
  which began on A2 and now stands on A4, is reduced to rank 3.
- `A2x-A4=2` — the attacker lost. The attacker is removed; the defender, still on
  A4, is reduced to rank 2.
- `A2x-A4x` — both were removed.
- `A2-A4x` — the **Flag** on A4 was captured. The attacker carries no mark
  because capturing the Flag is not combat. This is the only way a move can mark
  one square and not the other, so this form always means a Flag capture.

#### Simplified form

For entering a move in a text interface, the from-square and to-square may be
written with nothing between them: `A2A4`. This form is **never used for
recording a game**, because it cannot carry the marks above, and a game written
this way cannot be replayed correctly.

---

## 5. Ending the Game

The game ends the moment any of the following is met. Every condition is checked
**after each move**, including the opponent's, so a game never continues past the
point at which it has been decided.

Sections 5.1–5.4 are settled by the position itself. Sections 5.5 and 5.6 are
**declared by a player** and cannot be read off the board.

### 5.1 Win — Flag capture

A player who **captures the opposing Flag**, by moving a piece onto it, wins
immediately. The Flag may be captured orthogonally or diagonally (see
[Section 4.4](#44-diagonal-attacks)).

### 5.2 Loss — Attrition

A player left with **no numbered pieces** loses immediately. The Flag does not
count: a player holding nothing but their Flag has no army and has lost.

### 5.3 Draw — Mutual attrition

If a single move leaves **both** players with no numbered pieces — a trade in
which each side's last piece is removed — the game is a **draw**. Neither player
is credited with the win for having moved last.

### 5.4 Draw — Inactivity

An **inactivity counter** starts at **0** and rises by **1** on every move in
which no piece is removed. Any attack that removes the attacking piece, the
defending piece, or both resets the counter to **0**.

A move that merely reduces a piece's rank without removing anything cannot occur:
every combat removes at least one piece.

If the inactivity counter reaches **40**, the game is a **draw**.

### 5.5 Loss — Resignation

A player may **resign** at any point, conceding the game; the opponent wins
immediately.

Unlike a draw offer, a resignation is not an offer. It needs no acceptance and
cannot be declined, and it is always available — no position prevents a player
from resigning.

### 5.6 Draw — by agreement

The players may agree to a draw at any time: either player may offer a draw on
their turn, and if the opponent accepts, the game ends immediately in a draw. If
the offer is declined, the offering player takes their turn as usual — a draw
offer does not replace or skip a move.

---

## 6. The Fair Play Rule

Players must not stall by shuffling pieces unproductively — prolonging a game
with moves that make no genuine attempt at progress.

---

## 7. Glossary

- **Move** — a single action by one player on their turn (either stepping a piece
  or making an attack). One full round is two moves, one per player.
- **Rank** — a numbered piece's strength, 1 to 5, with 5 the strongest. A piece's
  rank is its whole identity; the name attached to a rank carries no rules
  meaning.
- **Rank reduction** — the reduction of a surviving piece by one rank at the end
  of any combat it lives through.
- **Encumbered** — for a given direction of travel, having an enemy piece on any
  of the five squares ahead of or beside you. The three squares behind you do not
  encumber. An encumbered piece may move only one square.
- **Formation bonus** — a bonus granted to a piece that has a friendly piece of
  equal rank within one square (orthogonal or diagonal), letting it draw against
  a piece one rank stronger instead of losing.
- **Open path** — the requirement that a diagonal attack have at least one of its
  two flanking squares empty.
- **Sacrificial attack** — an attack in which the attacking piece does not
  survive. **Complete:** attacker removed, defender survives (and is reduced).
  **Partial:** both removed.
- **Attrition** — the state of having no numbered pieces left, which loses the
  game immediately. **Mutual attrition**, where one move leaves both players in
  that state, is a draw.
- **Resignation** — conceding the game. The opponent wins immediately; unlike a
  draw offer, it needs no acceptance.
- **Ruleset** — a named body of rules. A ruleset name always means whichever
  edition of it is currently active.
- **Edition** — a specific, permanent version of a ruleset, written
  `<major>-<minor>:<Ruleset>`. An edition fixes every rule setting, so naming one
  names exactly what was played.

---

## Appendix — Ruleset and edition

An **edition** is the permanent, exact answer to "which rules was this game
played under." Every game record states its edition, so the rules behind a stored
game are always recoverable.

An edition id is written `<major>-<minor>:<Ruleset>`. **The major number names
the rules text.** This document is **major 3**, so it describes every edition
numbered `3-`.

### Proposed

| Edition | Settings | In plain terms | Status |
|---|---|---|---|
| `3-0:PRE-RELEASE` | *(none — this major publishes no rule settings)* | 8 × 8 open board; 16-piece army across five ranks; generated starting position; rank reduction on surviving combat | proposed |

**Major 3 launches with no rule settings at all.** Earlier majors carry a table
of named settings that an edition fixes values for; this one has none, and
`3-0:PRE-RELEASE` is defined entirely by the text above. Settings will be
introduced if and when a rule genuinely needs to vary, and — as always — the
first value of any new setting will be the behaviour that preceded it, so
introducing one will never change what this edition means.

**Editions at earlier majors are unaffected.** `2-0:BATTLE`, `2-0:CLASH` and
`2-1:SKIRMISH` were played under a different rules text, which this document does
not contain and does not replace. A record stamped with one of them still names
exactly what it always named. In particular, **rank numbering runs the other way
at major 2**, where rank 1 is the strongest piece; see
[`README.md`](README.md).

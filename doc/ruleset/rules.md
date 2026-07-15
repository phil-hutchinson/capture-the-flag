# Capture the Flag — Official Rules

---

## 1. Overview

Capture the Flag is a two-player battlefield board game played in two phases:

1. **Placement (secret, simultaneous).** Both players arrange their army in
   their own home zone at the same time, without seeing the opponent's setup.
   The armies are revealed together once both are ready.
2. **Play (alternating, fully visible).** From the reveal onward, every piece is
   visible to both players. Players alternate taking one action at a time until
   the game ends.

The primary object of the game is to **capture the opposing Flag**. There are
also other ways to win or end the game — see [Section 5](#5-ending-the-game).

Throughout these rules, a **move** is a single action taken by one player on their
turn. (One full round is two moves: one per player.)

The two sides are designated **White** and **Black**, with White identifying
the player that moves first after piece placement. These colours name the
players throughout these rules — for example when recording moves (see
[Section 4.4](#44-recording-a-move)) — and are the standard used for pieces and
coordinates. The side assignment is settled before placement begins, and
other than the first move it carries no inherent advantage
(see [Section 3](#3-setup--phase-1-placement)).

---

## 2. Components

### 2.1 The board

The board is a **12 × 12 grid**. Reading from one player's side to the other, the
rows are arranged as:

| Rows | Region |
|---|---|
| 4 | Player A home zone |
| 1 | Neutral buffer (empty) |
| 2 | Lakes |
| 1 | Neutral buffer (empty) |
| 4 | Player B home zone |

Each home zone is 4 rows × 12 columns = **48 squares**, exactly enough for one
army.

**Lakes.** Within the two lake rows, the columns follow this pattern (left to
right across all 12 columns):

```
O L L O O L L O O L L O
```

`O` = open, `L` = lake. This forms three separate 2 × 2 lakes, leaving
single-column lanes at the two far edges and double-column lanes through the
interior. Lake squares are impassable to every piece: no piece may end a move on,
or move through, a lake (see [Movement](#42-movement)).

### 2.2 The pieces

Each player commands an identical army of **25 pieces**:

| Rank | Piece | Qty |
|---|---|---|
| 1 | Master-of-Arms | 3 |
| 2 | Champion | 3 |
| 3 | Knight | 3 |
| 4 | Halberdier | 3 |
| 5 | Foot Soldier | 3 |
| 6 | Militia | 3 |
| — | Tower | 6 |
| — | Flag | 1 |

The six numbered pieces form a strict strength order from rank 1 (strongest) to
rank 6 (weakest). Towers and the Flag cannot move or attack but can be attacked. 
All pieces follow the same movement and combat rules with no special abilities.

---

## 3. Setup — Phase 1: Placement

- Each player arranges their **entire 25-piece army** in their own home zone,
  **one piece per square, choosing which squares to fill**.
- Placement is **secret and simultaneous.** Neither player sees the other's
  arrangement until both are finished; the boards are then revealed together.
- **No two towers may be placed next to each other**, including on a diagonal. 
  (This means the eight squares immediately surrounding it, or fewer at board
  edges or next to lakes.)
- There are **no restrictions on where pieces other than towers are placed**,
  subject to the rule that they must be placed in their home zone.
- **Sides are assigned before placement begins** (by lot or by tournament
  schedule): one player is **White**, the other **Black**. White moves first
  once play begins, so **both players know who moves first while they place.**

Once both armies are revealed, the game proceeds to Phase 2.

---

## 4. Phase 2: Play

### 4.1 Turn order

- Play strictly alternates: one move per player, back and forth.
- **Passing is never allowed.** A player who has no legal move on their turn loses
  immediately (see [Section 5.2](#52-loss--no-legal-move)).

### 4.2 Movement

- **Baseline.** On a move, a piece steps **one square orthogonally** (up, down,
  left, or right — never diagonally). It may move into an empty square, or attack
  an enemy piece by moving onto its square (see [Combat](#43-combat)).
- **Unencumbered bonus.** A piece is considered unencumbered if there are no
  enemy pieces in any of the eight surrounding squares (orthogonal or 
  diagonal). When a piece is unencumbered, it may **move two squares 
  orthogonally**, at its option. Multi-square moves require a clear path: no 
  piece of either side may occupy or block the intermediate square.
- **Encumbered movement.** When a piece is encumbered (i.e., an enemy piece 
  occupies any of its eight surrounding squares), it may move only **one square 
  orthogonally**.
- **Immobile pieces.** Towers and the Flag never move.
- **Lakes and blocking.** No piece may enter or pass through a lake.
- A piece may never move onto a square occupied by a **friendly** piece.

### 4.3 Combat

**How an attack works.** The only way to attack is to move a piece onto an
enemy-occupied square. Resolve the result immediately:

- **Attacker wins** — the defender is removed and the attacker advances onto the
  square.
- **Attacker loses** — the attacker is removed; the defender stays where it is.
- **Draw** — both pieces are removed and the square is left empty.

**Rank (numbered pieces).** When two numbered pieces fight, the **lower-numbered
(stronger) piece wins** and the higher-numbered piece is removed.

**Equal rank.** When two pieces of the *same* rank fight, the result is a 
**draw** — both are removed.

**Formation bonus.** A piece receives a formation bonus when it has a friendly 
piece of equal rank within one square (orthogonal or diagonal). The bonus is 
checked:
- For an attacking piece: before its move
- For a defending piece: at the moment it is attacked

**Formation bonus effect.** A piece with the formation bonus will draw against
a piece one rank higher, rather than losing. (Both pieces are removed.)

**Towers.** Any piece attacking a tower results in a draw. Both the tower and the
attacking piece are removed.

#### Sacrificial attacks

Any piece may attack **any** enemy piece, regardless of relative strength —
attacking a piece you know will beat you is always legal. An attack in which the
**attacking piece does not survive** is a **sacrificial attack**, and comes in
two forms that these rules refer to by name:

- **Complete sacrifice** — the attacker is removed and the defender survives
  (for example, attacking a stronger piece). You lose your piece and remove nothing.
- **Partial sacrifice** — the attacker is removed and so is the defender (any
  mutual-loss result you initiate — an equal-rank attack, a formation-bonus draw
  against a piece one rank higher, or a tower attack). You trade your piece for
  the defender's.

Sacrificial attacks are legal and reset the inactivity counter (see [Section 5.3](#53-draw--inactivity)).

### 4.4 Recording a move

Every square has a unique name for writing moves down on a score sheet:
columns are lettered **A–L** left to right, and rows are numbered **1–12**,
where **row 1 is White's back rank** and **row 12 is Black's back rank** —
regardless of which physical side of the board White sits at. For example,
**A1** is White's near-left corner and **L12** is Black's far corner.

A move is recorded by entering the square that the moving piece started from,
`-`, and the square it moved to or attacked. In the case of combat, an `x` is
added immediately after a square to mark that the piece standing there did not
survive the move:

- `A4-A5` — a move with no attack.
- `A4-A5x` — the attacker wins (the defender is removed).
- `A4x-A5` — the attacker loses (a complete sacrifice).
- `A4x-A5x` — mutual loss (a trade).

#### Simplified form

While scorekeeping uses the rules above, a simplified manner of describing the
move (e.g. for selecting a move in a simply text UI) is to include the from-square
and to-square, without any `-` or combat-marking `x`. All of the example moves 
above would be entered as `A4A5`. The simplified form is **never used for
official scorekeeping**.

---

## 5. Ending the Game

The game ends the moment any of the following conditions is met.

### 5.1 Win — Flag capture

A player who **captures the opposing Flag** (by moving a piece onto it) wins
immediately.

### 5.2 Loss — No legal move

A player who **cannot make any legal move** on their turn — all pieces captured 
or every surviving piece boxed in — **loses immediately**. Passing is not allowed.

### 5.3 Draw — Inactivity

An **inactivity counter** starts at **0** and rises by **1** on every move in 
which no piece is captured (i.e., non-attacking moves). Any **attack** that 
results in the removal of either the attacking piece, the defending piece, or 
both resets the counter to **0**. This includes tower destruction.

If the inactivity counter reaches **50**, the game is a **draw**.

### 5.4 Draw — by agreement

The players may agree to a draw at any time: either player may offer a draw on
their turn, and if the opponent accepts, the game ends immediately in a draw. If
the offer is declined, the offering player takes their turn as usual — a draw offer
does not replace or skip a move.

---

## 6. The Fair Play Rule

Players must not stall by shuffling pieces unproductively — prolonging a game with
moves that make no genuine attempt at progress.

---

## 7. Glossary

- **Move** — a single action by one player on their turn (either stepping a piece
  or making an attack). One full round is two moves, one per player.
- **Unencumbered** — a piece with no enemy pieces in any of its eight surrounding squares.
- **Encumbered** — a piece with at least one enemy piece in one of its eight surrounding squares.
- **Formation bonus** — a bonus granted to a piece that has a friendly piece of equal rank 
  within one square (orthogonal or diagonal).
- **Sacrificial attack** — an attack in which the attacking piece does not
  survive. **Complete:** attacker removed, defender survives. **Partial:**
  attacker and defender both removed (a trade you initiate).
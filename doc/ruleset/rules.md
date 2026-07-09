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
also several structural ways the game can end — see [Section 6](#6-ending-the-game).

Throughout these rules, a **move** is a single action taken by one player on their
turn. (One full round is two moves: one per player.)

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

Each player commands an identical army of **48 pieces**:

| Rank | Piece | Qty | Summary |
|---|---|---|---|
| 1 | Lord Marshal | 1 | Beats any piece in a straight fight |
| 2 | Champion | 2 | — |
| 3 | Knight | 4 | May *charge* (attack from 2–3 squares); special rules vs. Knight and Halberdier |
| 4 | Infantry | 4 | Reliable generalist; no special rules |
| 5 | Halberdier | 6 | Cannot be *charged* by a Knight |
| 6 | Militia | 6 | Cheap line troops; no special rules |
| 7 | Skirmisher | 6 | May *rush* (move or attack up to 3 squares) |
| 8 | Archer | 3 | Provides defensive support to an adjacent piece |
| 9 | Sapper | 8 | The only piece that can destroy a Tower |
| Special | Assassin | 1 | Wins whenever it attacks; loses whenever it is attacked |
| — | Tower | 6 | Immobile; cannot attack; only a Sapper destroys it |
| — | Flag | 1 | Immobile; cannot attack; the game ends if it is captured |

The nine numbered pieces form a strict strength order from rank 1 (strongest) to
rank 9 (weakest). The Assassin resolves by its own special rule rather than by
rank. Towers and the Flag are non-combatants.

---

## 3. Setup — Phase 1: Placement

- Each player arranges their **entire 48-piece army** in their own home zone,
  **one piece per square, filling every square** — no square is left empty.
- Placement is **secret and simultaneous.** Neither player sees the other's
  arrangement until both are finished; the boards are then revealed together.
- **There are no restrictions on where a piece may go** beyond filling the home
  zone. Any piece — including the Flag and Towers — may be placed on any square,
  front row included.
- **Turn order is fixed before placement begins** (by lot or by tournament
  schedule) and **both players know who moves first while they place.**

Once both armies are revealed, the game proceeds to Phase 2.

---

## 4. Phase 2: Play

### 4.1 Turn order

- Play strictly alternates: one move per player, back and forth.
- **Passing is never allowed.** A player who has no legal move on their turn loses
  immediately (see [No legal move](#63-loss--no-legal-move)).

### 4.2 Movement

- **Baseline.** On a move, a piece steps **one square orthogonally** (up, down,
  left, or right — never diagonally). It may move into an empty square, or attack
  an enemy piece on an adjacent square (see [Combat](#43-combat)).
- **Knight — charge.** A Knight may instead move **2 or 3 squares in a straight
  line**, but *only* when the move ends in an attack. (A 1-square attack is an
  ordinary attack, not a charge — the distinction matters for the Halberdier and
  Knight-vs-Knight rules.) A charge requires a **clear straight line**: every
  square between the Knight and its target must be empty (no piece of either
  side, and no lake). A Knight may move more than one square **only as part of an
  attack**: any Knight move that does not end in an attack is limited to a single
  square, for any reason — advancing, repositioning, or retreating alike.
- **Skirmisher — rush.** A Skirmisher may move **up to 3 squares in a straight
  line**, for either movement *or* attack, at any time. It has the same clear
  straight-line requirement as a charge. Unlike the Knight's charge, a rush does
  not require an attack — a Skirmisher may dash in and, on a later turn, dash back
  out.
- **Immobile pieces.** Towers and the Flag never move.
- **Lakes and blocking.** No piece may enter or pass through a lake. The
  clear-line requirement for a charge or a rush is broken by any lake square as
  well as by any occupying piece.
- A piece may never move onto a square occupied by a **friendly** piece.

### 4.3 Combat

**How an attack works.** The only way to attack is to move a piece onto an
enemy-occupied square. Resolve the result immediately:

- **Attacker wins** — the defender is removed and the attacker advances onto the
  square.
- **Attacker loses** — the attacker is removed; the defender stays where it is.
- **Mutual loss** — both pieces are removed and the square is left empty.

**Rank (numbered pieces).** When two numbered pieces fight, the **lower-numbered
(stronger) piece wins** and the higher-numbered piece is removed.

**Equal rank.** When two pieces of the *same* rank fight, the result is **mutual
loss** — both are removed. This is the default for every rank, overridden
only by the two exceptions noted below (the Knight-vs-Knight charge and
Assassin-vs-Assassin).

#### Special combat rules

- **Assassin.** Whenever the Assassin *attacks*, it wins — regardless of the
  target's rank. Whenever the Assassin is *attacked*, it loses — regardless of
  the attacker's rank. It is unstoppable on offense but defenseless once engaged.
  This also settles Assassin-vs-Assassin: the *attacking* Assassin wins and the
  defending Assassin is removed (rather than mutual loss). The guaranteed win does
  **not** extend to Towers — only a Sapper can destroy a Tower, so an Assassin that
  attacks a Tower is destroyed like any other non-Sapper.

- **Sapper and Tower.** Only a **Sapper** can destroy a Tower, and it always
  does: a Sapper that attacks a Tower removes it and advances. **Any other piece
  may still attack a Tower, but cannot destroy it** — the attacking piece is
  removed and the Tower stands. (This is a complete sacrifice; see
  [Sacrificial attacks](#sacrificial-attacks) below.) A Tower never attacks and
  never moves.

- **Halberdier vs. Knight (defense only).** A Knight may **not** *charge* a
  Halberdier. To attack a Halberdier, a Knight must approach to an adjacent square
  and attack normally — at which point the Knight still wins (rank 3 beats rank
  5). The Halberdier gains nothing when it *initiates* an attack against a Knight
  or anything else; the ability only denies the charge. It is a "brace against
  cavalry," not a Knight-hunter.

- **Knight vs. Knight — charge exception.** If a Knight **charges** another Knight
  (attacks from 2–3 squares away), the charging Knight **wins and advances**,
  rather than the usual equal-rank mutual loss. An **adjacent** (1-square)
  Knight-vs-Knight attack still resolves as normal mutual loss. Only a
  genuine charge triggers the exception; there is no equivalent for the
  Skirmisher's rush.

- **Archer — defensive support.** An Archer supports a friendly piece that is
  **defending** an attack. If a friendly piece adjacent to an Archer **loses a
  defensive combat**, and the Archer stands on the square **directly opposite the
  attacker** — that is, one square beyond the defender, continuing the exact
  straight line the attacker traveled — then the result becomes **mutual
  loss** instead of a clean loss: the victorious attacker is struck down as
  it moves into the square it just won.
  - The trigger square is always well-defined: every attack arrives along a
    straight orthogonal line, so "opposite the attacker" is simply one square
    beyond the defender in the attacker's direction of travel, regardless of how
    far the attack originated.
  - Support applies **only when the adjacent friendly piece is defending**, never
    when it is attacking.
  - "Friendly piece" **includes a Tower.** An Archer directly opposite a Sapper's
    line of demolition turns the demolition into a trade — the Tower is destroyed
    and the Sapper is slain.
  - If the trigger square is off the board, a lake, or otherwise not occupied by
    a friendly Archer facing that line, there is no support.
  - The Archer's *own* combat is ordinary: when an Archer attacks or is attacked
    directly, it fights by its rank (rank 8). The support ability protects a
    neighboring defender, never the Archer itself.

#### Sacrificial attacks

Any piece may attack **any** enemy piece, regardless of relative strength —
attacking a piece you know will beat you is always legal. An attack in which the
**attacking piece does not survive** is a **sacrificial attack**, and comes in
two forms that these rules refer to by name:

- **Complete sacrifice** — the attacker is removed and the defender survives
  (for example, attacking a stronger piece, or a non-Sapper attacking a Tower).
  You lose your piece and remove nothing.
- **Partial sacrifice** — the attacker is removed and so is the defender (any
  mutual-loss result you initiate — an equal-rank attack, or an attack an
  Archer converts into a trade). You trade your piece for the defender's.

Sacrificial attacks are legal and interact with the inactivity and progress rules
— see [Section 6.4](#64-loss--inactivity) and [Section 6.5](#65-draw--no-progress).

### 4.4 Recording a move

Every square has a unique name for writing moves down on a score sheet:
columns are lettered **A–L** left to right, and rows are numbered **1–12**,
where **row 1 is White's back rank** and **row 12 is Black's back rank** —
regardless of which physical side of the board White sits at. For example,
**A1** is White's near-left corner and **L12** is Black's far corner.

A move is written as its source square followed by its destination square,
with no space or separator between them — for example, **A4A5** for a move or
attack from A4 to A5. A move always travels in a single straight line, and
every square parses unambiguously (a letter followed by its 1–2 digit row
number, ended by the next letter), so this alone is enough to record — and
later replay — an entire game: the result of an attack always follows
automatically from the position and the rules, so it does not need to be
written down separately.

A score sheet may instead use an extended form that also marks the *result*
of each move directly. This form is always written with a `-` between the two
squares (which is how it is told apart from the plain form above), with an
`x` immediately after a square to mark that the piece standing there did not
survive the move:

- `A4-A5` — a move with no attack.
- `A4-A5x` — the attacker wins (the defender is removed).
- `A4x-A5` — the attacker loses (a complete sacrifice).
- `A4x-A5x` — mutual loss (a trade).

---

## 5. Reachability

The Unbreachable Flag condition ([Section 6.2](#62-win--unbreachable-flag)) turns
on whether a piece can **structurally reach** a target square. One square
structurally reaches another when a path of single orthogonal steps connects them
while treating **lakes, the relevant Towers, and the relevant Flag as impassable**
and **ignoring all mobile pieces**. Section 6.2 specifies which Towers and Flag act
as walls for each check.

---

## 6. Ending the Game

The game ends the moment any of the following conditions is met.

### 6.1 Win — Flag capture

A player who **captures the opposing Flag** (by moving a piece onto it) wins
immediately.

### 6.2 Win — Unbreachable Flag

A player **wins immediately** when **both** of the following hold:

1. **Every one of the opponent's Sappers is unavailable.** A Sapper is
   *unavailable* if it has been captured, **or** if it currently cannot reach any
   of this player's Towers by any legal path (i.e., a Sapper sealed in behind its
   own side's Towers). Availability is judged against the *current* board using
   the reachability notion in [Section 5](#5-reachability).
2. **This player's own Flag is fully enclosed by intact Towers** (together with
   the board edge), so that **no non-Sapper enemy piece could ever reach it.**

Edge cases:

- **Enclosure can only be reduced, never built.** A player who has not fully
  enclosed their Flag by the end of placement can never meet condition 2 (Towers
  never move or appear during play, so enclosure only degrades as Towers are
  destroyed).
- **Availability is re-checked continuously.** A Sapper that is unavailable can
  become available again — for instance if a Tower blocking its only path is
  destroyed — so availability is evaluated against the board as it currently
  stands.
- **Mutual last-Sapper trade → draw.** If each side's last available Sapper
  destroys the other in a single combat (equal-rank mutual loss), both
  sides lose their last available Sapper at once. If **both** flags are still
  fully enclosed at that moment, both conditions are met simultaneously and the
  game is a **draw**. If only **one** flag is still enclosed, only that side's
  condition is met and that side **wins**.

### 6.3 Loss — No legal move

A player who **cannot make any legal move** on their turn — every piece captured,
or every surviving piece boxed in — **loses immediately**. Passing is not allowed.

### 6.4 Loss — Inactivity

Each player has a personal **inactivity counter**, starting at **0**:

- Any **attack you make** — a winning attack, a trade, or a sacrifice — resets
  **your** counter to **0**.
- Any of **your** moves that is not an attack raises **your** counter by **1**.
- Any **sacrificial attack your opponent makes** (complete or partial) also resets
  **your** counter to **0**.

If a player's counter reaches **50**, that player **loses immediately**.

### 6.5 Draw — No progress

A single shared **progress counter** starts at **0** and rises by **1** on every
ply in which no piece is captured. A **capture** — any attack in which the
defending piece is removed (a winning attack or a mutual loss), including a Sapper
destroying a Tower — resets it to **0**; a complete sacrifice captures nothing and
does not reset it.

If the progress counter reaches **80** (40 turns for each player), the game is a
**draw**.

### 6.6 Draw — by agreement

The players may agree to a draw at any time: either player may offer a draw on
their turn, and if the opponent accepts, the game ends immediately in a draw. If
the offer is declined, the offering player takes their turn as usual — a draw offer
does not replace or skip a move.

---

## 7. The Fair Play Rule

Players must not stall by shuffling pieces unproductively — prolonging a game with
moves that make no genuine attempt at progress.

---

## 8. Glossary

- **Move** — a single action by one player on their turn (either stepping a piece
  or making an attack). One full round is two moves, one per player.
- **Charge** — a Knight's 2–3-square straight-line attack (attack-only).
- **Rush** — a Skirmisher's up-to-3-square straight-line move or attack.
- **Sacrificial attack** — an attack in which the attacking piece does not
  survive. **Complete:** attacker removed, defender survives. **Partial:**
  attacker and defender both removed (a trade you initiate).
- **Available Sapper** — a Sapper that is on the board and can currently reach an
  enemy Tower by a legal path (see [Section 5](#5-reachability)).
- **Enclosed Flag** — a Flag that no non-Sapper enemy piece can structurally
  reach, walled off by intact Towers and the board edge.

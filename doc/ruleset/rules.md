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

### Two rulesets

Capture the Flag is played in two forms, which share every rule in this document
and differ only in the board and the army:

- **Battle** — a 12 × 12 board and an army of 25 pieces across six ranks.
- **Skirmish** — an 8 × 8 board and an army of 16 pieces across four ranks.

Both are described in full in [Section 2](#2-components). Neither is a variation
on the other, and everything in Sections 3–7 applies identically to both.

**If you are learning the game, start with Skirmish.** The smaller board and the
shorter rank order make it quicker to play and easier to hold in your head, and
nothing you learn there has to be unlearned for Battle.

---

## 2. Components

### 2.1 The board

Both boards are square, divided into two home zones separated by lake rows.

#### Battle — 12 × 12

Reading from one player's side to the other, the rows are arranged as:

| Rows | Region |
|---|---|
| 4 | Player A home zone |
| 1 | Neutral buffer (empty) |
| 2 | Lakes |
| 1 | Neutral buffer (empty) |
| 4 | Player B home zone |

Each home zone is 4 rows × 12 columns = **48 squares**.

Within the two lake rows, the columns follow this pattern (left to right across
all 12 columns):

```
O L L O O L L O O L L O
```

This forms three separate 2 × 2 lakes.

#### Skirmish — 8 × 8

| Rows | Region |
|---|---|
| 3 | Player A home zone |
| 2 | Lakes |
| 3 | Player B home zone |

Each home zone is 3 rows × 8 columns = **24 squares**. There are **no neutral
buffer rows**: each home zone sits directly against the lakes, so the two armies
begin closer together than on the Battle board.

Within the two lake rows, the columns follow this pattern (left to right across
all 8 columns):

```
O L L O O L L O
```

This forms two separate 2 × 2 lakes.

#### Both boards

`O` = open, `L` = lake. On either board the lakes leave single-column lanes at
the two far edges and a double-column lane through the interior.

**Lake squares are impassable to every piece:** no piece may end a move on, or
move through, a lake (see [Movement](#42-movement)).

A home zone is always larger than the army that fills it, so a player always has
a choice of which squares to occupy (see [Section 3](#3-setup--phase-1-placement)).

### 2.2 The pieces

Each player commands an army identical to their opponent's. Its composition
depends on the ruleset.

#### Battle — 25 pieces

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

#### Skirmish — 16 pieces

| Rank | Piece | Qty |
|---|---|---|
| 1 | Master-of-Arms | 3 |
| 2 | Champion | 3 |
| 3 | Knight | 3 |
| 4 | Halberdier | 3 |
| — | Tower | 3 |
| — | Flag | 1 |

Skirmish uses the top four ranks only; Foot Soldier and Militia do not appear.

#### Both armies

The numbered pieces form a strict strength order, **rank 1 being the strongest**
and the highest-numbered rank the weakest. Towers and the Flag cannot move or
attack but can be attacked. All pieces follow the same movement and combat rules
with no special abilities.

---

## 3. Setup — Phase 1: Placement

- Each player arranges their **entire army** (Section 2.2) in their own home
  zone, **one piece per square, choosing which squares to fill**.
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
  left, or right). It may move into an empty square, or attack an enemy piece by
  moving onto its square (see [Combat](#43-combat)).
- **Diagonal attacks only.** A piece may also move **one square diagonally, but
  only to attack a movable enemy piece** — see
  [Diagonal attacks](#diagonal-attacks). A piece may never move diagonally onto
  an empty square.
- **Unencumbered bonus.** A piece is considered unencumbered if there are no
  enemy pieces in any of the eight surrounding squares (orthogonal or 
  diagonal). When a piece is unencumbered, it may **move two squares 
  orthogonally**, at its option. Multi-square moves require a clear path: no 
  piece of either side may occupy or block the intermediate square. The bonus
  never applies diagonally: a two-square diagonal move does not exist, and a
  piece with an enemy on its diagonal is by definition encumbered.
- **Encumbered movement.** When a piece is encumbered (i.e., an enemy piece 
  occupies any of its eight surrounding squares), it may move only **one square 
  orthogonally** — or make a **one-square diagonal attack**, which is only ever
  available to an encumbered piece in any case.
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

#### Diagonal attacks

A piece may attack a piece standing on any of its **four immediate diagonal
squares**, moving onto that square exactly as it would for an orthogonal attack.
Combat then resolves by the ordinary rules above: rank, equal rank, and the
formation bonus all apply unchanged, and none of them depends on the direction
the attack came from.

Three restrictions apply:

- **One square only.** There is no two-square diagonal attack. The unencumbered
  bonus never extends a diagonal — and a piece with an enemy on its diagonal is
  encumbered in any case.
- **Movable targets only.** A diagonal attack may be made only against a piece
  that is able to move — that is, against a numbered piece. **Towers and the Flag
  may not be attacked diagonally.** They can still be attacked, but only
  orthogonally.
- **No diagonal move without an attack.** A piece may never step diagonally onto
  an empty square. The diagonal is an attacking direction and nothing else.

The most important consequence: **the Flag can only ever be captured from an
orthogonally adjacent square** (see [Section 5.1](#51-win--flag-capture)).

Sacrificial attacks of both kinds (below) are permitted diagonally, subject to
the same restrictions — a complete or partial sacrifice against a numbered piece
is legal on the diagonal, while a tower attack, which is always a partial
sacrifice, is not.

#### Sacrificial attacks

Any piece may attack **any** enemy piece it can reach, regardless of relative
strength — attacking a piece you know will beat you is always legal. (Relative
strength never restricts an attack. What a piece can *reach* is set by
[Movement](#42-movement) and by [Diagonal attacks](#diagonal-attacks).) An attack
in which the **attacking piece does not survive** is a **sacrificial attack**,
and comes in two forms that these rules refer to by name:

- **Complete sacrifice** — the attacker is removed and the defender survives
  (for example, attacking a stronger piece). You lose your piece and remove nothing.
- **Partial sacrifice** — the attacker is removed and so is the defender (any
  mutual-loss result you initiate — an equal-rank attack, a formation-bonus draw
  against a piece one rank higher, or a tower attack). You trade your piece for
  the defender's.

Sacrificial attacks are legal and reset the inactivity counter (see [Section 5.3](#53-draw--inactivity)).

### 4.4 Recording a move

Every square has a unique name for writing moves down on a score sheet:
columns are **lettered from A, left to right**, and rows are **numbered from 1**,
where **row 1 is White's back rank** and the highest-numbered row is **Black's
back rank** — regardless of which physical side of the board White sits at.

| Ruleset | Columns | Rows | White's near-left corner | Black's far corner |
|---|---|---|---|---|
| Battle | A–L | 1–12 | A1 | L12 |
| Skirmish | A–H | 1–8 | A1 | H8 |

The notation is the same on either board; only the range of coordinates differs.

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

The Flag is not a movable piece, so it **cannot be attacked diagonally** (see
[Diagonal attacks](#diagonal-attacks)). Capturing it always means moving in from
an **orthogonally adjacent** square.

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
- **Movable piece** — a numbered piece (any rank). Towers and the Flag are not
  movable pieces. Only movable pieces may be attacked diagonally.
- **Diagonal attack** — an attack on a movable enemy piece standing one square
  diagonally away. Diagonal movement is never allowed without an attack, and
  Towers and the Flag can never be attacked this way (Section 4.3).
- **Sacrificial attack** — an attack in which the attacking piece does not
  survive. **Complete:** attacker removed, defender survives. **Partial:**
  attacker and defender both removed (a trade you initiate).
- **Ruleset** — a named body of rules, such as Battle or Skirmish. A ruleset name
  always means whichever edition of it is currently active (Appendix B).
- **Edition** — a specific, permanent version of a ruleset, written
  `<major>-<minor>:<Ruleset>` — for example `2-0:SKIRMISH`. An edition fixes a
  value for **every** variant setting, the board and the army included, so naming
  one names exactly what was played.
- **Variant** — a named rule setting that can be switched away from its standard
  value. Published variants are listed in Appendix A.

---

## Appendix A — Variants

A **variant** is a single named rule setting with two or more named values, one
of which is its **default**.

Sections 1–7 describe both published rulesets in full, so you do not need this
appendix to play either of them. What it provides is the vocabulary that names
*which* set of rules a given game used — the thing every game record and every
trained engine stamps itself with — and a defined place for future settings to
land.

Three promises govern this appendix:

1. **A variant's default is always the rule that came before it.** Introducing a
   variant never changes how the game is played by default, and never changes
   what any earlier edition or any recorded game meant. Turning a variant away
   from its default is always a deliberate choice.
2. **Names are permanent.** Once a variant and its values are published here,
   those names are never reused for different behavior and never redefined. A
   rule change that would alter what a published name means gets a new name
   instead.
3. **This appendix only grows, and entries only get clearer.** Entries are added
   and never removed. Their wording may be revised freely — a clearer sentence, a
   worked example, an ambiguity resolved — but a revision may never change the
   substance of a published variant. The test: if every game legal under the old
   wording is still legal under the new one and resolves the same way, it is a
   clarification and welcome. If not, it is a different variant, and it gets its
   own name rather than replacing this one.

Each entry gives the variant's identifier, its available values, which value is
the default, and what each value does in play.

Variants that are still being considered are *not* listed here — they live in
[`proposed-variants.md`](proposed-variants.md), which carries no promises at all
and may change or disappear at any time. A variant reaches this appendix only
once it is actually implemented in the game.

### `BOARD_LAYOUT`

**Values:** `standard_144` | `standard_64` — **default `standard_144`**

Selects the board. A value names a **complete layout**, not just a size: the grid
dimensions, how many rows each home zone occupies, and where the lakes sit.

| Value | Grid | Rows | Home zone | Lakes |
|---|---|---|---|---|
| `standard_144` | 12 × 12 | 4 home / 1 buffer / 2 lake / 1 buffer / 4 home | 48 squares | three 2 × 2 |
| `standard_64` | 8 × 8 | 3 home / 2 lake / 3 home | 24 squares | two 2 × 2 |

Both layouts are described in full in [Section 2.1](#21-the-board):
`standard_144` is the Battle board, `standard_64` the Skirmish board.

Because a value names the whole layout, a board that differed only in its
home-zone depth — the same 8 × 8 grid with two home rows instead of three — would
be a **new value**, not an adjustment to this one.

### `ARMY_COMPOSITION`

**Values:** `standard_battle` | `standard_skirmish` — **default `standard_battle`**

Selects the army each player commands.

| Value | Army | Total |
|---|---|---|
| `standard_battle` | 3 each of ranks 1–6, 6 Towers, 1 Flag | 25 |
| `standard_skirmish` | 3 each of ranks 1–4, 3 Towers, 1 Flag | 16 |

Both armies are listed in full in [Section 2.2](#22-the-pieces).

### Combining these two

`BOARD_LAYOUT` and `ARMY_COMPOSITION` are set independently, so it is possible to
name a combination that **cannot be played**: an army must fit in its home zone,
one piece per square, with squares to spare. `standard_battle` on `standard_64`
asks 25 pieces to occupy 24 squares and is therefore **not a valid setting for
play**. The published rulesets in Appendix B always pair them validly.

This restriction is about *playing* a game. It does not apply to reading a
recorded one: a record shows the board it was played on, and a record may begin
from a position part-way through a game that had no placement phase to be valid
or invalid.

---

## Appendix B — Rulesets

An **edition** is the permanent, exact answer to "which rules was this game
played under": a value for every variant, together with the numbered rules text
those variants apply to. A **ruleset name** points at whichever of its editions
is current, and that pointer moves when a new edition is published. Every game
record and every trained engine records its edition, so the rules behind a stored
game are always recoverable.

An edition id is written `<major>-<minor>:<Ruleset>`. **The major number names
the rules text**; the variant values fill in the settings that text leaves open.
This document is **major 2**, so it describes every edition numbered `2-`.
Editions at an earlier major were played under earlier rules text, which this
document no longer contains — their entries remain below so that a stored game
still names something real.

The two tables share the same fields. **Active** lists the current edition of
every ruleset on offer; **Historical** lists editions no longer pointed at.
Editions in both tables are equally permanent — retiring an edition does not
change what it meant, it only stops it from being the one currently played.

### Active

| Edition | Variant values | In plain terms | Status |
|---|---|---|---|
| `2-0:BATTLE` | `BOARD_LAYOUT=standard_144`, `ARMY_COMPOSITION=standard_battle` | 12 × 12 board; 25-piece army across six ranks | active |
| `2-0:SKIRMISH` | `BOARD_LAYOUT=standard_64`, `ARMY_COMPOSITION=standard_skirmish` | 8 × 8 board; 16-piece army across four ranks | active |

Both rulesets are offered and maintained together. They share this entire rules
text and differ only in the two variant values shown. **Skirmish** is the
recommended starting point for a new player (see
[Section 1](#two-rulesets)); **Battle** is the larger game.

The "in plain terms" column restates the variant values for readability. The
variant values are what the edition actually fixes.

### Historical

| Edition | Variant values | In plain terms | Status |
|---|---|---|---|
| `1-2:PRE-RELEASE` | *(predates both variants; resolves to their defaults)* | 12 × 12 board; 25-piece army across six ranks | retired |

`PRE-RELEASE` was the ruleset used while the game was being shaped before
release. It was retired when Battle and Skirmish were published. Being a major-1
edition, it was played **without diagonal attacks** and on the 12 × 12 board
only — under rules text this document no longer carries.

The **Status** column carries one of two reasons an edition left the Active
table:

- **superseded** — a newer edition of the same ruleset exists, and the ruleset
  name now points at that one.
- **retired** — the ruleset name itself is no longer offered.

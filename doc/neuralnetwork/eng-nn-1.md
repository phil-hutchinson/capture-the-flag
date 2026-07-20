# Neural Network Input/Output Guide

Name: ENG_NN_1

See [README.md](README.md) for what this specification covers and when a new
one is minted.

## Compatible Rulesets

Each entry is a complete (version, name, flags) combination:

| Version | Name        | Flags  |
|---------|-------------|--------|
| 1.2     | PRE-RELEASE | (none) |

## Input

The input to the engine is an (18,12,12) tensor, representing
(Feature Planes, Row, Column). Values are floats. At inference the network
takes a batch of positions with a leading batch axis: (N,18,12,12).

### Perspective and coordinates

The input is always from the perspective of the player to move; the board is
rotated 180° when Black is to move. In tensor coordinates the mover's own back
rank is always row 0, and the mover advances toward increasing row index.

- **White to move:** tensor row = board row − 1 (board rows are 1–12, row 1 =
  White's back rank); tensor column = board column (A=0 … L=11).
- **Black to move:** tensor row = 12 − board row; tensor column = 11 − board
  column.

### Feature Planes

#### Piece presence: 1 if present, 0 if not present

- 0: Our Flag
- 1: Our Tower
- 2: Our Master-of-Arms
- 3: Our Champion
- 4: Our Knight
- 5: Our Halberdier
- 6: Our Foot Soldier
- 7: Our Militia
- 8: Their Flag
- 9: Their Tower
- 10: Their Master-of-Arms
- 11: Their Champion
- 12: Their Knight
- 13: Their Halberdier
- 14: Their Foot Soldier
- 15: Their Militia

#### Additional position characteristics

- 16: Passable (0 for Lakes, 1 for playable squares)
- 17: Inactivity Count — every square filled uniformly with
  (current inactivity count / draw threshold). The threshold is 50 in
  ruleset 1.2 (rules.md §5.3).

## Output

### Value head

A single element per position, in [−1, 1], **from the perspective of the
player to move**: +1 means the player to move is winning, −1 losing.

### Policy head

An (8,12,12) tensor, representing (Movement Index, Row, Column). Row and
column identify the ply's **source square**, in the same perspective frame as
the input (rotated 180° for Black); the movement index gives the destination
as an offset from that square.

The entries are **raw logits**, not probabilities. The consumer obtains the
legal plies from the rules engine, selects only those entries, and applies a
softmax over that legal set. Entries at illegal locations carry no meaning
and must be ignored — the network never guarantees anything about them.

#### Movement Index

The movement index represents an offset from the source square, and is used
for both combat and non-combat plies.

Entries (row delta, column delta):

- 0: Up one square (1, 0)
- 1: Right one square (0, 1)
- 2: Down one square (-1, 0)
- 3: Left one square (0, -1)
- 4: Up two squares (2, 0)
- 5: Right two squares (0, 2)
- 6: Down two squares (-2, 0)
- 7: Left two squares (0, -2)

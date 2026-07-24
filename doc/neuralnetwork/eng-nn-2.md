# Neural Network Input/Output Guide

Name: ENG_NN_2

See [README.md](README.md) for what this specification covers and when a new
one is minted. Supersedes [ENG_NN_1](eng-nn-1.md): no rule change, but the
input gains eighteen feature-engineered planes (flag-relative distance,
army-strength), which widens the tensor contract. The output contract is
unchanged from `ENG_NN_1` and carries over verbatim below.

## Compatible Rulesets

Each entry is a complete (version, name, flags) combination:

| Version | Name        | Flags  |
|---------|-------------|--------|
| 1.2     | PRE-RELEASE | (none) |

Same combination(s) as `ENG_NN_1` — no rule changed, so the input still
faithfully represents every distinguishable state and the action space is
untouched.

## Input

The input to the engine is a (34,12,12) tensor, representing
(Feature Planes, Row, Column). Values are floats. At inference the network
takes a batch of positions with a leading batch axis: (N,34,12,12).

### Perspective and coordinates

The input is always from the perspective of the player to move; the board is
rotated 180° when Black is to move. In tensor coordinates the mover's own back
rank is always row 0, and the mover advances toward increasing row index.

- **White to move:** tensor row = board row − 1 (board rows are 1–12, row 1 =
  White's back rank); tensor column = board column (A=0 … L=11).
- **Black to move:** tensor row = 12 − board row; tensor column = 11 − board
  column.

Every plane — piece presence and the two engineered families alike — is
computed in this same side-to-move frame: "own"/"our" and "enemy"/"their"
always track the mover, never a fixed colour. Rotating a position 180°,
swapping every piece's side label (White↔Black), and flipping the side to
move produces an equivalent position — the two encode to identical tensors.

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

#### Flag-relative distance (new in ENG_NN_2)

Each square's **signed** offset to a flag, along one axis, normalized by the
board's extent along that axis (12 squares). Rows and columns are the ones
defined above — 0–11, already in the mover's frame:

```
row offset    = (flag's row    − square's row)    / 12
column offset = (flag's column − square's column) / 12
```

Positive means the flag lies at a higher row/column than the square, negative
the reverse. Values fall in (−11/12, 11/12) ⊂ (−1, 1). A flag is always
present during play (its capture ends the game), so these planes are always
defined.

- 18: Signed row offset to **our** flag
- 19: Signed column offset to **our** flag
- 20: Signed row offset to **their** flag
- 21: Signed column offset to **their** flag

#### Army strength (new in ENG_NN_2)

For each side and each of the six mobile ranks, the fraction of that rank's
starting roster still on the board:

```
strength = count_remaining_of_rank / roster_count_of_rank
```

`roster_count_of_rank` is however many pieces of that rank each player fields,
per the ruleset (rules.md §2.2) — under the current 1.2/PRE-RELEASE ruleset
this is `3` for every mobile rank. The formula is defined against the
ruleset's roster, not a literal number, so a future ruleset combination with a
different roster count does not by itself force a new spec: the plane's
meaning stays "fraction of that rank's starting strength remaining," always in
`[0, 1]`.

Every square in a plane carries the same value (a per-position scalar,
broadcast across the plane — the same pattern as Inactivity Count above). A
value of `1.0` means the rank is intact; `0.0` means it has been wiped out.
Only the six mobile ranks are represented — Tower and Flag are excluded (the
Flag count is always 1 during play and carries no information; Tower is out of
scope for this spec).

- 22: Our Master-of-Arms remaining fraction
- 23: Our Champion remaining fraction
- 24: Our Knight remaining fraction
- 25: Our Halberdier remaining fraction
- 26: Our Foot Soldier remaining fraction
- 27: Our Militia remaining fraction
- 28: Their Master-of-Arms remaining fraction
- 29: Their Champion remaining fraction
- 30: Their Knight remaining fraction
- 31: Their Halberdier remaining fraction
- 32: Their Foot Soldier remaining fraction
- 33: Their Militia remaining fraction

## Output

Unchanged from `ENG_NN_1`.

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

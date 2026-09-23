# Neural Network Input/Output Guide

Name: ENG_NN_4

See [README.md](README.md) for what this specification covers and when a new
one is minted. Supersedes [ENG_NN_3](eng-nn-3.md) to remove obsolete or
discontinued feature planes:

1. **Removal of tower and rank-six feature planes.** Towers are no longer present
   in the ruleset; neither are rank-six pieces. So related feature planes have been
   removed. (The remaining feature planes for rank-based pieces have been updated
   with the new names, and importantly, they start from the *highest rank* due to
   the change in rank numbering.)
2. **Removal of distance-from-flag feature planes.** With lakes removed and a
   smaller board, this hint may no longer be necessary to kickstart the learning
   process. Better to begin without it and add it later than to include it
   without knowing it is necessary.
3. **Removal of army-strength feature planes.** Each plane read as a fraction of
   that rank's *starting* roster remaining, which rank reduction breaks: a rank's
   population is no longer bounded by how many the army began with, since combat
   can now push a piece down into it from above. Rather than choose a new
   normaliser, these planes are removed in favour of leaving material strength to
   the machine-learning process to discover directly from the presence planes,
   which still carry the same information positionally.

Another important change is **rank reduction**: a piece that survives combat is
reduced by one rank (`rules.md` §4.3). Strictly speaking this would have been
achievable within the previous engine — a rank change is just a different
one-hot plane activation, nothing the action space or plane layout has to
express specially — so it was not itself a reason for a new engine spec.

Another ruleset change was **removal of lake squares**. This also does not affect
the engine interface, because the related feature plane has been retained: it is
now constant everywhere on the one published board, but still lets the network
tell a real edge square from the zero-padding a convolution adds at the border.

## Compatible Rulesets

Each entry is a complete (edition, flags) combination. An edition is
`<major>-<minor>:<Ruleset>` and already fixes every flag value, so a row with no
deviating flags names exactly one ruleset (see `doc/ruleset/rules.md` Appendix B):

| Edition           | Deviating flags | Board | Army                        |
|-------------------|-----------------|-------|------------------------------|
| `3-0:PRE-RELEASE` | (none)          | 8 × 8 | 3 each of ranks 1–5, 1 Flag |

This is the one **Active** edition (`rules.md` Appendix B), and major 3
publishes no rule flags at all, so it is also the only combination this spec
has to serve. Nothing here is parametric across several live rulesets the way
`ENG_NN_3` was across Battle, Clash and Skirmish — the board symbols below stay
general only so a second major-3 ruleset, if one is ever published, does not by
itself force another spec.

Every earlier edition is **not** compatible: `2-0:BATTLE`, `2-0:CLASH`,
`2-1:SKIRMISH` and the historical `2-0:SKIRMISH` are all retired major-2
editions whose army fields a Tower and a sixth rank this spec's planes have no
subject for, and rank reduction gives major 3 mutable ranks major 2 never had.
`1-2:PRE-RELEASE` is a major-1 edition and was already incompatible with
`ENG_NN_2` and `ENG_NN_3` for want of diagonal entries in the action space; that
does not change here. No weights trained under any of them survive.

A network is shaped for the one combination above and its parameters are not
portable to another edition — which is moot while only one edition exists, but
is why a checkpoint's stamp still records the combination it was trained under,
and why the spec name is qualified by board (`ENG_NN_4/simple_64`) wherever it
identifies an artifact rather than a contract.

## Board parameters

Everything below is stated in two numbers, fixed for a given ruleset:

| Symbol | Meaning       | `3-0:PRE-RELEASE` |
|--------|---------------|--------------------|
| `R`    | board rows    | 8                  |
| `C`    | board columns | 8                  |

## Input

The input to the engine is a (14,`R`,`C`) tensor, representing
(Feature Planes, Row, Column). Values are floats. At inference the network
takes a batch of positions with a leading batch axis: (N,14,`R`,`C`).

### Perspective and coordinates

The input is always from the perspective of the player to move; the board is
rotated 180° when Black is to move. In tensor coordinates the mover's own back
rank is always row 0, and the mover advances toward increasing row index.

- **White to move:** tensor row = board row − 1 (board rows are 1–`R`, row 1 =
  White's back rank); tensor column = board column (A=0 …).
- **Black to move:** tensor row = `R` − board row; tensor column = `C` − 1 −
  board column.

Every piece-presence plane is computed in this same side-to-move frame:
"own"/"our" and "enemy"/"their" always track the mover, never a fixed colour.
Rotating a position 180°,
swapping every piece's side label (White↔Black), and flipping the side to
move produces an equivalent position — the two encode to identical tensors.

#### Piece presence: 1 if present, 0 if not present

- 0: Our Flag
- 1: Our Master-of-Arms
- 2: Our Champion
- 3: Our Foot Soldier
- 4: Our Militia
- 5: Our Peasant
- 6: Their Flag
- 7: Their Master-of-Arms
- 8: Their Champion
- 9: Their Foot Soldier
- 10: Their Militia
- 11: Their Peasant

#### Additional position characteristics

- 12: Passable — 1 on every square of the one published board, which has no
  impassable squares. Carried forward from `ENG_NN_3` rather than dropped: a
  convolution pads its input with zeros at the border, and without this plane
  those padding zeros are indistinguishable from an in-board square reading
  zero everywhere else — this plane is what lets the network tell "off the
  board" from "on it but empty of anything else."
- 13: Inactivity Count — every square filled uniformly with
  (current inactivity count / draw threshold). The threshold is 40
  (rules.md §5.4).

### Why White's first ply needs no plane

Major 3 limits **White's first move of the game to one square** (rules.md
§4.1), which makes the legal set depend on something that is not on the board:
the same arrangement admits two-square plies at ply 1 and does not at ply 0. A
plane that encoded ply count would answer this, and none is specified. The
argument that none is needed is worth stating, because the omission otherwise
looks like a compatibility failure.

Two positions that differ *only* in whether the restriction applies would have
to share a board, a side to move, and an inactivity count while sitting at ply
0 and at some later ply. They cannot. Reaching ply 0's arrangement again
requires that no piece was ever removed — a removal is irreversible, since
pieces never return to the board and rank reduction only ever moves a survivor
*down* — and §5.4 raises the inactivity counter on exactly the plies that
remove nothing. So a later position with ply 0's board has a counter equal to
its ply count, and ply 0's counter is 0: plane 13 already separates them.

The restriction therefore never collapses two distinguishable positions into
one tensor, and the network is free to learn it as a property of the
low-inactivity-count opening rather than from a dedicated input.

## Output

### Value head

A single element per position, in [−1, 1], **from the perspective of the
player to move**: +1 means the player to move is winning, −1 losing. Unchanged
from `ENG_NN_1` and `ENG_NN_2`.

### Policy head

A (12,`R`,`C`) tensor, representing (Movement Index, Row, Column). Row and
column identify the ply's **source square**, in the same perspective frame as
the input (rotated 180° for Black); the movement index gives the destination
as an offset from that square.

The entries are **raw logits**, not probabilities. The consumer obtains the
legal plies from the rules engine, selects only those entries, and applies a
softmax over that legal set. Entries at illegal locations carry no meaning
and must be ignored — the network never guarantees anything about them.

#### Movement Index

The movement index represents an offset from the source square, and is used
for both combat and non-combat plies. It does **not** vary by board: the
entries are square-to-square deltas, so the same twelve address every ply on
every layout, and only the number of source squares they are indexed from
changes.

Entries (row delta, column delta):

- 0: Up one square (1, 0)
- 1: Right one square (0, 1)
- 2: Down one square (-1, 0)
- 3: Left one square (0, -1)
- 4: Up two squares (2, 0)
- 5: Right two squares (0, 2)
- 6: Down two squares (-2, 0)
- 7: Left two squares (0, -2)
- 8: Up-right one square (1, 1)
- 9: Up-left one square (1, -1)
- 10: Down-right one square (-1, 1)
- 11: Down-left one square (-1, -1)

Indices 0–7 are unchanged from `ENG_NN_2`; 8–11 are the diagonals major 2 adds.

The four diagonals are appended rather than interleaved into the geometric order
they would otherwise sit in. Nothing at load time depends on that — a
differently-shaped policy head is rejected on the spec stamp regardless — but it
keeps a hand-read logit index meaning the same thing across every spec since
`ENG_NN_2`.

A diagonal offset is only ever an **attack**: the rules never make diagonal
movement onto an empty square legal, so no index has to distinguish the two
cases. The action space addresses ply *geometry* only; legality always comes
from the rules engine at decode time.

## Design rationale (non-normative)

Nothing below is part of the contract — a network satisfies this spec by
matching the tensors above, whatever its internals. Network internals stay out of
a spec (see [README.md](README.md)); the architecture a given set of weights was
trained at is recorded with the artifact, in the checkpoint's own metadata.

### Whole-board scalar as broadcast plane

Carried forward from `ENG_NN_2` unchanged, along with the reasoning: keeping the
game↔network contract a **single tensor** is worth the one channel the
broadcast plane spends restating one scalar. The deferred alternative —
a scalar side-input pathway merged as a per-channel bias on the stem's output —
is described in full in [ENG_NN_2](eng-nn-2.md#design-rationale-non-normative)
and is not repeated here. It remains a live follow-up, gated on strength
measurement, and adopting it would mint a new spec rather than being an internal
refactor.

Parameterising by board size does not change that trade-off. If anything it
sharpens it slightly: on the 8 × 8 board a broadcast plane restates its scalar 64
times rather than 144, so the redundancy the side-input pathway would remove is
smaller there.

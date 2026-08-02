# Neural Network Input/Output Guide

Name: ENG_NN_3

See [README.md](README.md) for what this specification covers and when a new
one is minted. Supersedes [ENG_NN_2](eng-nn-2.md) for two independent reasons,
either of which alone would have forced a new spec:

1. **Diagonal attack.** Major 2 makes a one-square diagonal attack part of the
   baseline rules. That is new ply *geometry*, which the eight-entry `ENG_NN_2`
   action space cannot address — the case README.md names explicitly.
2. **The board is no longer fixed.** Two rulesets are published in parallel on
   different boards, so the tensor extents are stated in the board's dimensions
   rather than as the literal 12 × 12 of `ENG_NN_2`.

The **plane layout is unchanged from `ENG_NN_2`** — same thirty-four planes, same
indices, same meanings. Only their extent, the action space, and the roster the
army-strength planes normalise by are now parametric.

## Compatible Rulesets

Each entry is a complete (edition, flags) combination. An edition is
`<major>-<minor>:<Ruleset>` and already fixes every flag value, so a row with no
deviating flags names exactly one ruleset (see `doc/ruleset/rules.md` Appendix B):

| Edition        | Deviating flags | Board  | Army                                |
|----------------|-----------------|--------|-------------------------------------|
| `2-0:BATTLE`   | (none)          | 12 × 12 | 3 each of ranks 1–6, 6 Towers, 1 Flag |
| `2-1:SKIRMISH` | (none)          | 8 × 8   | 3 each of ranks 1–4, 3 Towers, 1 Flag |

These are the two **Active** editions (`rules.md` Appendix B). The historical
`2-0:SKIRMISH` is also compatible — it differs from `2-1:SKIRMISH` only in
`TOWER_PLACEMENT`, which restricts where a Tower may be *placed* and so changes
neither a plane nor an action-space entry — but no build implements it, so no
weights can be trained or stamped under it and it is not listed as a target.
Compatibility of that kind is what the rule in [README.md](README.md) describes:
a change that only restricts which plies are legal leaves a spec compatible.

`1-2:PRE-RELEASE` — the only combination `ENG_NN_1` and `ENG_NN_2` listed — is
**not** compatible: it is a major-1 edition, and its action space has no diagonal
entries for this one to correspond to. No weights trained under it survive.

Two rulesets appearing in one list is the ordinary many-to-one relationship
README.md describes: this contract can *serve* either. It does not follow that a
single set of weights can. A network is shaped for exactly one of these
combinations and its parameters are not portable to the other, which is why a
checkpoint's stamp records the single combination it was trained under, and why
the spec name is qualified by board (`ENG_NN_3/standard_144`,
`ENG_NN_3/standard_64`) wherever it identifies an artifact rather than a
contract.

## Board parameters

Everything below is stated in three numbers, fixed for a given ruleset:

| Symbol | Meaning                                | `2-0:BATTLE` | `2-1:SKIRMISH` |
|--------|----------------------------------------|--------------|----------------|
| `R`    | board rows                             | 12           | 8              |
| `C`    | board columns                          | 12           | 8              |
| `N_r`  | how many of rank *r* one army fields   | 3 (r = 1…6)  | 3 (r = 1…4), 0 (r = 5, 6) |

## Input

The input to the engine is a (34,`R`,`C`) tensor, representing
(Feature Planes, Row, Column). Values are floats. At inference the network
takes a batch of positions with a leading batch axis: (N,34,`R`,`C`).

### Perspective and coordinates

The input is always from the perspective of the player to move; the board is
rotated 180° when Black is to move. In tensor coordinates the mover's own back
rank is always row 0, and the mover advances toward increasing row index.

- **White to move:** tensor row = board row − 1 (board rows are 1–`R`, row 1 =
  White's back rank); tensor column = board column (A=0 …).
- **Black to move:** tensor row = `R` − board row; tensor column = `C` − 1 −
  board column.

Every plane — piece presence and the two engineered families alike — is
computed in this same side-to-move frame: "own"/"our" and "enemy"/"their"
always track the mover, never a fixed colour. Rotating a position 180°,
swapping every piece's side label (White↔Black), and flipping the side to
move produces an equivalent position — the two encode to identical tensors.

### Feature Planes

**All thirty-four planes are present under every army**, including planes for
ranks the army does not field. Under `2-1:SKIRMISH` the Foot Soldier and Militia
planes (6, 7, 14, 15, 26, 27, 32, 33) are therefore always zero. Dropping them
would make the two rulesets two different contracts and foreclose any question
about a trunk trained on one board being reused on the other; keeping the layout
fixed costs four dead channels on the smaller army and leaves that open.

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
  (current inactivity count / draw threshold). The threshold is 50 in both
  compatible rulesets (rules.md §5.3).

#### Flag-relative distance

Each square's **signed** offset to a flag, along one axis, normalized by the
board's extent along that axis. Rows and columns are the ones defined above —
0-based, already in the mover's frame:

```
row offset    = (flag's row    − square's row)    / R
column offset = (flag's column − square's column) / C
```

Positive means the flag lies at a higher row/column than the square, negative
the reverse. Values fall in (−1, 1). A flag is always present during play (its
capture ends the game), so these planes are always defined.

- 18: Signed row offset to **our** flag
- 19: Signed column offset to **our** flag
- 20: Signed row offset to **their** flag
- 21: Signed column offset to **their** flag

#### Army strength

For each side and each of the six mobile ranks, the fraction of that rank's
starting roster still on the board:

```
strength = count_remaining_of_rank_r / N_r        when N_r > 0
strength = 0                                      when N_r = 0
```

`N_r` is the resolved value of the ruleset's `ARMY_COMPOSITION` flag
(rules.md §2.2, Appendix A), not a literal number, so a ruleset with a different
roster does not by itself force a new spec: the plane's meaning stays "fraction
of that rank's starting strength remaining," always in `[0, 1]`.

The `N_r = 0` case is new here and is what an army that omits a rank encodes to.
The ratio is undefined, and the constant 0 is chosen over any other value because
it is the true reading of "none of this rank remains" and the only one continuous
with the plane's meaning at every other point — a rank an army never fields is
indistinguishable, to the network, from one wiped out.

Every square in a plane carries the same value (a per-position scalar,
broadcast across the plane — the same pattern as Inactivity Count above). A
value of `1.0` means the rank is intact; `0.0` means it has been wiped out (or
was never fielded). Only the six mobile ranks are represented — Tower and Flag
are excluded (the Flag count is always 1 during play and carries no information;
Tower is out of scope for this spec).

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
keeps a hand-read logit index meaning the same thing across the two specs.

A diagonal offset is only ever an **attack**: the rules never make diagonal
movement onto an empty square legal, so no index has to distinguish the two
cases. The action space addresses ply *geometry* only; legality always comes
from the rules engine at decode time.

## Design rationale (non-normative)

Nothing below is part of the contract — a network satisfies this spec by
matching the tensors above, whatever its internals. Network internals stay out of
a spec (see [README.md](README.md)); the architecture a given set of weights was
trained at is recorded with the artifact, in the checkpoint's own metadata.

### One parametric contract, not one spec per board

The alternative to parameterising by `R` and `C` was a spec per board —
`ENG_NN_3` for 12 × 12, `ENG_NN_4` for 8 × 8, and one more for every layout
after. It was rejected because a spec is a statement about *how a position
becomes a tensor*, and that statement is identical on both boards: same planes,
same perspective rule, same movement index, same normalisation. Two documents
would have differed only in three numbers, and every later change would have had
to be made twice and kept in step by hand.

The cost is that a spec name no longer identifies a set of interchangeable
weights. That cost is paid where it arises rather than in the document: the
engine-spec **stamp** on a checkpoint qualifies the name with the board
(`ENG_NN_3/standard_64`), so a checkpoint trained on one board meeting a run on
the other is refused before its weights are touched.

### Whole-board scalars as broadcast planes

Carried forward from `ENG_NN_2` unchanged, along with the reasoning: keeping the
game↔network contract a **single tensor** is worth the thirteen channels the
broadcast planes spend restating thirteen scalars. The deferred alternative —
a scalar side-input pathway merged as a per-channel bias on the stem's output —
is described in full in [ENG_NN_2](eng-nn-2.md#design-rationale-non-normative)
and is not repeated here. It remains a live follow-up, gated on strength
measurement, and adopting it would mint a new spec rather than being an internal
refactor.

Parameterising by board size does not change that trade-off. If anything it
sharpens it slightly: on the 8 × 8 board a broadcast plane restates its scalar 64
times rather than 144, so the redundancy the side-input pathway would remove is
smaller there.

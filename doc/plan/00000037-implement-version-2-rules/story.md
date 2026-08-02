# Story 37: Implement Version 2 Rules

## Summary

Implement in code the rules that [story 34](../00000034-rule-change-allow-diagonal-attack-and-board-sizing/story.md)
published as documents, and add one rule change of this story's own.

1. **Board layout and army composition become run-time configuration** rather
   than module constants. `BOARD_LAYOUT` and `ARMY_COMPOSITION` stop being
   documentation-only flags and start selecting real geometry and a real roster.
2. **Diagonal attack** enters move generation.
3. **A build implements every Active edition**, and the configuration a run plays
   is selected at launch and threaded through to every artifact it stamps.
4. **A new flag, `TOWER_PLACEMENT`**, forbids placing a Tower where it blocks a
   lane through the lakes — and a new edition, **`2-1:SKIRMISH`**, turns it on.

Items 1–3 close a gap story 34 deliberately opened. Item 4 is new, and is the
only rules change this story makes on its own authority.

## Context: the documents are ahead of the code

Story 34 changed documents only, on the constraint that its branch would not
reach `main` until the rules it published were implemented. That constraint was
not held — the branch merged at #36 — so `main` currently describes a game it
does not implement:

- `record.py` stamps `ACTIVE_EDITION = "1-2:PRE-RELEASE"`, an edition Appendix B
  marks **retired**. Every record and checkpoint written today is tagged with a
  ruleset name that is no longer offered.
- `board.py` bakes a 12 × 12 grid, the lake pattern, and the home-zone rows into
  module constants.
- `pieces.py` carries one `ARMY_ROSTER`, with each piece's count fixed on the
  `PieceType` enum member itself.
- `moves.py` generates orthogonal plies only.

This story closes all four. Nothing about the published documents is reopened:
the flag identifiers, value labels, and edition ids in `rules.md` are already
permanent, and this story implements them as written rather than renegotiating
them.

## Motivation for the new rule

Playing with the Skirmish board surfaced a placement exploit that the Battle
board does not have, and that only exists because Skirmish has no neutral buffer
row.

**The geometry.** The lake pattern `O L L O O L L O` puts lakes on columns B/C
and F/G across rows 4–5, leaving four passable columns: edge lanes at **A** and
**H**, and the double lane **D–E**. Row 3 is White's front home row and sits
directly against lake row 4, so each lane square's only orthogonal entry from
White's half is the row-3 square above it — B4 is a lake, so A4 can be reached
only from A3 or A5.

**The exploit.** A Tower placed on A3, D3, E3, or H3 therefore seals that lane
from White's side. Towers never move and can only be removed by an attack that
destroys the attacker as well, so the blockade is permanent unless it is paid
for in pieces.

**What it costs to break.** Towers cannot be attacked diagonally, so an A3 Tower
can be attacked only from A4 — a Black piece has to walk into the very lane it
is trying to open and sacrifice itself there. Three blocked lanes cost Black
three of its twelve movable pieces, a quarter of the mobile army, to restore a
board it should have had for free.

**The ceiling is three of four**, and it is the existing Tower spacing rule that
sets it: D3 and E3 are orthogonally adjacent, so no army can seal all four lanes
regardless of how many Towers it has. The remaining open file is a chokepoint
rather than a wall, and if both sides blockade, play funnels through it. Whether
one open file is *enough* is a judgment this story does not have to make in
advance — that is what publishing it behind a flag is for.

**Why a flag rather than a rewrite.** `2-0:SKIRMISH` is published and its meaning
is fixed. New behavior lands as a flag with a preserving default outside a major
bump, and there is no major bump here — the notation is untouched. So the
restriction is a flag, and turning it on for Skirmish publishes a new edition.

**Why not a board change instead.** The root cause is Skirmish's missing buffer
row, so a `BOARD_LAYOUT` value with one is the obvious alternative. It does not
fit: 3 home / 1 buffer / 2 lake / 1 buffer / 3 home is ten rows, not eight, and
compressing to two home rows gives 16 squares for 16 pieces — a home zone with no
placement choice at all, which removes phase 1 from the game. The Tower rule is
the cheaper lever.

## Specification

### 1. Configuration replaces constants

The board and the army stop being module-level facts and become values resolved
from a configuration.

- **`BOARD_LAYOUT`** resolves to grid dimensions, home-zone row counts, lake rows,
  and the lake column pattern. `board.py`'s `BOARD_COLUMNS`, `BOARD_ROWS`,
  `LAKE_PATTERN`, `LAKE_ROWS`, `WHITE_HOME_ROWS`, `BLACK_HOME_ROWS`,
  `LAKE_SQUARES`, and the two home-square sets all derive from it.
- **`ARMY_COMPOSITION`** resolves to a roster. `PieceType`'s `army_count`
  attribute cannot survive as-is: a count that lives on the enum member is a
  single global army by construction. Rank, symbol, name, and mobility stay on
  the enum; the count moves out.
- **Coordinates become size-parametric.** `_COLUMN_LETTERS` and `parse_square`'s
  range check read the configured width rather than assuming A–L / 1–12.

`Square` itself is unchanged — a column index and a row number are layout
independent, and only the bounds that validate them move.

### 2. Diagonal attack

Move generation gains diagonal plies, subject to the three restrictions
`rules.md` states:

- **One square only**, and only **onto an enemy-occupied square** — never onto an
  empty one. The unencumbered two-square bonus never extends a diagonal.
- **Movable targets only.** The target must be a numbered piece; Towers and the
  Flag are not legal diagonal targets. This is a generation-time restriction, not
  a combat-resolution one — `combat.py` needs no change, since a diagonal attack
  that is generated resolves by exactly the rules an orthogonal one does.
- **A lake corner does not block.** A diagonal has no intermediate square to
  clear, so the *skirt* case (attacking past a lake corner, e.g. A6 → B5 on
  Battle) is legal and needs no special handling. The *squeeze* case — both
  flanking squares lakes — is unreachable on both published layouts and stays
  unimplemented, per the decision recorded in `technical-notes.md`.

Encumbrance already tests all eight surrounding squares, so the existing
definition carries over untouched.

### 3. Two Active editions, selected at run time

`record.py`'s `ACTIVE_EDITION` — today a single string — becomes a **set** of
Active edition ids, and the configuration a run plays becomes a parameter rather
than a build constant.

- `EDITIONS` gains rows for every published edition, Active and Historical.
- `Edition` changes shape. It currently carries a `distribution` mapping as a
  field of its own; since major 2, distribution is the resolved value of
  `ARMY_COMPOSITION`, so an edition holds flag values and the distribution is
  derived by resolving them. This is the change story 34 named as its sharpest
  code implication.
- `RULE_FLAGS` gains `BOARD_LAYOUT`, `ARMY_COMPOSITION`, and `TOWER_PLACEMENT`.
- **The checkpoint stamp is compared against the run's configuration**, not
  against a build-level constant. The historical-edition rejection survives with
  its reasoning corrected: a historical edition is rejected because it is not
  Active, not because a build holds only one edition.
- The **per-edition distribution assertion** in `tests/test_record.py` replaces
  the single-roster one. A check covering only one Active edition leaves the
  other unguarded.

**Where the configuration has to reach:** the game and batch runners, the
training runner, match setup, the text UI, placement generation and parsing, and
the neural-network tensor layout. `ENGINE_SPEC_NAME` must distinguish the two
layouts, since the input tensor's spatial extent differs — the one case where the
spec stamp and the ruleset stamp genuinely overlap, which `technical-notes.md`
already records as redundancy rather than a problem.

**Placement files need no migration.** A placement file carries no ruleset
marker, but its shape identifies it: 4 rows × 12 characters is a Battle file,
3 × 8 a Skirmish file. Parsing validates against the configuration in play, and
the two committed files stay valid for `2-0:BATTLE`.

### 4. `TOWER_PLACEMENT = spacing_only | spacing_and_lanes`

Default: **`spacing_only`** — the rule that predates the flag.

| Value | Restrictions on Tower placement |
|---|---|
| `spacing_only` | No two Towers within one square of each other (orthogonally or diagonally). |
| `spacing_and_lanes` | The above, **plus**: no Tower on a square orthogonally adjacent to a non-lake square in a lake row. |

**The definition is geometric, not enumerated.** The forbidden squares are
derived from the layout rather than listed per `BOARD_LAYOUT` value, so a future
layout gets the rule without anyone hand-computing a square list for it.

**On `standard_64`** this closes **A3, D3, E3, H3** and **A6, D6, E6, H6** to
Towers; B3, C3, F3, and G3 stay open, as does every square in rows 1–2 and 7–8.
**On `standard_144`** it closes nothing, because the neutral buffer row means no
home square touches a lake row — so the flag is a genuine no-op on Battle.

**The rulebook carries the rule by example.** `rules.md` is written for players,
so the precise formulation above belongs in `technical-notes.md`; §3 states the
restriction plainly ("a Tower may not be placed directly in front of a gap in the
lakes") and shows which Skirmish squares that closes. `lane` is already used in
§2.1 prose and should gain a glossary entry.

**A rejected alternative, recorded so it is not re-proposed:** defining the
restriction by connectivity — a Tower may not disconnect the lanes — reads better
as a statement of intent but permits D3, since E stays open. The blockade is
harmful well before it is total.

**Feasibility.** Three Towers into 20 candidate squares, with the spacing rule
also in force, never stalls: the first Tower removes at most its nine-square
closed neighbourhood, leaving at least 11, and the second leaves at least 2.
`placement.py`'s random generator carries a comment proving exactly this for six
Towers in 48 squares; that argument becomes per-layout and must be re-derived
rather than deleted.

### 5. Editions published

**Active**

| Edition | `BOARD_LAYOUT` | `ARMY_COMPOSITION` | `TOWER_PLACEMENT` |
|---|---|---|---|
| `2-0:BATTLE` | `standard_144` | `standard_battle` | `spacing_only` |
| `2-1:SKIRMISH` | `standard_64` | `standard_skirmish` | `spacing_and_lanes` |

**Historical**

| Edition | Status |
|---|---|
| `2-0:SKIRMISH` | superseded |
| `1-2:PRE-RELEASE` | retired |

`2-0:BATTLE` **does not move.** `TOWER_PLACEMENT` is a no-op on `standard_144`,
so turning it on there would spend an edition for no behavioral change.
Publishing a new edition of one ruleset and not the other is the deliberate
decision `doc/ruleset/CLAUDE.md` asks for, and this is its justification.

**`2-0:BATTLE`'s Appendix B row should list `TOWER_PLACEMENT` explicitly**, even
though the edition predates the flag and would resolve to the same value by the
"published before the flag existed" fallback. Writing out a flag at the value it
already resolves to does not change what the edition means — `technical-notes.md`
canonicalization treats the two as identical, and the rendered stamp omits the
flag either way — and an Active row that spells out every flag is easier to read
than one the reader has to resolve.

`2-0:SKIRMISH` becomes the first **superseded** edition; `PRE-RELEASE` is the
only historical row today and it is *retired*, a different reason. No checkpoint
or record can be stamped with `2-0:SKIRMISH`, since no build ever implemented it,
so the supersession has no artifacts to strand. It stays in `EDITIONS` regardless,
because the table's job is to keep every published id nameable.

### 6. Documents to change

| Document | Change |
|---|---|
| `doc/ruleset/proposed-variants.md` | `TOWER_PLACEMENT` entered while the branch is open, removed at graduation |
| `doc/ruleset/rules.md` | §3 gains the Tower lane restriction with Skirmish examples; glossary gains *Lane*; Appendix A gains `TOWER_PLACEMENT`; Appendix B publishes `2-1:SKIRMISH` and moves `2-0:SKIRMISH` to Historical |
| `doc/ruleset/technical-notes.md` | the precise geometric definition; the Active-edition list; the connectivity alternative and why it was rejected |
| `doc/ruleset/changelog.md` | one entry for `2-1:SKIRMISH`, newest first, recording story 37 and the date |
| `doc/ruleset/CLAUDE.md` | the two Active editions are now `2-0:BATTLE` and `2-1:SKIRMISH` |
| `README.md` | checked, and updated if the configuration-selection change alters anything it describes |

The **graduation rule is honored as written**: `TOWER_PLACEMENT` sits in
`proposed-variants.md` while the branch is open and moves to Appendix A when the
branch merges, which is also when the engine first implements it.

## Out of scope

- **Tuning the inactivity counter per edition.** Still 50 plies on both boards.
  Story 34 left it alone pending watched games, and this story adds a third
  confound — the lane restriction changes how quickly contact happens on Skirmish
  — rather than a reason to move it.
- **Any third `BOARD_LAYOUT` or `ARMY_COMPOSITION` value**, including a
  buffer-row Skirmish board.
- **Network architecture and cross-board transfer.** Whether a Skirmish-trained
  network can be reused on Battle stays unexamined; nothing here depends on it.
- **A record reader, parser, or replay-validation path**, still absent by design.
- **Retrofitting existing training runs or checkpoints.** Artifacts stamped
  `1-2:PRE-RELEASE` become unloadable by the rule that a historical edition is
  rejected. That is the intended behavior, not a migration to be written.

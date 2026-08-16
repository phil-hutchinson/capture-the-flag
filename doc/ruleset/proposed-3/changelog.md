# Capture the Flag — Ruleset Changelog (Major 3, Proposed)

> **Draft.** This is the entry major 3 *would* publish, written in the form
> consumers track, so that a front-end can be planned against it before anything
> is committed to. It is not part of [`../changelog.md`](../changelog.md) and
> nothing has been published. See [`README.md`](README.md).

---

## Edition 3-0:PRE-RELEASE — Story 00000046 — 2026-08-15 — **proposed**

**A new major. Nothing about Battle, Clash or Skirmish changes.** `2-0:BATTLE`,
`2-0:CLASH` and `2-1:SKIRMISH` stay exactly as they are, at the same majors and
minors, with the same boards, armies and rules text. A consumer that does not
want to offer major 3 need do nothing at all.

A consumer that *does* want to offer it should read this entry as a list of
breaking changes, because that is what it is. Major 3 is not a variation on major
2 — it is a different rules text, and several of the differences are of a kind
that will produce a wrong board rather than an error.

### Read this part first — two silent breakages

- **Rank numbering is reversed.** At major 2, rank `1` is the **strongest** piece.
  At major 3, rank `5` is the strongest and rank `1` the weakest. The digits in a
  position block mean the opposite of what they meant. A renderer that maps a
  digit to artwork or to a strength value **must branch on the record's major**.
- **Piece names are reused at different ranks.** Names are explicitly flavour at
  major 3 and carry no permanence guarantee at all, and **every major 2 name that
  survives into major 3 carries a different digit** — see the table below.

| Name | Rank in `2-0:BATTLE` | Rank in `3-0:PRE-RELEASE` |
|---|---|---|
| Master-of-Arms | 1 (strongest) | 5 (strongest) |
| Champion | 2 | 4 |
| Knight | 3 | *not in this army* |
| Halberdier | 4 | *not in this army* |
| Foot Soldier | 5 | 3 |
| Militia | 6 (weakest) | 2 |
| Peasant | *did not exist* | 1 (weakest) |

The two failure modes are different, and both are silent. A consumer that maps a
**name to artwork** survives the first two rows — `Master-of-Arms` and `Champion`
keep their place in the strength order — and is wrong on `Foot Soldier` and
`Militia`, which move. A consumer that maps a **name to a rank digit**, or a
digit back to a name, is wrong on all four. **Key off `(major, rank digit)`.
Never off a name, and never off a digit alone.**

### Notation — one new mark, and one form withdrawn

- **New mark `=N`.** A square may now carry `=N` immediately after it, meaning the
  piece that began the ply on that square **survived and is now rank `N`**. It sits
  alongside the existing `x`, follows the same convention — both marks describe the
  piece that *started* on that square — and appears because of rank reduction
  (below).

  ```
  A2-A4      a ply with no combat
  A2=3-A4x   attacker won; defender removed; attacker now rank 3
  A2x-A4=2   attacker lost; defender survived and is now rank 2
  A2x-A4x    both removed
  A2-A4x     Flag captured (capturing the Flag is not combat)
  ```

- **In any combat ply, each of the two squares carries exactly one mark**, `x` or
  `=N` — never both, never neither. This is a usable parser assertion.
- **`A2-A4x` always means a Flag capture**, since no real combat leaves a source
  square unmarked. The terminal ply is detectable from the tape alone.
- **The plain form is no longer valid in a record.** `A2A4` cannot carry `=N`, so a
  plain-form major 3 record cannot be replayed correctly. Records must use the
  extended form. The plain form remains available for *entering* a move in a text
  interface.
- **Replay still requires no rules knowledge.** The `=N` mark exists precisely so
  that the view-only replay guarantee survives rank reduction. A reader steps a
  major 3 record exactly as it steps a major 2 one, applying the marks it is given.

### Position block

- The alphabet is `1`–`5`, `F`, `---`. There is **no `T`** and — more useful for a
  renderer — **never any `XXX`**, because there are no lakes. This holds for major
  3 records only; do not generalise it.
- Dimensions and layout are still recoverable by reading the block, as at major 2.

### The game

- **8 × 8 board, entirely open.** No lakes, no lanes, no impassable squares, no
  buffer rows. Rows 1–2 and 7–8 are the home areas; rows 3–6 start empty.
- **16-piece army: three each of ranks 1–5, plus one Flag.** No Towers — the piece
  type does not exist at major 3, and neither does the tower-placement restriction.
- **No placement phase.** The game is single-phase and fully visible from the first
  ply. Both armies fill their home rows completely, so there is no choice of which
  squares to occupy.
- **The starting position is generated**, from 1,345,344,000 possibilities, with
  the Flag on the back row. Black's army is derived from White's by a reflection or
  a half-turn, chosen by a stated rule about where the Flag sits relative to the
  army's strength. Both branches produce an even position. Full specification in
  [`start-position.md`](start-position.md).
- **An optional `[StartPosition "…"]` header tag** may carry the position's ID. It
  is redundant for replay and a reader must not require it. The ID is a
  **16-character hexadecimal code** spelling out White's two home rows, one digit
  per square (`1`–`5` for a rank, `F` for the Flag, `0` for an empty square), so an
  engine and a front-end can agree on a position without exchanging a board.
  **Handle it as a string.** Sixteen hex digits is 64 bits, past the 2⁵³ limit
  within which a JavaScript `Number` holds integers exactly, so parsing an ID into
  a `Number` corrupts it silently.

### Movement and combat

- **Rank reduction.** Any piece that **survives combat** is immediately reduced by
  one rank, attacker and defender alike. A rank 5 that wins becomes a rank 4 in
  every respect. Draws reduce nothing, since they leave no survivor, and no piece
  can be reduced below rank 1. **A piece's rank is mutable during a game** — a
  consumer must hold it as state rather than as a fixed property of a token.
- **Encumbrance is direction-relative.** A piece may move two squares if no enemy
  stands on the five squares ahead of or beside it *in the direction of travel*;
  the three squares behind it do not encumber. At major 2, any of the eight
  surrounding squares encumbered, in every direction.
- **Diagonal attacks apply to every piece, the Flag included.** Major 2's
  restriction to movable targets is gone — so, unlike major 2, **the Flag can be
  captured diagonally**.
- **Diagonal attacks require an open path.** At least one of the two squares
  orthogonally adjacent to both attacker and target must be empty. This is what
  gives a Flag its defence: pieces packed orthogonally around it close the
  diagonals into it.
- **White's first ply of the game is limited to one square.** Every other ply
  follows the ordinary rules.
- The formation bonus is unchanged in substance: a friendly piece of equal rank
  within one square lets a piece draw against a piece one rank stronger. Note that
  a reduced piece may gain or lose a formation, so formations must be recomputed
  after each combat.

### Ending a game

- **Attrition replaces "no legal move."** A player with no numbered pieces loses
  immediately, checked after **every** ply rather than at the start of their turn.
  The Flag does not count toward this.
- **Mutual attrition is a draw.** If one ply leaves both players with no numbered
  pieces, neither wins.
- **Resignation is a new way to end a game.** A player may concede at any point and
  the opponent wins immediately. Unlike a draw offer it needs no acceptance and
  cannot be declined. Note that it is a **decisive result that cannot be derived
  from the position** — a reader replaying a resigned game stops at a position that
  is not terminal, which is correct and not a malformed record. `Draw by Agreement`
  has always behaved this way; resignation extends it to wins.
- `ResultReason` uses `Attrition` and `Mutual Attrition` where major 2 used
  `No Legal Move`, and adds `Resignation`. `Result` values are unchanged.
- **The inactivity limit drops from 50 plies to 40.**
- Flag capture and draw by agreement are unchanged.

### Editions and settings

- **Major 3 publishes no rule settings.** `3-0:PRE-RELEASE` is defined entirely by
  its rules text, and its ruleset tag always renders as a bare edition id with no
  deviations. Major 2's `BOARD_LAYOUT`, `ARMY_COMPOSITION` and `TOWER_PLACEMENT` do
  not exist here and are not referenced by anything at this major.
- `PRE-RELEASE` is a **working name**. It reuses a name already retired at major 1;
  see [`technical-notes.md`](technical-notes.md).

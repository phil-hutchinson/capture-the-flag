# Capture the Flag — Ruleset Changelog

Revision history for [`rules.md`](rules.md), newest first. Each entry records the
**edition**, the **story** that introduced the change, and the **date**, followed
by a summary of what changed.

**Any change to `rules.md` must add an entry here** (see [`CLAUDE.md`](CLAUDE.md)).
External consumers — in particular a separate front-end player application — track
this changelog to know when and how to update.

Entries before 2026-07-26 predate editions and are labelled with the ruleset
*version* they carried at the time (`1.2`, dotted). Those versions map to
editions of the same number under `PRE-RELEASE`: version `1.2` is edition
`1-2:PRE-RELEASE`.

---

## Edition 3-0:PRE-RELEASE — Story 00000049 — 2026-09-16

**A new major, and it replaces the old ones.** `2-0:BATTLE`, `2-0:CLASH` and
`2-1:SKIRMISH` move to the Historical table and are retired: no code path can set
any of them up any longer, though their rows remain so that a game record or
checkpoint stamped with one still names something real. `3-0:PRE-RELEASE` is the
only Active edition.

This entry is a list of breaking changes for anyone consuming major 3, and also a
note that offering major 2 is no longer an option: this repository plays
`PRE-RELEASE` and nothing else. Major 3 is not a variation on major 2 — it is a
different rules text, and several of the differences are of a kind that will
produce a wrong board rather than an error.

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
- `PRE-RELEASE` is retained deliberately, not merely as a working name. It reuses
  a name already retired at major 1 — see [`technical-notes.md`](technical-notes.md)
  — because the name says what is true: the game is not finished.

---

## Edition 2-0:CLASH — Story 00000043 — 2026-08-08

**A third ruleset is published. Nothing about Battle or Skirmish changes.**
`2-0:BATTLE` and `2-1:SKIRMISH` stay Active at the same minors, with the same
board, army and Tower rule. A consumer that does not want to offer Clash need do
nothing.

- **Clash is a 10 × 10 board with a 20-piece army.** 3 home rows / 1 buffer / 2
  lake / 1 buffer / 3 home, a 30-square home zone, and 3 each of ranks 1–5 plus 4
  Towers and 1 Flag. Militia (rank 6) does not appear. It sits between Skirmish
  and Battle in size; **Skirmish is still the recommended starting point** for a
  new player. See [Section 2.1](rules.md#21-the-board) and
  [Section 2.2](rules.md#22-the-pieces).
- **Its lakes are not symmetric, and this is the first board where that is
  true.** The lake pattern is `L O O L O O L L L O`, giving lakes one column wide
  at A, one column wide at D, and three columns wide across G–I — so the lanes
  are B–C, E–F and J. **Column A is a lake, not a lane.** Both other boards are
  open at each far edge with wider lanes through the interior; Clash is not. A
  renderer or editor that assumes a mirror-symmetric lake row, or a lane at each
  edge, will draw this board wrong.
- **The board is still symmetric between the two players**, which is what
  placement fairness depends on: both home zones sit the same distance from the
  same lakes, with a buffer row on each side. Column letters name fixed physical
  positions and do not flip per player
  ([Section 4.4](rules.md#44-recording-a-move)), so the left-right asymmetry
  applies identically to both.
- **The notation is unaffected.** A 10 × 10 board has been expressible since the
  major-2 notation became size-parametric: columns A–J, rows 1–10, and both the
  dimensions and the lake layout recoverable from a record's position block. A
  consumer that reads dimensions from the block, as major 2 requires, reads Clash
  records with no change at all.
- **Two published variants gain a third value each**, in Appendix A:
  `BOARD_LAYOUT` gains `asymmetric_100` and `ARMY_COMPOSITION` gains
  `standard_clash`. Both defaults are unchanged, so no existing edition and no
  existing record is affected. This is the first time a value has been added to
  an already-published variant rather than a new variant introduced.
- **`TOWER_PLACEMENT` is `spacing_only` on Clash**, and `spacing_and_lanes` would
  close nothing on it: the restriction closes a square only where a home zone
  sits directly against the lake rows, and Clash has a buffer row exactly as
  Battle does. [Section 3](rules.md#3-setup--phase-1-placement) now states that
  restriction as a property of the board rather than as a Skirmish rule; no
  square that was open or closed before has changed.
- **There are now three Active editions, and their minors are unrelated.** Clash
  is at minor 0 because `2-0:CLASH` is its first edition — not because it agrees
  with `2-0:BATTLE` about anything. Do not read a relationship into two editions
  sharing a minor; they share a major, and that is the only number that means the
  same thing across rulesets.

---

## Edition 2-1:SKIRMISH — Story 00000037 — 2026-08-02

**Skirmish only.** `2-0:BATTLE` is unchanged and stays Active; `2-0:SKIRMISH`
moves to the Historical table, superseded. Consumers that only read Battle
records need do nothing.

- **A new placement restriction in Skirmish: no tower directly in front of a
  lane.** The four squares in each Skirmish home zone that sit immediately in
  front of an open column through the lake rows — **A3, D3, E3, H3** and **A6,
  D6, E6, H6** — are closed to towers. Every other home square stays open,
  including B3, C3, F3 and G3, which sit behind the lakes rather than behind a
  lane. The tower spacing rule is unchanged and applies as well. See
  [Section 3](rules.md#3-setup--phase-1-placement).
- **The restriction is a published variant, `TOWER_PLACEMENT`,** with values
  `spacing_only` (the default, and what every earlier edition played) and
  `spacing_and_lanes`. It joins Appendix A. Because the closed set is defined
  geometrically — a home square orthogonally adjacent to a non-lake square in a
  lake row — `spacing_and_lanes` closes **nothing at all** on the Battle board,
  whose home zones are separated from the lakes by a buffer row.
- **`2-0:BATTLE` now spells out `TOWER_PLACEMENT=spacing_only` in Appendix B.**
  Nothing about that edition changed: an edition has always fixed a value for
  every variant, and this one was at its default before it had a name.
- **The glossary gains _lane_** — a gap the lakes leave open through the lake
  rows. Battle has four, Skirmish three. This names something the rules already
  described in [Section 2.1](rules.md#21-the-board); no rule changed with it.
- **Nothing about play in progress changed.** Movement, combat, and the ending
  conditions are untouched, and **the notation is unaffected** — a placement
  restriction produces no new kind of ply. A record stamped `2-1:SKIRMISH` reads
  exactly as one stamped `2-0:SKIRMISH` does.
- **The minor numbers of the two rulesets now differ**, which is the first time
  that has happened: Skirmish is at `2-1` and Battle at `2-0`. They still share
  major 2 because they share this rules text. A consumer must not assume the two
  Active editions carry the same minor.

---

## Editions 2-0:BATTLE and 2-0:SKIRMISH — Story 00000034 — 2026-07-30

**A major bump, and a breaking one.** Consumers must update. Two editions are
published at once and `PRE-RELEASE` is retired.

- **The notation is now size-parametric.** A board is a rectangular grid whose
  dimensions are read from the record's position block, rather than a fixed
  12 × 12 with the coordinate frame baked in. Lake layout is likewise recoverable
  from the block's `XXX` cells. Columns are lettered from A and rows numbered
  from 1 as before, supporting up to 26 columns. **This is the breaking change**
  — any consumer that assumed a 12 × 12 grid must now read the dimensions.
  The **home-zone row count is not** recoverable from a position block; it comes
  from the configuration's `BOARD_LAYOUT` value. A review-only viewer does not
  need it.
- **Diagonal attack is now baseline.** A piece may attack a movable enemy piece
  one square diagonally. Diagonal movement without an attack is not allowed, and
  **Towers and the Flag may not be attacked diagonally** — so the Flag can only
  ever be captured from an orthogonally adjacent square. Both sacrifice types are
  permitted diagonally. Rank, equal rank, and the formation bonus apply unchanged;
  the unencumbered bonus never interacts, since a piece with an enemy on its
  diagonal is encumbered by definition. **The notation is unaffected** — a
  diagonal attack is a source and a destination like any other ply.
  A **lake corner does not block a diagonal attack**: only the attacked square
  itself must not be a lake. (The converse case — a diagonal squeezing between
  *two* lakes — cannot arise on either published board and is not addressed in
  the rules; [`technical-notes.md`](technical-notes.md) records the decision for
  any future layout that makes it reachable.)
- **Two rulesets are published and maintained in parallel.** `2-0:BATTLE` is the
  12 × 12 board and 25-piece army carried forward from `1-2:PRE-RELEASE`;
  `2-0:SKIRMISH` is a new 8 × 8 board with a 16-piece army (3 each of ranks 1–4,
  3 Towers, 1 Flag), 3 home rows and 2 lake rows with no neutral buffer. Skirmish
  is the recommended ruleset for a new player.
- **`PRE-RELEASE` is retired.** `1-2:PRE-RELEASE` moves to Appendix B's
  Historical table marked *retired*. Being a major-1 edition it was played without
  diagonal attacks, under rules text `rules.md` no longer carries.
- **The first two variants are published** in Appendix A:
  `BOARD_LAYOUT = standard_144 | standard_64` (default `standard_144`) and
  `ARMY_COMPOSITION = standard_battle | standard_skirmish` (default
  `standard_battle`). A `BOARD_LAYOUT` value names a *complete* layout —
  dimensions, home-zone depth, and lakes. Not every combination is playable: an
  army must fit its home zone.
- **An edition is now a major baseline plus a complete set of variant values.**
  Piece distribution is no longer a separate axis of an edition; it is the
  `ARMY_COMPOSITION` value. The major names the rules text, so editions at
  different majors are not comparable by variant values alone. Minor numbers are
  namespaced per ruleset; majors are global.
- **Board size no longer forces a major bump.** That was the point of spending
  this one. Future layouts cost a new `BOARD_LAYOUT` value, not a new major. See
  [`technical-notes.md`](technical-notes.md) for the revised major-bump list.

---

## Edition 1-2:PRE-RELEASE — Story 00000032 — 2026-07-26

**No rule changed.** This entry records a change to the *conventions* around the
rules, which consumers of this changelog need to know about even though play is
unaffected. The edition stays at minor 2, carrying the former version 1.2
forward: there is no semantic change for a new minor to mark.

- **Rulesets, editions, and flags replace the single version number.** A
  *ruleset* is a mutable name (`PRE-RELEASE`); an *edition* — `1-2:PRE-RELEASE`,
  dashed — is an immutable pairing of that name with a piece distribution and
  explicit variant settings; a *rule flag* (called a *variant* in `rules.md`) is
  an enum-valued rule setting whose default always preserves the behavior that
  predated it.
- **Two new appendices in `rules.md`.** Appendix A (Variants) is append-only and
  currently empty; Appendix B (Rulesets) carries the Active and Historical
  edition tables. Sections 1–6 are unchanged; Section 7's glossary gains
  *Ruleset*, *Edition*, and *Variant*.
- **`doc/ruleset/proposed-variants.md` is new** — a mutable sandbox that carries
  no promises. A variant graduates from it to Appendix A only when its
  implementing branch merges.
- **The `Ruleset` record tag changes form**, from `1.2:PRE-RELEASE` to
  `1-2:PRE-RELEASE` plus any deviating flags. Dashes, and the full edition id
  rather than a bare ruleset name.
- **"Latest version only" is retired.** Replaced by two guarantees: view-only
  replay for all records by notation-schema stability alone, and validated replay
  for published editions. See [`technical-notes.md`](technical-notes.md), which
  also now states exactly what forces a major (notation) bump.

---

## Version 1.2 — Story 00000018 — 2026-07-14

This represents a major change to the rules. Note that this would involve a 
major version update with many breaking changes, but this is a pre-release
update so it will remain at version level 1.

Updates include:

- **Piece restructuring.** Ranks 7-9 and the assassin were removed. Some
  of the existing ranks were also renamed, and names moved to different ranks.
  See [the story](../00000018-revamp-rules/story.md) for all details.
- **Special ability removal.** Special abilities for ranked pieces have been
  removed (no more Knight charges, Skirmisher rushes, Archer support, or Sapper
  tower destruction).
- **Formation ability.** The formation ability, affecting ranked pieces in
  general, has been added. A piece with an equal-ranked ally adjacent to it
  draws against a piece one rank higher, rather than losing.
- **Unencumbered bonus.** The unencumbered bonus, affecting movement, has
  been added to all movable pieces. Pieces may move two squares orthogonally
  when unencumbered (no enemy pieces in the 8 surrounding squares).
- **Tower placement.** Towers may no longer be placed next to each other,
  making it impossible for them to surround the flag. Mechanics related to
  flag breachability (including the victory method) have also been removed.
- **Tower combat.** Any piece may now attack a tower, resulting in a draw
  (both the tower and attacking piece are removed).
- **Inactivity game ends.** There is now only a single game-ending condition
  for inactivity—a draw triggered by 50 consecutive non-attacking plies. The
  previous dual-counter system (per-player inactivity loss + shared progress
  counter) has been consolidated into this single shared counter.
- **Colour standard.** The overview now states explicitly that the two sides are
  designated White and Black, the standard used for pieces and coordinates.

## Version 1.1 — Story 00000004 — 2026-07-09

Added the coordinate system and move notation to the player-facing rules, now
that the reference engine's move generation and combat resolution are stable
enough to promote them out of the working notation draft
(`.local/game-notation-suggestion.md`):

- **New Section 4.4, "Recording a move".** Squares are named by column letter
  (A–L, left to right) and row number (1–12; row 1 is White's back rank, row
  12 is Black's back rank). A move is written as source-then-destination with
  no separator (e.g. `A4A5`) — sufficient on its own to record and replay a
  game, since any attack's result follows automatically from the position and
  the rules. A result-marking form (source-dash-destination, with `x` marking
  a piece that did not survive) is documented as reserved for future score
  sheets.
- The full game-record file format (the position block, header tags, and move
  sequence) is documented separately in `technical-notes.md`, since it is a
  developer/file-interchange concern rather than player-facing.

Also clarified two previously-unaddressed Archer support edge cases in
Section 4.3 (behavioural, resolving ambiguities the reference engine hit rather
than reworking the ability):

- **The Flag is never supported.** Capturing the Flag is always an immediate
  win for the attacker (Section 6.1); an Archer behind the Flag no longer
  converts the capture into a mutual loss, so the attacker always moves onto
  the Flag and wins.
- **The Assassin is not immune to Archer support.** An Assassin attacking a
  supported piece is a mutual loss (its guaranteed win removes the target; the
  Archer removes the Assassin) — except against a supported Flag, where the
  exemption above makes it an outright win.

## Version 1.0 — Story 00000001 — 2026-07-08

Initial official ruleset, consolidated from the offline design notes into a single
source of truth. Notable decisions relative to those notes:

- **Piece counts** set to: Lord Marshal 1, Champion 2, Knight 4, Infantry 4,
  Halberdier 6, Militia 6, Skirmisher 6, Archer 3, Sapper 8, Assassin 1, Tower 6,
  Flag 1 — 48 pieces per side.
- **Placement** has no restrictions beyond filling the home zone (any piece,
  including the Flag and Towers, may go on any home-zone square).
- **Towers are no longer immune to non-Sappers.** Any piece may attack a Tower,
  but only a Sapper destroys it; a non-Sapper that attacks a Tower is removed and
  the Tower stands (a complete sacrifice).
- **Anti-stalling reworked into two clocks.** An **individual inactivity clock**
  (50 of a player's own plies with no attack → that player loses; reset by any
  attack you make, or any sacrificial attack by your opponent) supplies pressure to
  resolve, and a **collective progress clock** (80 plies with no capture → draw)
  provides the intended out for standoffs. A complete sacrifice resets both
  players' inactivity clocks but not the progress clock.
- **Draw by agreement** added; the **Fair Play Rule** (no unproductive shuffling,
  intentionally informal) added.
- The structural "no-hope" win was renamed **Unbreachable Flag**; its substance
  (all enemy Sappers unavailable + own Flag fully Tower-enclosed → immediate win,
  with the mutual last-Sapper trade resolving to a draw) is unchanged.

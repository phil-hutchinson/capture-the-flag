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

# Capture the Flag — Ruleset Changelog

Revision history for [`rules.md`](rules.md), newest first. Each entry records the
ruleset **version**, the **story** that introduced the change, and the **date**,
followed by a summary of what changed.

**Any change to `rules.md` must add an entry here** (see [`CLAUDE.md`](CLAUDE.md)).
External consumers — in particular a separate front-end player application — track
this changelog to know when and how to update.

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

# Capture the Flag — Ruleset Changelog

Revision history for [`rules.md`](rules.md), newest first. Each entry records the
ruleset **version**, the **story** that introduced the change, and the **date**,
followed by a summary of what changed.

**Any change to `rules.md` must add an entry here** (see [`CLAUDE.md`](CLAUDE.md)).
External consumers — in particular a separate front-end player application — track
this changelog to know when and how to update.

---

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

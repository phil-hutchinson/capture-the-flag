# Implementation Plan: Revamp rules

This plan implements the conversion to a more simplified ruleset, as specified in the story.

## Step 1 - Update rules, rules change log, and rules technical notes

Update the rules document to reflect the new rules design. Do not exhaustively update the changelog with the changes - instead
identify it as a major rewrite, and refer back to the story for details. Note that the changes here would represent a large enough
change to the rules to warrant an increase to a new major rule version; however, because of the early stage of this project, it
will not be marked as such.

Also update the technical notes related to the rules appropriately.

## Step 2 - Rewrite the rules core: pieces, combat, and movement

Rewrite the piece domain data (`pieces.py`), combat resolution (`combat.py`), and legal-move
generation (`moves.py`) to the new ruleset.

- **Pieces:** replace the twelve-type roster with the new army — ranks 1–6 (Master-of-Arms,
  Champion, Knight, Halberdier, Foot Soldier, Militia) at three each, plus six Towers and one Flag
  (25 pieces total). Remove the Assassin, Archer, Skirmisher, and Sapper types and their symbols.
  Collapse the `Mobility` model to the two cases the new rules need (immobile vs. mobile), since all
  mobile pieces now share one movement rule — no Knight charge or Skirmisher rush. Update the
  symbol/roster tables (`ARMY_ROSTER`, `ARMY_SIZE`, `PIECE_BY_SYMBOL`).
- **Combat:** resolve by rank alone — lower rank number wins, equal rank is a mutual loss. Add the
  formation bonus: a piece with a friendly equal-rank piece within one square (checked before the
  move for the attacker, at the moment of attack for the defender) draws against a piece one rank
  higher instead of losing. Any attack on a Tower is a mutual loss; capturing the Flag is an
  immediate attacker win. Remove all removed-piece special cases (Sapper-vs-Tower, Assassin,
  Knight-vs-Knight charge, Archer support).
- **Movement:** a mobile piece steps one square orthogonally; if it is *unencumbered* (no enemy
  piece in any of its eight surrounding squares) it may instead step two squares orthogonally
  through a clear path. Encumbered pieces move one square only. Keep the existing lake, blocking,
  and friendly-occupancy restrictions.

Why it comes here: these three modules define the piece vocabulary the rest of the engine branches
on. They are treated as a single step because they share an import graph through the package
`__init__` and the new roster removes the enum members the old combat and movement code branch on —
changing one without the others leaves the package unimportable. The `CombatResult` enum and
`CtfPly` shape are unchanged, so the state, placement, and presentation layers still compile against
them until their own steps.

Verification (automated): update and run `pytest tests/test_pieces.py tests/test_combat.py
tests/test_moves.py`. Confirm the roster totals 25 with the six ranks at three each, that equal-rank
attacks and the formation bonus resolve as specified, that any Tower attack is a mutual loss, and
that an unencumbered piece can step two squares while an encumbered one cannot.

## Step 3 - Simplify the endgame: single inactivity counter, remove the Unbreachable Flag

Rework the game-state model and endings to match the simplified rules across `position.py`,
`transitions.py`, `outcome.py`, and `placement.assemble_position`, and delete the now-dead
`breachability.py` and `reachability.py`.

- Replace the two per-side inactivity counters and the separate progress counter with a **single
  shared inactivity counter** on `CtfPosition`. In `transitions.py`, reset it to 0 on any ply that
  removes at least one piece (a winning attack, a mutual loss, or a Tower destruction) and increment
  it by 1 on every non-capturing ply.
- In `outcome.py`, keep only the surviving endings: Flag capture (win) and no-legal-move (loss),
  plus the inactivity draw when the shared counter reaches 50. Remove the Unbreachable Flag and
  no-progress branches and their reason labels; keep the `Flag Captured`, `Inactivity`, and
  `No Legal Move` reasons.
- Remove the breachability cache field from `CtfPosition`, stop populating it in
  `assemble_position`, delete `breachability.py`/`reachability.py`, and drop the corresponding
  `__init__.py` exports (`BreachabilityCache`, `compute_breachability`) and any now-unused `Mobility`
  export left over from Step 2.

Why it comes here: it depends on the Step 2 rules core (the combat results that drive counter
resets) and it removes state fields the presentation layer reads, so it must precede Step 5. These
modules must change together because `outcome.py` and `transitions.py` read the position fields being
removed and would not compile otherwise.

Verification (automated): update and run `pytest tests/test_transitions.py tests/test_outcome.py`.
Confirm the shared counter resets on any capture and increments otherwise, that reaching 50 yields an
inactivity draw, that Flag capture and no-legal-move resolve correctly, and that no test references
the removed Unbreachable Flag or no-progress endings.

## Step 4 - Enforce placement constraints

Update `placement.py` for the new setup rules: each side now places its **25-piece** army into its
48-square home zone, leaving 23 squares empty (a partial fill, not a full one), and **no two Towers
may be adjacent** — orthogonally or diagonally. Update `_validate_placement` to accept any 25-square
subset of the home zone whose piece counts match the new roster and to reject placements with
adjacent Towers. Update `random_placement` to produce a uniformly-random *legal* placement that
respects the Tower non-adjacency constraint.

Depends on: Step 2 (the new `ARMY_ROSTER`) and Step 3 (`assemble_position` no longer builds a
breachability cache).

Verification (automated): update and run `pytest tests/test_placement.py`. Confirm a valid 25-piece
placement is accepted, that a placement with two adjacent Towers (including diagonally) is rejected,
that a full 48-square fill is now rejected, and that repeated `random_placement` calls always satisfy
the Tower non-adjacency rule.

## Step 5 - Update the presentation and record surface

Bring the player- and record-facing layers in line with the new state model.

- `game_view.py`: replace the two-per-side inactivity plus no-progress clock line with the single
  shared inactivity counter against its limit of 50.
- `record.py`: bump `RULESET_VERSION` to `1.2` so records are stamped with the version the Step 1
  changelog and technical notes now declare (the constant is still `1.1`). Also change the ruleset
  tag: rename `RULESET_NAME` from `PRIMARY` to `PRE-RELEASE`, and flip the tag value order to
  `{RULESET_VERSION}:{RULESET_NAME}` so the stamped value becomes `1.2:PRE-RELEASE`. Update the
  `Ruleset` tag description in `technical-notes.md` (currently documents the `NAME:VERSION` form and
  the `PRIMARY` name) to match the new order and name.
- Sanity-check `rendering.py`, `game_logging.py`, and `game_ui.py`: the position block and move
  annotations should render the new symbols (`1`–`6`, `T`, `F`) with no reference to removed pieces
  or clocks.

Depends on: Step 3 (the single-counter state model and removed reason labels).

Verification (automated + manual): update and run `pytest tests/test_game_view.py
tests/test_rendering.py tests/test_game_logging.py`. Then run the text UI / PvP runner on a short
game and confirm the board renders the new pieces and the clock line shows the single inactivity
counter.

## Step 6 - Integration sweep and full green build

Update the remaining cross-cutting tests (`test_smoke.py`, `test_batch_runner.py`,
`test_pvp_runner.py`, `test_human_player.py`, `test_game_ui.py`) for the new roster, movement, and
counter, and resolve any lingering references to removed mechanics. Then confirm the whole system is
consistent end to end.

Depends on: Steps 2–5 (all engine and presentation changes in place).

Verification (automated + manual): run the full suite `pytest`, plus `pyright` and `ruff check .`,
and confirm all pass clean. Then play a complete random-vs-random match through the runner and
confirm it reaches a terminal outcome (Flag capture, no legal move, or the inactivity draw) with a
sensible record.

## Step 7 - README check

Verify `README.md` is still accurate given the ruleset changes — piece names, counts, movement, and
any endgame description it references — updating it if warranted or confirming no change is needed.
The `/update-readme` command automates this by reviewing the current branch diff.

Verification (manual): run `/update-readme`; confirm any README statements about the pieces, army
size, movement, or win/draw conditions match the new rules, and that the resulting README reads
correctly.

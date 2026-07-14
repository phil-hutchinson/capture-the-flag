# Story 18: Revamp the Ruleset

## Summary

Simplify and streamline the Capture the Flag ruleset to reduce complexity while maintaining strategic depth. Replace the current 9-rank piece system with a simpler 6-rank system, remove special abilities (Knight charges, Skirmisher rushes, Archer support, Sapper towers), and unify combat mechanics. Eliminate the dual-counter system (inactivity + progress) in favor of a single inactivity counter.

## Motivation

The current ruleset has grown complex with many piece-specific exceptions and abilities. This story reduces cognitive load, simplifies the implementation, and makes the game easier to teach and explain while preserving the core strategy of flag capture and board control. Importantly,
it is also a game that should be more trainable for AI.

## Specification

### Pieces

Each player has **25 pieces total**:

**Ranked pieces (18 total):**
- Rank 1: Master-of-Arms (3) (rebranded from Lord Marshal)
- Rank 2: Champion (3)
- Rank 3: Knight (3)
- Rank 4: Halberdier (3)
- Rank 5: Foot soldier (3) (rebranded from Infantry)
- Rank 6: Militia (3)

**Immobile pieces (7 total):**
- Flag (1) — win condition target
- Towers (6) — obstacles and tactical elements

**Removed:**
- All current pieces (Lord Marshal, current Champions, Infantry, Skirmishers, Archers, Sappers)
- Assassin piece

### Board and Placement

- Same 12×12 board with lake restrictions
- Each player places exactly 25 pieces in their 48-square home zone (23 squares remain empty)
- **Tower placement constraint:** Towers cannot be placed adjacent to each other, either orthogonally or diagonally (no tower within the immediate 8 surrounding squares of another tower). This means the flag cannot be hidden within a tower perimeter.

### Movement

**Baseline movement:**
- Move **1 or 2 squares orthogonally** when **unencumbered**
- Unencumbered = no enemy piece (including towers and flag) in any of the 8 surrounding squares (orthogonal or diagonal)
- Multi-square moves require a clear path (no friendly or enemy pieces blocking)
- **When encumbered:** pieces move only **1 square**

**No special movement abilities** — all pieces follow the same movement rules.

### Combat

**Basic rank system:**
- Higher ranked (lower numbered) pieces defeat lower ranked pieces
- Equal ranked pieces result in a **draw** — both pieces are removed
- **Special equal-rank rule:** If two pieces of equal rank are within one square (including diagonals) at:
  - The start of the attacking piece's turn, OR
  - The moment the piece is being attacked
  
  Then each piece **draws against a piece 1 rank higher** rather than losing.

**Tower combat:**
- Any piece may attack a tower
- Result: **mutual loss** — both the tower and the attacking piece are removed
- Towers cannot attack

**Flag capture:**
- Immediate win condition — no draw mechanic for the flag

### Win and Draw Conditions

**Win:**
1. **Capture the flag** — immediate win
2. **No legal moves** — opponent cannot make any legal ply (all pieces captured)

**Draw:**
1. **Inactivity counter** — single counter shared concept:
   - Resets when any piece is captured (either by attack or tower destruction)
   - Increments on non-attacking plies
   - Reaches 50 → draw
2. **By agreement** of players

### No Special Abilities

All pieces follow the same movement and combat rules with no exceptions:
- No Knight charges
- No Skirmisher rushes
- No Archer support
- No Sapper tower destruction (towers can only be removed by any piece attacking them)

## Acceptance Criteria

- Ruleset document updated to reflect all changes
- Implementation correctly handles the 6-rank piece system
- Tower placement validation enforces the non-adjacency constraint
- Movement correctly implements the encumbrance rule
- Equal-rank special combat rule is correctly implemented
- Inactivity counter is the only endgame counter
- All piece types, tower mechanics, and winning conditions work correctly
- Existing tests updated to reflect the new rules

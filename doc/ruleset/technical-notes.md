# Capture the Flag — Ruleset Technical Notes

Companion to [`rules.md`](rules.md). `rules.md` is deliberately kept clean enough
to hand to a player as-is, so anything that is really a developer- or
design-facing annotation lives here instead. Nothing in this file changes how the
game is played; it records metadata, provisional values, and cross-references to
the rest of the project.

## Versioning and source of truth

- **Current version:** 1.1 — bumped by Story 00000004 on 2026-07-09. See
  [`changelog.md`](changelog.md) for the full history.
- `rules.md` is the **single source of truth** for the ruleset: the engine
  implementation, tests, evaluators, and any external consumer are checked against
  it. If code and `rules.md` disagree, that is a bug, and `rules.md` is the
  reference.
- The revision history lives in [`changelog.md`](changelog.md). Any change to
  `rules.md` must add a changelog entry and bump the version (see
  [`CLAUDE.md`](CLAUDE.md)).
- The rules are also consumed by a separate front-end player application, which
  tracks the changelog to know when and how to update — another reason the version
  and changelog are load-bearing, not decorative.
- **Latest version only.** This repository implements and supports **only the
  latest ruleset version.** Records are always written under the current version
  (stamped in the record's `Ruleset` tag, below), and no code is maintained for
  reading, replaying, or otherwise interpreting games recorded under earlier rule
  versions. When the version is bumped, the record writer's `RULESET_VERSION`
  constant (`capture_the_flag/record.py`) must be bumped with it.

## Terminology: "move" in the rules, "ply" everywhere else

`rules.md` is written for a non-technical player audience and uses **"move"** for a
single player's action throughout. Everywhere else in this project — code, tests,
plans, and design documents — the term is **"ply"**, per the project vocabulary in
the root `CLAUDE.md`. The two are the same concept: **one move = one ply.**
`rules.md` is the *only* document that prefers "move."

## Game notation and the record file format

The move notation in `rules.md` [Section 4.4](rules.md#44-recording-a-move) and
this file format share one coordinate frame and a common position-block
rendering. The engine currently emits only the plain move form and the
from-placement record shape described below; the result-marking move form and
mid-game records are documented as reserved for later use.

### Player colours

The first player to move is **White**; the second is **Black**, regardless of
the colour the tokens are physically rendered as (tokens are often **Red** for
White and **Blue** for Black). White and Black are the labels used in record
header tags and to identify the two sides in the position block.

### The position block

The full 12×12 board, rendered from White's perspective: row 12 at the top,
row 1 at the bottom, column A at the left. Every square is a fixed-width,
3-character cell, cells separated by a single space, one board row per line
(12 lines of 12 cells). Because a position need not be a game start, a
piece's side cannot be inferred from which half of the board it stands on, so
side is encoded explicitly per cell:

- **White piece:** `[R]` — e.g. `[1]`, `[9]`, `[A]`, `[T]`, `[F]`
- **Black piece:** `*R*` — e.g. `*3*`, `*9*`, `*A*`, `*T*`, `*F*`
- **Empty square:** `---`
- **Lake square:** `XXX`

`R` is the piece symbol from `rules.md` [Section 2.2](rules.md#22-the-pieces):
`1`–`9` for the numbered ranks, `A` Assassin, `T` Tower, `F` Flag. The whole
12×12 board — including the empty buffer rows and the lake rows — is always
shown, so the block is self-describing. This is the same string the engine's
`render_position_block` produces and the library-facing `text_board` reuses.

### Record file format

A record file has three sections, in order, separated by one or more blank
lines:

1. **Header tags**
2. **Position block** (the record's starting board)
3. **Move sequence**

**Header tags** use PGN tag syntax, `[Name "value"]`, one per line. The record
reuses PGN's Seven Tag Roster plus `ResultReason` and `Ruleset` tags: `Event`,
`Site`, `Date`, `Round`, `White`, `Black`, `Result`, `ResultReason`, `Ruleset`.
`Result`, `ResultReason`, and `Ruleset` are always written; the roster tags
(`Event`…`Black`) are optional/best-effort.

`Ruleset` records **which ruleset the game was played under**, in the form
`NAME:VERSION` — e.g. `PRIMARY:1.1`. `NAME` identifies the ruleset variant;
`PRIMARY` is the main ruleset and, at present, the only one. `VERSION` is the
`rules.md` version from the changelog. Because this repository supports only the
latest version (see *Versioning and source of truth* above), every record it
writes carries the current version; the tag exists so a reader can still tell
which rules a stored game was played under. `Result` uses PGN's values:
`1-0` (White wins), `0-1` (Black wins), `1/2-1/2` (draw), `*`
(ongoing/unknown). `ResultReason` is free text (e.g. `Flag Captured`,
`Inactivity`, `No Progress`, `Unbreachable Flag`, `No Legal Move`); until the
shared `game-engine-core` library can surface a termination reason (see the
upstream requirements note planned for a later story) it is recorded as
`Unknown`. `Date` uses PGN's `YYYY.MM.DD` form (`????.??.??` when unknown).
Tag *values* are escaped as in PGN — a literal `\` is written `\\` and a
literal `"` is written `\"` — so a value containing either stays inside its
quotes; writers also collapse any newline in a value to a space, since a tag
occupies a single line.

**Position block** is exactly the format specified above: for a game started
from placement, the revealed initial position; for a mid-game record, the
resumption board.

**Move sequence**: rounds numbered from 1, each `N. WhiteMove BlackMove`,
multiple rounds one per line (or wrapped freely — parsing is
whitespace-insensitive within this section). A game ending on White's move
shows that round with only White's move.

Each move may use **either** notation form from `rules.md` Section 4.4: the
plain form (`L4L3`, source-then-destination, no separator) or the extended
result-marking form (`L4-L3`, with `x` marking a piece that did not survive).
A reader must accept both, and the two forms may even be mixed within one
file. The current reference engine emits only the **plain** form, so a record
it produces looks like:

```
20. L4L3 H2H1
21. K3K2
```

The same ending written in the extended form (equivalent, and also valid):

```
20. L4-L3 H2-H1x
21. K3-K2
```

**Mid-game records** (format-reserved, not yet implemented): a record whose
starting position has Black to move opens the move sequence with
`N... <blackmove>`. Side-to-move and the three clocks for a non-start
resumption would be carried in additional header tags (names TBD). The
current engine only produces from-placement starts (White to move, all
clocks at 0), so this is documented but unused for now.

**File conventions:** UTF-8 encoding. Files are *written* with `\n` (LF) line
endings; *readers* must accept both LF and CRLF. The header, position, and
move sections are separated by one or more blank lines.

## Intended outcomes and their priority

The intended resolution of a well-played game, in order:

1. **Flag capture** — or, where a side has walled its Flag, the **Unbreachable
   Flag** win (Section 6.2).
2. **Draw** — by agreement in human play (Section 6.6), or by the no-progress
   clock (Section 6.5) in engine play. A future engine may be given an explicit
   accept/decline-draw choice when playing humans.

The **inactivity loss** (Section 6.4, the 50-ply individual clock) is *not* meant
to be how a good game ends. It is pressure to force resolution, not an outcome to
play for.

## The two clocks — design

Two independent clocks, with deliberately different reset rules and outcomes.

**Individual inactivity clock (Section 6.4): 50 of a player's own plies → that
player loses.** Any attack you make resets it, *including a complete sacrifice*.
The effect: unproductive shuffling is strictly self-weakening and
self-terminating — to keep stalling you must keep burning pieces, and you run out.
This makes pointless shuffling (e.g. a Knight oscillating between two targets while
an Archer shuffles to cover them) a losing line *by construction*, rather than
something forbidden by an explicit repetition rule that a determined staller could
work around.

- *Opponent-sacrifice reset.* Your opponent's sacrificial attack also resets your
  clock. Without it, a player winning a stream of defensive exchanges (the opponent
  feeding pieces into a strong line) would time out despite dominating — perverse.
  Keeping it *sacrifice-only* (not any opponent attack) means being beaten down by
  winning captures does **not** rescue your clock, so you cannot shuffle-to-safety
  against an opponent who can actually capture you.
- *Sacrifice-to-Tower (Section 4.3).* Letting non-Sappers attack (and die to) a
  Tower guarantees every player always has an attack available to reset their own
  clock: a Tower is immobile, so a "runaway" opponent cannot deny you a target.

**Collective progress clock (Section 6.5): 80 plies with no capture → draw.**
Resets only on a *capture* (an enemy piece removed — a winning attack or a mutual
loss). A complete sacrifice does not reset it. This produces the case we want: when
both sides can only weaken themselves by attacking, they trade stall-then-sacrifice,
which keeps resetting both *individual* clocks (neither times out) but never the
*collective* one, so the game draws at 80. This is preferred over grinding a thin
attrition edge (e.g. 15 mobile pieces vs 14) down to an "exhaustive" but joyless
win that both human players would rather just agree to draw. Against a genuinely
evasive opponent the intended answer is still to capture the Flag, not to win on a
clock.

### Magnitude invariant

The two limits are coupled. A lone staller (opponent actively capturing)
self-eliminates at their 50th own ply ≈ global ply 99–100; the collective clock
fires at 80. Because 80 < ~99, **mutual** inaction resolves as a *draw* (collective
fires first) rather than an arbitrary "first player to move loses." If either limit
is retuned, preserve `collective_plies < 2 × individual_plies − 1`, or the
mutual-standoff outcome flips.

### Provisional values

Both limits — individual **50** plies, collective **80** plies (= 40 turns each) —
are first-playable starting values, expected to be tuned once games are played.
Changing either is a ruleset change (changelog + version bump).

## The Fair Play Rule (Section 7)

Deliberately left undefined in the rulebook. It is primarily a **human-vs-human**
sportsmanship backstop: the clocks bound game length mechanically, but a player who
knows they are lost can still drag things out within the clocks, and no crisp
definition of "unproductive" is worth the complexity for casual play.

For **engine play** we cannot lean on a fuzzy rule, and must keep the AI from
dithering *without* degrading its strength. The failure mode to watch (visible in
public chess engines): a repetition and its non-repeating alternative are
*value-equivalent* to the evaluator, so evaluation noise tips the choice either way
— the engine is not "trying" to repeat, it is indifferent, and will churn
2×-repetitions while still avoiding a 3×-repetition draw. The intended remedy is to
give non-progress a *tiny, strictly negative* signal so there is a gradient away
from dithering — e.g. feeding the clock counts to the nets as input features (the
phase-1 design already plans this) and/or a small shaping term — without distorting
genuine position evaluation. This is a phase-2 AI concern, recorded here so it is
not lost; it is not a rule.

## Clarifications trimmed from the rulebook

Statements removed from `rules.md` to keep it declarative, retained here:

- *Unbreachable Flag (6.2):* when both conditions hold, the opponent can never
  structurally breach the Flag — they have no available Sapper to open the Tower
  wall — which is why the game is decided at once.
- *No legal move (6.3):* this is rarer than it looks, since sacrificial attacks are
  always legal — any mobile piece adjacent to an enemy always has at least one
  legal move.
- *Sacrificial attacks (4.3):* typical uses are clearing a lane or freeing a
  boxed-in piece.

## Naming history

- **"Unbreachable Flag" (Section 6.2)** was called the **"no-hope" rule** in the
  early offline design notes. The mechanic is unchanged; only the player-facing
  name differs. This note exists so that references to the old term in design
  history map cleanly onto the official rule.

## Related design background

Deeper rationale for these rules — why the piece counts, combat asymmetries, and
win conditions are shaped the way they are — lives in the offline design notes
(retained as history, not authoritative). Where those notes disagree with
`rules.md`, `rules.md` governs.

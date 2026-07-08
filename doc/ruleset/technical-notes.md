# Capture the Flag — Ruleset Technical Notes

Companion to [`rules.md`](rules.md). `rules.md` is deliberately kept clean enough
to hand to a player as-is, so anything that is really a developer- or
design-facing annotation lives here instead. Nothing in this file changes how the
game is played; it records metadata, provisional values, and cross-references to
the rest of the project.

## Versioning and source of truth

- **Current version:** 1.0 — introduced by Story 00000001 on 2026-07-08.
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

## Terminology: "move" in the rules, "ply" everywhere else

`rules.md` is written for a non-technical player audience and uses **"move"** for a
single player's action throughout. Everywhere else in this project — code, tests,
plans, and design documents — the term is **"ply"**, per the project vocabulary in
the root `CLAUDE.md`. The two are the same concept: **one move = one ply.**
`rules.md` is the *only* document that prefers "move."

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

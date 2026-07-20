# Story: Consider rank-symmetry optimization

## Summary

An exploratory story: evaluate whether the learned play engine should exploit
the game's rank symmetry, and adopt the winning approach if one earns its
keep. The six ranked pieces interact almost entirely through rank
*differences* — movement is identical across ranks, the army carries the same
count of each rank, and combat (including the formation bonus) is defined
relative to the opponent's rank — so tactics learned at one rank level
transfer conceptually to every other. The baseline network (stories 00000008
and 00000009) encodes ranks as independent one-hot planes and must relearn
those tactics per rank; this story considers making that transfer structural.

## Motivation

The rank symmetry is a near-exact translation symmetry along the rank axis,
broken only at the endpoints (rank 1 has nothing above it, rank 6 nothing
below — analogous to board edges breaking spatial translation symmetry).
Exploiting a genuine symmetry is an inductive bias that typically buys sample
efficiency: patterns learned in one rank neighbourhood apply everywhere,
instead of being rediscovered per rank. Whether that efficiency matters here
is an empirical question — self-play may simply learn its way past it — which
is why this is a "consider" story with measurement at its core, not a
committed feature.

All candidate approaches are derived from the rules alone (the combat
ordering), so they sit within the epic's pure-discovery constraint.

## Background: the candidate approaches

Recorded from the design discussion during story 00000008, cheapest to most
structural:

1. **Do nothing (baseline).** One-hot rank planes; training discovers the
   symmetry from data. Always viable; costs samples, not design.
2. **Input-level — cumulative (thermometer) rank encoding.** Replace or
   augment the one-hot rank planes with cumulative planes ("piece here of
   rank *k* or stronger"), making "outranks" directly readable as a
   difference between plane stacks, so one learned pattern applies at every
   rank level. No architecture change; only the encoder and the network's
   input width move.
3. **Architecture-level — weight sharing along a rank axis.** Treat rank as
   an additional convolutional axis and share weights along it, the way
   spatial convolutions share weights across the board: rank equivariance by
   construction. The strongest transfer, at the highest structural cost.
4. **Training-time — rank-shift data augmentation.** Because the symmetry is
   exact away from the endpoints, a position with no rank-1 (or no rank-6)
   pieces is strategically identical to the same position with every rank
   shifted one step toward the vacated end — each such self-play position
   yields an extra valid training example for free.

These compose: 2 and 4 are cheap and independent; 3 subsumes much of what 2
provides.

## What we want

- **A measured comparison.** At least one candidate approach trained under
  the same budget as the one-hot baseline, compared on training efficiency
  and/or final strength against the fixed reference opponents.
- **A decision.** Adopt, reject, or defer each candidate, recorded with the
  measurements that justify it.
- **Adoption done cleanly, if it happens.** A change of input encoding or
  network body is a retrofit: the encoder module and the network change; the
  action space, policy decoding, evaluator contract, and engine wiring do
  not. Adoption implies a full retrain from scratch — accepted cost.

## Out of scope

- Any change to the rules or to what the encoding is allowed to draw on
  (pure discovery still applies).
- Other auxiliary inputs or training signals not related to rank symmetry.

## Acceptance criteria

- Each considered approach has a recorded adopt/reject/defer decision backed
  by comparative measurement (or an explicit rationale where measurement was
  unnecessary).
- If an approach is adopted: encoding/architecture tests updated alongside
  it, the retrained engine is at least as strong as the pre-change engine
  against the reference opponents, and the story documents the observed
  efficiency or strength gain.
- If nothing is adopted: the story closes with the comparison results
  recorded for future reference.

## Dependencies

- Story 00000009 (self-play training) must be complete: comparing training
  efficiency requires a working training loop and reference-opponent
  strength measurements to compare against.

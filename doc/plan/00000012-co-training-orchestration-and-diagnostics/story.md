# Story: Co-training orchestration and diagnostics

## Summary

Tie the two learning systems together into one supervised, observable process.
The play engine's training and the placement pool's improvement each work in
isolation after stories 00000009 and 00000011; this story interlocks them —
each feeding the other on a schedule — and instruments the whole system with
the measurements that tell us it is healthy and improving. The deliverable is
a single orchestrated training process, resumable and observable, that
improves both phases together.

## Motivation

The two systems are mutually dependent: placement quality is judged by the
play engine, and the play engine should be trained on the kinds of positions
good placement actually produces. Run separately, they drift apart — the
placement mixture stays tuned to a stale, weaker play engine, and the play
engine over-trains on positions no competent placer would create. And because
so much here is learned against a moving reference, plain "is it working?"
questions need deliberate instrumentation to answer.

## What we want

- **Interlocked schedules.** Self-play starting positions drawn from a healthy
  mix — the current placement mixture, plus random placements, plus retired
  pool members — so the play engine stays competent broadly, not just on the
  current fashion. When the play engine has materially improved, the placement
  pool's scores are refreshed and the mixture re-solved, which also gives
  previously discarded placements a fresh hearing under the stronger engine.
- **One orchestrated process.** The full schedule runs unattended across both
  systems, survives interruption and resumes, and records enough to
  reconstruct what happened when.
- **Diagnostics.** The measurements that report system health, tracked over
  training time, including: the exploitability measure from story 00000011
  (the primary health number); the size and spread of the placement mixture;
  agreement between the play engine's cheap judgments and real game outcomes;
  placements the play engine handles poorly (candidates buried before their
  time); how often games end each way — with walled-Flag placements and their
  associated endings called out, since walling is the strategy the system must
  discover on its own; and the measured value of moving first.
- **A presentable summary.** The diagnostics reviewable without archaeology —
  a report or summary a developer can glance at to answer "is training
  healthy, and is it still improving?"
- **Delineation.** The diagnostics harness and the pool re-scoring machinery
  are shared-library candidates; keep them separated from the Capture the
  Flag specifics, per the shared-library-candidates inventory in the epic
  story (00000007).

## Out of scope

- New learning techniques (uncertainty-driven exploration, learned placement
  generators, auxiliary training signals) — refinements this story's
  diagnostics may later justify.
- Final strength targets. This story delivers the process and its
  instruments; how long to run it, and to what strength, is ongoing work
  beyond the epic.

## Acceptance criteria

- One command (or equivalent) runs the interlocked schedule end to end,
  unattended, and can resume after interruption.
- Refreshing placement scores after play-engine improvement demonstrably
  changes the mixture (stale judgments are actually being corrected).
- Every diagnostic listed above is produced during a run and reviewable
  afterward as a coherent summary.
- A sustained run shows both systems improving together: play-engine strength
  rising against fixed references, and placement exploitability falling.

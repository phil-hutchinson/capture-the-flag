# Story: Phase 2 AI self-play training

## Summary

Stand up the self-play training machinery for the play engine built in story
00000008: the engine plays games against itself from randomly generated
placements, learns from the outcomes, and the improved network plays the next
round. The deliverable is a training loop that runs end-to-end on one
workstation and produces a saved model you can play against or resume training
from, with sensible starting hyperparameters that are recorded. *Measuring*
that the engine gets stronger — the tournament that turns strength into a
number, and the tuned run that demonstrates improvement — is deferred to a
follow-up; it needs self-play throughput we do not yet have (a meaningful game
currently takes on the order of 15 minutes).

## Motivation

This is where the AI first becomes real: everything before it is machinery,
and everything after it depends on a play engine whose judgment can be
trusted. In particular, the placement-phase work (stories 00000010 onward)
uses the play engine's assessment of a revealed position as its scoring
function — so "a play engine with meaningful judgment" is the gateway to the
rest of the epic. This story delivers the *machinery* to train that judgment
and a resumable model to iterate on; demonstrating and measuring the resulting
strength is the immediate follow-up.

## What we want

- **A self-play training loop**, reusing the shared library's training
  machinery: the engine plays itself from random placements, the results feed
  training, and the improved network plays the next round. Random placements
  are deliberate at this stage — the engine should learn to play *any*
  position it might be dealt, and the placement phase isn't learned yet.
- **A resumable, saved model.** A checkpoint written using the shared
  library's conventions, so the model can be loaded later — to play against, to
  seed the placement work, or to resume training — after a few rounds of
  training and stopping. A single resumable latest checkpoint is enough here;
  richer checkpoint infrastructure (a strength ladder, selection policies)
  comes with the strength-measurement follow-up.
- **Sensible starting hyperparameters, recorded.** Starting settings (game
  counts, search effort, training cadence, exploration temperature, optimizer /
  learning rate) that let the loop run to completion on a single workstation,
  chosen with justification and captured in the run's config record. Tuning
  them until strength visibly improves is deferred (see Out of scope) — we
  cannot yet run at the scale that would make such tuning meaningful.

## Noted ideas (optional, not acceptance criteria)

- **Flag-relative-location input planes.** Four extra input planes giving
  every square its signed offset (as a fraction of board size, in (−1, 1))
  to the own and enemy flags, horizontally and vertically. The flags never
  move after placement, and under the receptive-field math a distant square
  needs many conv layers before it can "see" a flag — baking the offsets in
  hands every square that knowledge at layer zero, potentially lowering the
  depth the network needs. Cheap to try once baseline training works, and
  measurable as a checkpoint-strength comparison. Must be computed in the
  side-to-move perspective frame like every other input plane, and changes
  the encoder's `INPUT_SHAPE`. (Idea from the story-00000008 step 4
  architecture discussion.) Now scoped as its own follow-up story, not part of
  this one.

## Out of scope

- **Strength measurement and the tuned training run.** The tournament that pits
  checkpoints against the random engine, the flat-value reference, and earlier
  checkpoints — and the hyperparameter tuning that demonstrates later
  checkpoints beating earlier ones — are a follow-up. They are gated on
  self-play throughput this story does not yet provide.
- Placement learning (stories 00000010–00000012) — placements here are random.
- Auxiliary training signals (e.g. predicting *how* a game ends) and other
  sample-efficiency techniques — later refinements if basic training proves
  slow.
- Rules-engine performance work, unless self-play throughput turns out to
  block the story entirely — in which case that becomes its own conversation.
  (The strength-measurement follow-up will likely need this first.)

## Acceptance criteria

- The self-play → train → checkpoint loop runs end to end without intervention
  and produces a saved model.
- The saved model can be loaded and used as a playing engine through the same
  interfaces as every other engine.
- Training can be resumed from the saved model and continues from where it
  stopped.
- Learning is demonstrably occurring at the wiring level — the overfit-a-batch
  loss trends down (the single-generation check) and per-generation loss trends
  down across a modest run. This evidences correct wiring; it is not a strength
  claim — measured strength is the follow-up.
- The starting hyperparameters and run configuration are recorded well enough
  to reproduce the run.

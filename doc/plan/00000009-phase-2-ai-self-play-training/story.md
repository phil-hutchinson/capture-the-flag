# Story: Phase 2 AI self-play training

## Summary

Train the play engine built in story 00000008 to basic competence: the engine
plays games against itself from randomly generated placements, learns from the
outcomes, and gets measurably stronger. The deliverable is a training run that
produces saved engine versions of clearly increasing strength — decisively
beating the random engine, and measured against the flat-value reference
engine.

## Motivation

This is where the AI first becomes real: everything before it is machinery,
and everything after it depends on a play engine whose judgment can be
trusted. In particular, the placement-phase work (stories 00000010 onward)
uses the play engine's assessment of a revealed position as its scoring
function — so "a play engine with meaningful judgment" is the gateway to the
rest of the epic.

## What we want

- **A self-play training loop**, reusing the shared library's training
  machinery: the engine plays itself from random placements, the results feed
  training, and the improved network plays the next round. Random placements
  are deliberate at this stage — the engine should learn to play *any*
  position it might be dealt, and the placement phase isn't learned yet.
- **Checkpoints.** Saved versions at regular intervals, using the shared
  library's conventions, so any version can be loaded later — for strength
  comparison, for the placement work, or as a tournament entrant.
- **Strength measurement.** Tournament runs pitting checkpoints against the
  random engine, the flat-value engine, and earlier checkpoints, so progress
  is a number rather than an impression.
- **A workable training recipe.** Settings (game counts, search effort,
  training cadence) that produce visible learning on a single workstation in
  acceptable wall-clock time. Finding these is part of the story; documenting
  what was tried belongs in the story's records.

## Out of scope

- Placement learning (stories 00000010–00000012) — placements here are random.
- Auxiliary training signals (e.g. predicting *how* a game ends) and other
  sample-efficiency techniques — later refinements if basic training proves
  slow.
- Rules-engine performance work, unless self-play throughput turns out to
  block the story entirely — in which case that becomes its own conversation.

## Acceptance criteria

- A training run completes end to end without intervention and produces a
  series of checkpoints.
- Later checkpoints beat earlier ones; the final checkpoint beats the random
  engine overwhelmingly and performs credibly against (ideally beats) the
  flat-value reference engine.
- Any checkpoint can be loaded and used as a playing engine through the same
  interfaces as every other engine.
- The training configuration used is recorded well enough to reproduce the
  run.

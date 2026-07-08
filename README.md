# capture-the-flag

A two-phase, perfect-information battlefield board game with an AI that learns to play
it. Phase 1 is secret simultaneous placement of 48 pieces per side; phase 2 is
alternating, fully visible play on a 12x12 board until a flag is captured (or a
structural "no hope" / no-progress condition resolves the game).

The game is built on [game-engine-core](https://github.com/phil-hutchinson/game-engine-core),
which provides the game-agnostic engine, MCTS/PUCT search, and learning
infrastructure. This repository implements the Capture the Flag ruleset,
position/ply types, evaluators, and the phase 1 / phase 2 training on top of it.

> **Status:** bootstrap. The scaffolding, dev container, and a smoke test are in
> place; the ruleset and AI implementation land in subsequent stories.

## Requirements

- Python 3.12+
- The dev container installs everything else (including the pinned
  `game-engine-core` dependency and PyTorch).

## Development

The repo ships a VS Code Dev Container that provisions the full environment
automatically. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the toolchain,
and conventions.

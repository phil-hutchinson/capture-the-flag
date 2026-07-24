# capture-the-flag

A two-phase, perfect-information battlefield board game with an AI that learns to play
it. Phase 1 is secret simultaneous placement of 25 pieces per side; phase 2 is
alternating, fully visible play on a 12x12 board until a flag is captured (or a
player is left with no legal move, or an inactivity limit forces a draw).

The game is built on [game-engine-core](https://github.com/phil-hutchinson/game-engine-core),
which provides the game-agnostic engine, MCTS/PUCT search, and learning
infrastructure. This repository implements the Capture the Flag ruleset,
position/ply types, evaluators, and the phase 1 / phase 2 training on top of it.

> **Status:** the rules engine is fully implemented and playable — board and
> piece geometry, legal move generation, combat resolution, and every ending
> condition. On top of it sits a learned play engine — position encoding, a
> value/policy network, an evaluator, and an MCTS-backed player — that plays
> complete legal games, together with a self-play training loop that improves
> the network generation over generation. Random, human, and learned players are
> selectable in both the headless batch runner and the terminal single-game
> runner.

## Requirements

- Python 3.12+
- The dev container installs everything else (including the pinned
  `game-engine-core` dependency and PyTorch).

## The engine

`capture_the_flag/` implements the ruleset in
[`doc/ruleset/rules.md`](doc/ruleset/rules.md) as a `game-engine-core`-compatible
game: `CtfPosition`/`CtfPly` (board state, legal moves, combat, endings), a
placement seam that assembles a starting position from two per-side
placements, and a `CtfPlayer` seam so `game-engine-core`'s players and
`StandardGame` drive phase-2 play unchanged.

## Running a batch of games

A headless runner plays batches of machine-vs-machine games (random or the
learned engine, in either seat) and writes a record file per game:

```bash
python -m capture_the_flag.batch_runner -n 100 -o games
```

`-n`/`--games` sets the batch size and `-o`/`--output-dir` the record output
directory; `--seed` seeds the batch for reproducible runs. `--white`/`--black`
choose each seat's kind — `random` or `neural` (the learned engine); a neural
seat's search is tuned with `--iterations`/`--temperature`. Each record names the
result and how the game ended and renders moves in the ruleset's combat
notation, and the run prints an outcome split, an ending-category breakdown, and
game-length statistics. Record files follow the format documented in
[`doc/ruleset/technical-notes.md`](doc/ruleset/technical-notes.md).

## Playing a game in the terminal

The single-game runner plays one complete game — placement, alternating play, and
an announced result — between any two player kinds. `--white`/`--black` choose
each seat: `human`, `random`, or `neural` (both default to `human`, so with no
options it is a human-vs-human game); `--white-name`/`--black-name` set display
names, and `--iterations`/`--temperature` tune a neural seat's search.

```bash
python -m capture_the_flag.game_runner --white human --black neural \
    --white-name Alice
```

The board is rendered before a human's turn (and throughout a machine-vs-machine
game, so it can be watched). Each human player supplies their phase-1 setup at a
prompt: either the name of a
placement file read from the gitignored `placements/` folder
(`-p`/`--placements-dir` overrides the folder), or `random` for a random legal
placement. A placement file is 4 rows of 12 characters — each a one-character
piece symbol (`1`–`6`, `T`, `F`) or `-` for an empty square, since only 25 of
the 48 home squares are filled — written from the owning player's seat (first
line nearest the lakes, last line the back rank), so the same file produces the
same setup for either side. Moves are typed in the simple source–destination
notation (e.g. `A2A3`); malformed or illegal input re-prompts with an
explanation, and each turn's display shows the coordinate-labelled board,
captured pieces, and the inactivity clock.

## Training the engine

A self-play training runner improves the learned network generation over
generation: each generation collects self-play games with the current network,
trains on them, saves a checkpoint, and carries the improved network forward.

```bash
python -m capture_the_flag.training_runner --generations 10
```

Each run lands in its own timestamped directory under `./training-runs/`
(gitignored), holding the checkpoint series and a `run-config.json`
reproducibility record. The self-play and training shape is tuned with
`--games` (games per generation), `--iterations`/`--temperature` (self-play
search), `--epochs`/`--batch-size`/`--learning-rate` (training),
`--features`/`--residual-blocks` (the network's width and depth), and
`--seed`; unset flags fall back to modest built-in defaults. `--resume`
reloads the most recent run's latest checkpoint and trains `--generations`
more into the same run, reusing that run's recorded hyperparameters — the
architecture included, so a resumed run rebuilds the network at the size it
was started at.

## Development

The repo ships a VS Code Dev Container that provisions the full environment
automatically. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the toolchain,
and conventions.

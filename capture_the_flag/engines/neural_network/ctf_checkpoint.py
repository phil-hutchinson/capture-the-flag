"""Checkpoint persistence for the learned play engine (story 00000009, Step 5).

Weights-only and resumable. Saving/loading the actual tensors is game-side code:
the shared `game_engine_learning.checkpoints` module is torch-free and only
supplies the run-directory / checkpoint-path naming, so the `torch.save` /
`torch.load` of the `CtfCrn` state lives here.

Two load directions share one file:

- `load_network` rehydrates the `CtfCrn` itself, so training can resume from a
  saved generation (Step 7 uses this).
- `load_neural_player` wires that network into a playable seat (evaluator + MCTS
  engine + `NeuralCtfPlayer`), so any checkpoint plays through the same
  interfaces as every other engine.

Optimizer state is deliberately not persisted. Training builds a fresh optimizer
per generation, so optimizer state never crosses a generation boundary and there
is nothing to carry across a resume (see doc/general-vocabulary.md, "Optimizer
state"). If that ever changes to a long-lived optimizer with a learning-rate
schedule, revisit this.
"""

from __future__ import annotations

import random
from pathlib import Path

import torch

from .ctf_crn import CtfCrn
from .neural_ctf_player import (
    DEFAULT_ITERATIONS,
    DEFAULT_TEMPERATURE,
    NeuralCtfPlayer,
    build_neural_player,
)

DEFAULT_RUNS_DIR = Path("training-runs")
"""Repo-root-relative base directory for training-run artifacts (checkpoints and,
from Step 6, the run-config record). Gitignored — runs are machine-local — and
resolved against the current working directory, matching the runners' existing
`placements/` convention."""


def save_checkpoint(network: CtfCrn, path: Path) -> None:
    """Write `network`'s weights to `path` (weights only, no optimizer state).

    Build `path` with `game_engine_learning.checkpoints.checkpoint_path` so the
    file lands in a run directory under the shared naming convention. The parent
    directory is created if it does not already exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(network.state_dict(), path)


def load_network(path: Path) -> CtfCrn:
    """Rebuild a `CtfCrn` from a checkpoint file, ready to resume training.

    A fresh network is constructed and the saved weights loaded into it; the
    checkpoint holds only weights, so the architecture must match the current
    `CtfCrn` (it does, since one module owns both save and load).
    """
    network = CtfCrn()
    state_dict = torch.load(path, map_location="cpu", weights_only=True)
    network.load_state_dict(state_dict)
    return network


def load_neural_player(
    path: Path,
    name: str,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    temperature: float = DEFAULT_TEMPERATURE,
    rng: random.Random | None = None,
    render_before_ply: bool = False,
) -> NeuralCtfPlayer:
    """Load a checkpoint into a playable seat: the saved network behind the
    evaluator + `MCTSEngine` + `NeuralCtfPlayer`, so a checkpoint plays through
    the same interfaces as every other engine. Search settings default to the
    greedy play-time defaults."""
    return build_neural_player(
        name,
        network=load_network(path),
        iterations=iterations,
        temperature=temperature,
        rng=rng,
        render_before_ply=render_before_ply,
    )

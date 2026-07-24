"""Checkpoint persistence for the learned play engine.

Weights-only and resumable. Saving/loading the actual tensors is game-side code:
the shared `game_engine_learning.checkpoints` module is torch-free and only
supplies the run-directory / checkpoint-path naming, so the `torch.save` /
`torch.load` of the `CtfCrn` state lives here.

Every checkpoint also stamps the engine I/O spec (`ENGINE_SPEC_NAME`) its
weights were produced against. `CtfCrn`'s input width follows `INPUT_SHAPE`
directly, so a checkpoint saved against a superseded, differently-shaped spec
(e.g. an `ENG_NN_1` checkpoint from before this story) would otherwise fail to
load with an opaque `state_dict` shape mismatch, or — worse, if the shapes ever
happened to coincide — load "successfully" into a network that misinterprets
its planes. `load_network` checks the stamp before touching the network at all,
so that failure is immediate and names the mismatch.

Alongside the spec, a checkpoint records the architecture (`CtfCrn`'s trunk width
and residual-block count) its weights were trained at. The two stamps are handled
deliberately differently on load: a spec mismatch means the *input contract*
changed, so the weights are meaningless and the checkpoint is rejected; a
differing architecture means the weights are perfectly valid and only the
container's shape differs, so the network is *reconstructed* at the recorded
sizes rather than rejected. That is what lets checkpoints trained at different
widths coexist under one code version, which any later width comparison needs.

Two load directions share one file:

- `load_network` rehydrates the `CtfCrn` itself, so training can resume from a
  saved generation (the resume path uses this).
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
from .tensor_layout import ENGINE_SPEC_NAME

DEFAULT_RUNS_DIR = Path("training-runs")
"""Repo-root-relative base directory for training-run artifacts (checkpoints and
the run-config record). Gitignored — runs are machine-local — and
resolved against the current working directory, matching the runners' existing
`placements/` convention."""

_CHECKPOINT_SPEC_KEY = "spec"
_CHECKPOINT_STATE_DICT_KEY = "state_dict"
_CHECKPOINT_ARCHITECTURE_KEY = "architecture"
_FEATURE_COUNT_KEY = "feature_count"
_RESIDUAL_BLOCK_COUNT_KEY = "residual_block_count"


def save_checkpoint(network: CtfCrn, path: Path) -> None:
    """Write `network`'s weights to `path` (weights only, no optimizer state),
    stamped with the engine spec (`ENGINE_SPEC_NAME`) they were produced under
    and the architecture `network` was built at.

    Build `path` with `game_engine_learning.checkpoints.checkpoint_path` so the
    file lands in a run directory under the shared naming convention. The parent
    directory is created if it does not already exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        _CHECKPOINT_SPEC_KEY: ENGINE_SPEC_NAME,
        _CHECKPOINT_ARCHITECTURE_KEY: {
            _FEATURE_COUNT_KEY: network.feature_count,
            _RESIDUAL_BLOCK_COUNT_KEY: network.residual_block_count,
        },
        _CHECKPOINT_STATE_DICT_KEY: network.state_dict(),
    }
    torch.save(checkpoint, path)


def load_network(path: Path) -> CtfCrn:
    """Rebuild a `CtfCrn` from a checkpoint file, ready to resume training.

    The checkpoint's stamped spec is checked against `ENGINE_SPEC_NAME` before
    anything else, so a checkpoint saved against a superseded, shape-incompatible
    spec is rejected with a clear error naming the mismatch, rather than either
    an opaque `state_dict` shape error or — should the shapes ever coincide — a
    network that silently misinterprets its input planes.

    Once that check passes, the network is rebuilt at the architecture the
    checkpoint records rather than at the current defaults, so a checkpoint
    trained at a different width or depth reloads at its own size instead of
    failing to fit a default-sized container.
    """
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or _CHECKPOINT_SPEC_KEY not in checkpoint:
        raise ValueError(
            f"{path} has no engine-spec stamp, so it predates spec stamping and "
            f"cannot be verified against the current {ENGINE_SPEC_NAME!r} input "
            "contract."
        )
    stamped_spec = checkpoint[_CHECKPOINT_SPEC_KEY]
    if stamped_spec != ENGINE_SPEC_NAME:
        raise ValueError(
            f"{path} was saved against spec {stamped_spec!r}, but the running "
            f"code implements {ENGINE_SPEC_NAME!r}. Checkpoints are not "
            "compatible across engine-spec changes; retrain from scratch."
        )
    if _CHECKPOINT_ARCHITECTURE_KEY not in checkpoint:
        # Guessing an architecture would risk loading weights into a network of
        # the wrong shape, which is exactly what stamping exists to prevent.
        raise ValueError(
            f"{path} has no architecture stamp, so the width and depth its "
            "weights were trained at are unknown and the network cannot be "
            "rebuilt to fit them."
        )
    architecture = checkpoint[_CHECKPOINT_ARCHITECTURE_KEY]
    network = CtfCrn(
        feature_count=architecture[_FEATURE_COUNT_KEY],
        residual_block_count=architecture[_RESIDUAL_BLOCK_COUNT_KEY],
    )
    network.load_state_dict(checkpoint[_CHECKPOINT_STATE_DICT_KEY])
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

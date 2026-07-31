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

A third stamp records the **ruleset configuration** — the edition plus any
deviating flags — the weights were trained under. The spec stamp does not cover
this: `ENGINE_SPEC_NAME` names the tensor *shape* contract, so a rules-only
change leaves it untouched and an unpinned checkpoint would load cleanly into a
network evaluating under rules it never saw. It is also a stricter statement than
an engine spec's compatible-rulesets list: that list is the *set* of rulesets an
I/O contract can serve, many-to-one, while this stamp is the single *point* in
that set these weights actually occupy.

Its three outcomes on load mirror the reasoning above, one per case:

- **absent** — rejected. A checkpoint from before ruleset stamping cannot be
  verified at all, and defaulting it would assert something unknown.
- **present and implementable** — *adopted*, so a resumed run continues under the
  configuration it was trained under rather than under current defaults, exactly
  as the architecture already is. A checkpoint trained with a flag on resumes
  with that flag on even if the current default is off, and the checkpoints that
  resume goes on to write carry the adopted configuration rather than the active
  one — that is what `save_checkpoint`'s `configuration` argument is for.
- **present and not implementable** — rejected, naming the flag. This is the case
  where the running code cannot be the code that trained these weights.

Backward compatibility is not the goal here; knowing whether the network matches
the variant in play is, and failing clearly when it does not, rather than running
silently against rules the network was never trained for.

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch

from ...record import (
    RulesetConfiguration,
    active_configuration,
    unsupported_aspects,
)
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
_CHECKPOINT_RULESET_KEY = "ruleset"
_FEATURE_COUNT_KEY = "feature_count"
_RESIDUAL_BLOCK_COUNT_KEY = "residual_block_count"


def save_checkpoint(
    network: CtfCrn, path: Path, *, configuration: RulesetConfiguration | None = None
) -> None:
    """Write `network`'s weights to `path` (weights only, no optimizer state),
    stamped with the engine spec (`ENGINE_SPEC_NAME`) they were produced under,
    the architecture `network` was built at, and the ruleset configuration they
    were trained under.

    `configuration` is that last stamp, defaulting to `active_configuration()` —
    what a run starting fresh is training under. A resumed run passes the
    configuration it adopted from the checkpoint it continued from instead, so
    the generations it appends carry the rules they were actually trained under
    rather than whatever the current active edition happens to be. Defaulting it
    here rather than requiring it keeps every caller that genuinely is training
    under current rules unchanged.

    Build `path` with `game_engine_learning.checkpoints.checkpoint_path` so the
    file lands in a run directory under the shared naming convention. The parent
    directory is created if it does not already exist.
    """
    if configuration is None:
        configuration = active_configuration()
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        _CHECKPOINT_SPEC_KEY: ENGINE_SPEC_NAME,
        _CHECKPOINT_ARCHITECTURE_KEY: {
            _FEATURE_COUNT_KEY: network.feature_count,
            _RESIDUAL_BLOCK_COUNT_KEY: network.residual_block_count,
        },
        _CHECKPOINT_RULESET_KEY: configuration.as_stamp(),
        _CHECKPOINT_STATE_DICT_KEY: network.state_dict(),
    }
    torch.save(checkpoint, path)


def checkpoint_configuration(path: Path) -> RulesetConfiguration:
    """The ruleset configuration `path` was trained under.

    Separate from `load_network` because a resume needs the configuration to
    carry forward and to cross-check its run config against, without any interest
    in the weights. Applies the same three outcomes `load_network` does — absent
    is rejected, unusable is rejected, unimplementable is rejected — so a
    configuration this returns is always one this code can actually play under.

    A resume calling both reads the file twice, which is deliberate: it keeps
    `load_network` returning exactly what its name says, and a second read of a
    ~15MB file is nothing beside the generation of self-play that follows it.
    """
    return _stamped_configuration(_loaded_checkpoint(path), path)


def _loaded_checkpoint(path: Path) -> dict[str, Any]:
    """Load `path` and confirm it has a checkpoint's overall shape.

    Shared by both entry points so that a structurally broken file is diagnosed
    the same way whichever one reads it: reached through `load_network` the next
    thing checked is the spec stamp and through `checkpoint_configuration` the
    ruleset stamp, and without this a file that is not a mapping at all would be
    reported as missing whichever stamp its reader happened to want.
    """
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict):
        raise ValueError(
            f"{path} is not a checkpoint: expected a mapping of stamps and "
            f"weights, got {type(checkpoint).__name__}."
        )
    return checkpoint


def _stamped_configuration(
    checkpoint: Mapping[str, object], path: Path
) -> RulesetConfiguration:
    """Read, validate, and adopt the ruleset stamp of an already-loaded checkpoint.

    The adopted configuration is the checkpoint's own, not the active one: a
    resume continues under the rules its weights were trained under, and the
    active configuration is only what a *fresh* run starts from. `save_checkpoint`
    takes it back as its `configuration` argument, which is what carries the
    adoption through to the generations a resume appends.
    """
    if _CHECKPOINT_RULESET_KEY not in checkpoint:
        raise ValueError(
            f"{path} has no ruleset stamp, so it predates ruleset stamping and the "
            "rules its weights were trained under are unknown. A network is only "
            "valid for the rules it was trained on; retrain from scratch."
        )
    try:
        configuration = RulesetConfiguration.from_stamp(checkpoint[_CHECKPOINT_RULESET_KEY])
    except ValueError as error:
        # Present but unreadable is no better than absent, and gets the same
        # named failure rather than a bare KeyError deeper in.
        raise ValueError(f"{path}'s ruleset stamp is malformed: {error}") from error
    aspects = unsupported_aspects(configuration)
    if aspects:
        raise ValueError(
            f"{path} was trained under a ruleset configuration this code cannot "
            f"implement: {'; '.join(aspects)}. The network would be evaluating "
            "under rules it was not trained for."
        )
    return configuration


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

    The ruleset stamp is checked too, and rejected if absent or beyond what this
    code implements — a rules-only change leaves `ENGINE_SPEC_NAME` untouched, so
    without this check the weights would load cleanly into a network evaluating
    under rules they were never trained for. Use `checkpoint_configuration` to
    read the stamped configuration itself.
    """
    checkpoint = _loaded_checkpoint(path)
    if _CHECKPOINT_SPEC_KEY not in checkpoint:
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
    if not isinstance(architecture, dict) or not {
        _FEATURE_COUNT_KEY,
        _RESIDUAL_BLOCK_COUNT_KEY,
    } <= architecture.keys():
        # A stamp that is present but unreadable is no better than an absent one,
        # and deserves the same named failure rather than a bare KeyError.
        raise ValueError(
            f"{path}'s architecture stamp is malformed: expected a mapping with "
            f"{_FEATURE_COUNT_KEY!r} and {_RESIDUAL_BLOCK_COUNT_KEY!r}, got "
            f"{architecture!r}."
        )
    _stamped_configuration(checkpoint, path)
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

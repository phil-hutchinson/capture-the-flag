"""Single-generation training glue.

Composes the three established surfaces into one generation of learning: collect
self-play samples with the current network, then run joint value/policy gradient
descent over them (the shared `TrainingLoop`) with the game-specific
`ctf_policy_loss`. No orchestration, checkpointing, or run record here — the
orchestrator carries the improved network from one generation into the next.

`train_one_generation` builds the evaluator internally from `network` so the
collector's encoder and the search engine are guaranteed to share the same
network (the collector encodes with the evaluator while the engine searches with
it; they must be one network). Hyperparameters are the caller's to choose: the
defaults here are throwaway values for the "does learning happen at all" check,
not a tuned training recipe.
"""

from collections.abc import Callable

from game_engine_learning.training_loop import EpochLoss, TrainingLoop
from torch.optim import Optimizer

from ...instrumentation.timing import region
from ...position import CtfPosition
from ...timing_regions import SELF_PLAY, TRAIN
from .ctf_crn import CtfCrn
from .ctf_engine_factory import CtfEngineFactory
from .ctf_nn_evaluator import CtfNNEvaluator
from .ctf_policy_target import ctf_policy_loss
from .ctf_self_play import build_self_play_collector


def train_one_generation(
    network: CtfCrn,
    optimizer: Optimizer,
    *,
    n_games: int,
    epochs: int,
    batch_size: int = 32,
    self_play_iterations: int = 100,
    self_play_temperature: float = 1.0,
    position_factory: Callable[[], CtfPosition] | None = None,
) -> list[EpochLoss]:
    """Run one generation over `network` and return the per-epoch loss history.

    Collects `n_games` self-play games with the current `network`, then trains
    for `epochs` passes over that one collected batch. `network` is mutated in
    place (its weights are updated), so the caller holds the improved network
    after the call — this is the seam the generations loop reuses.

    `optimizer` must already be bound to `network.parameters()` (the caller
    builds it, so the optimizer/learning-rate choice stays a tuning decision for
    later). `self_play_temperature` defaults non-zero so self-play games diverge
    and the visit distributions carry policy signal — distinct from the greedy
    play-time default. A decreasing loss history is the signal that learning is
    happening (and the end-to-end test that the policy column mapping is correct:
    a flat or rising policy loss is that mapping's bug signature).
    """
    evaluator = CtfNNEvaluator(network)
    engine_factory = CtfEngineFactory(
        evaluator,
        iterations=self_play_iterations,
        temperature=self_play_temperature,
    )
    collector = build_self_play_collector(
        evaluator,
        engine_factory=engine_factory,
        position_factory=position_factory,
    )
    # The generation's two halves, timed separately: producing the data is
    # expected to dwarf learning from it, and the report is where that stops
    # being an expectation.
    with region(SELF_PLAY):
        samples = collector.collect(n_games)

    loop = TrainingLoop(network, optimizer, ctf_policy_loss)
    with region(TRAIN):
        return loop.train(samples, epochs=epochs, batch_size=batch_size)

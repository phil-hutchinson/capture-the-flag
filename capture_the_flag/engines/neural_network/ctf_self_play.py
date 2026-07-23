"""Self-play collection wiring for Capture the Flag (story 00000009, Step 3).

Composes the shared `SelfPlayCollector` from the game-specific pieces: the
story-8 evaluator, the Step-3 engine factory (self-play search budget +
exploration temperature), the Step-2 random-placement position factory, and the
Step-1 capture-time policy transform.

The transform is the load-bearing wiring. It re-keys each MCTS visit
distribution into the network's white-normalized frame *while the collector
still holds the position* (and thus its `active_player_id`); omitting it stores
Black-to-move targets in the wrong frame and silently trains the policy head
against mis-framed targets rather than crashing.
"""

from collections.abc import Callable

from game_engine_learning.self_play_collector import SelfPlayCollector

from ...position import CtfPosition
from .ctf_engine_factory import CtfEngineFactory
from .ctf_nn_evaluator import CtfNNEvaluator
from .ctf_position_factory import CtfPositionFactory
from .train import transform_policy_to_white_perspective


def build_self_play_collector(
    evaluator: CtfNNEvaluator,
    engine_factory: CtfEngineFactory | None = None,
    position_factory: Callable[[], CtfPosition] | None = None,
) -> SelfPlayCollector:
    """Wire a `SelfPlayCollector` around `evaluator`.

    `engine_factory` and `position_factory` are injectable so callers can tune
    the self-play search budget / temperature and (later) swap in a curriculum
    position factory; both default to the standard full-army, default-budget
    pieces. A caller supplying its own `engine_factory` is responsible for
    building it over *this* `evaluator` — the collector encodes with `evaluator`
    while the engine searches with it, and they must be the same network.
    """
    return SelfPlayCollector(
        evaluator=evaluator,
        engine_factory=engine_factory or CtfEngineFactory(evaluator),
        position_factory=position_factory or CtfPositionFactory(),
        policy_transform=transform_policy_to_white_perspective,
    )

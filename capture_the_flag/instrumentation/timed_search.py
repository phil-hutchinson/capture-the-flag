"""The search engine with its boundary timed.

`MCTSEngine` lives in `game-engine-core`, which this project consumes as a
pinned third-party dependency and does not modify — so the tree walk, expansion,
and backpropagation inside a search cannot be instrumented directly. What *can*
be timed is the boundary: how long a call into the engine takes.

That is enough, because of how regions nest. Everything the engine calls back
into — position evaluation, legal-ply generation, ply application, outcome
checks — is instrumented on our side, and by the call-path rule those recordings
land underneath whichever search call is open. So a search region's unattributed
remainder is exactly the engine's own internals, and cannot be inflated by our
code running anywhere else in the process. That number is the story's headline:
it says whether optimization effort belongs in this repository or upstream.

This subclasses rather than wraps because the shared self-play collector asks
for an `MCTSEngine` by name. If the timing ever moves into `game-engine-core`,
it belongs in `MCTSEngine` itself and this class disappears.
"""

from typing import Any

from game_engine_core.engines.mcts_engine import MCTSEngine
from game_engine_core.protocols.game_ply import GamePly
from game_engine_core.protocols.game_position import GamePosition
from game_engine_core.protocols.position_evaluator import PositionEvaluator

from .timing import region

SEARCH = "search"
"""A play-time search: one call to `select_ply`."""

SEARCH_WITH_POLICY = "search-with-policy"
"""A self-play search: one call to `select_ply_with_policy`. Distinct from
`SEARCH` because it also builds the visit distribution the training target is
made from, and because a run does one or the other, never both."""

SEARCH_OBSERVE_PLY = "search-observe-ply"
"""Re-rooting the tree after a ply was played in the real game."""

SEARCH_RESET = "search-reset"
"""Dropping the tree at the start of a game."""


class TimedMCTSEngine[
    TPly: GamePly,
    TPosition: GamePosition[Any],
    TEvaluator: PositionEvaluator[Any, Any],
](MCTSEngine[TPly, TPosition, TEvaluator]):
    """`MCTSEngine`, with every call into it timed.

    Behaviour is unchanged — each override opens a region and delegates — so a
    seat built on this plays exactly the games the plain engine would.
    """

    def select_ply(self, game_position: TPosition) -> TPly:
        with region(SEARCH):
            return super().select_ply(game_position)

    def select_ply_with_policy(
        self, game_position: TPosition
    ) -> tuple[TPly, dict[str, float]]:
        with region(SEARCH_WITH_POLICY):
            return super().select_ply_with_policy(game_position)

    def observe_ply(
        self, position: TPosition, ply: TPly, new_position: TPosition
    ) -> None:
        with region(SEARCH_OBSERVE_PLY):
            super().observe_ply(position, ply, new_position)

    def reset(self) -> None:
        with region(SEARCH_RESET):
            super().reset()

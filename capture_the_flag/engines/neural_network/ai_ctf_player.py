"""The learned-engine player and its untrained-play search settings.

`AICtfPlayer` is a thin `CtfPlayer`: phase-2 play is delegated to an injected
`MCTSEngine` (over the learned evaluator), and `get_placement` returns a random
placement for now — placement intelligence is out of scope until stories
00000010-00000012. `build_ai_player` is the construction seam the runners use;
it is the only place `torch` (via the network and evaluator) is pulled in.
"""

import random

from game_engine_core.engines.mcts_engine import MCTSEngine
from game_engine_core.players.ai_player import AIPlayer
from game_engine_core.protocols.game_engine import GameEngine

from ...placement import Placement, random_placement
from ...player import CtfPlayer
from ...ply import CtfPly
from ...position import CtfPosition
from ...side import Side
from .ctf_crn import CtfCrn
from .ctf_nn_evaluator import CtfNNEvaluator

DEFAULT_ITERATIONS = 100
"""MCTS iterations per ply for untrained play: small enough that a batch of
games finishes in reasonable wall-clock time (the engine is weak either way)."""

DEFAULT_TEMPERATURE = 0.0
"""Greedy ply selection — take the most-visited child, no exploration noise."""


class AICtfPlayer(AIPlayer[CtfPly, CtfPosition], CtfPlayer):
    """A `CtfPlayer` whose phase-2 play comes from the injected engine and whose
    phase-1 placement is (for now) drawn at random from `rng`."""

    def __init__(
        self,
        engine: GameEngine[CtfPly, CtfPosition],
        name: str,
        rng: random.Random | None = None,
        render_before_ply: bool = False,
    ) -> None:
        super().__init__(engine, name, render_before_ply)
        self._rng = rng if rng is not None else random.Random()

    def get_placement(self, side: Side) -> Placement:
        """A random legal placement. AI placement is out of scope for this story
        (stories 00000010-00000012)."""
        return random_placement(side, self._rng)


def build_ai_player(
    name: str,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    temperature: float = DEFAULT_TEMPERATURE,
    rng: random.Random | None = None,
    render_before_ply: bool = False,
) -> AICtfPlayer:
    """Construct an untrained learned-engine player: a fresh network wrapped in
    the evaluator and an `MCTSEngine`, seated behind an `AICtfPlayer`."""
    engine: MCTSEngine[CtfPly, CtfPosition, CtfNNEvaluator] = MCTSEngine(
        evaluator=CtfNNEvaluator(CtfCrn()),
        iterations=iterations,
        temperature=temperature,
    )
    return AICtfPlayer(engine, name, rng=rng, render_before_ply=render_before_ply)

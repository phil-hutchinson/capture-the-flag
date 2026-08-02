"""The learned-engine player and its untrained-play search settings.

`NeuralCtfPlayer` is a thin `CtfPlayer`: phase-2 play is delegated to an injected
`MCTSEngine` (over the learned evaluator), and `get_placement` returns a random
placement for now — placement intelligence is out of scope here.
`build_neural_player` is the construction seam the runners use; it is the only
place `torch` (via the network and evaluator) is pulled in.

The class still inherits the shared library's `AIPlayer` (its generic engine
seat), but everything game-specific here is named "neural" to match the player
kind the runners expose.
"""

import random

from game_engine_core.engines.mcts_engine import MCTSEngine
from game_engine_core.players.ai_player import AIPlayer
from game_engine_core.protocols.game_engine import GameEngine

from ...game_setup import GameSetup
from ...instrumentation.timed_search import TimedMCTSEngine
from ...placement import Placement, random_placement
from ...player import CtfPlayer
from ...ply import CtfPly
from ...position import CtfPosition
from ...side import Side
from .ctf_crn import CtfCrn
from .ctf_nn_evaluator import CtfNNEvaluator
from .tensor_layout import TensorLayout

DEFAULT_ITERATIONS = 100
"""MCTS iterations per ply for untrained play: small enough that a batch of
games finishes in reasonable wall-clock time (the engine is weak either way)."""

DEFAULT_TEMPERATURE = 0.0
"""Greedy ply selection — take the most-visited child, no exploration noise."""


class NeuralCtfPlayer(AIPlayer[CtfPly, CtfPosition], CtfPlayer):
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

    def get_placement(self, side: Side, setup: GameSetup) -> Placement:
        """A random legal placement. Placement intelligence is out of scope for
        now."""
        return random_placement(side, setup, self._rng)


def build_neural_player(
    name: str,
    setup: GameSetup,
    *,
    network: CtfCrn | None = None,
    iterations: int = DEFAULT_ITERATIONS,
    temperature: float = DEFAULT_TEMPERATURE,
    rng: random.Random | None = None,
    render_before_ply: bool = False,
) -> NeuralCtfPlayer:
    """Construct a learned-engine player: `network` (a fresh untrained `CtfCrn` by
    default, or one loaded from a checkpoint) wrapped in the evaluator and an
    `MCTSEngine`, seated behind a `NeuralCtfPlayer`.

    `setup` is the board and army the seat is being filled for; it shapes the
    evaluator and, when one is not supplied, the network. A supplied `network`
    must have been built for the same setup, and is checked rather than trusted:
    `load_neural_player` is handed the same setup it loads the checkpoint against
    so the two agree by construction, but a caller wiring a network up by hand has
    no such guarantee, and the alternative to a named refusal here is a torch
    shape error from somewhere inside the forward pass.

    The engine is the timed subclass, so an ordinary batch of games measures the
    same search boundary self-play does; with no timing session active it behaves
    exactly as the plain engine."""
    tensor_layout = TensorLayout.for_setup(setup)
    if network is not None and network.tensor_layout != tensor_layout:
        raise ValueError(
            f"this network was built for "
            f"{network.tensor_layout.layout.layout_id} / "
            f"{network.tensor_layout.composition.composition_id}, but the seat is "
            f"being filled for {tensor_layout.layout.layout_id} / "
            f"{tensor_layout.composition.composition_id}"
        )
    engine: MCTSEngine[CtfPly, CtfPosition, CtfNNEvaluator] = TimedMCTSEngine(
        evaluator=CtfNNEvaluator(
            network if network is not None else CtfCrn(tensor_layout), tensor_layout
        ),
        iterations=iterations,
        temperature=temperature,
    )
    return NeuralCtfPlayer(engine, name, rng=rng, render_before_ply=render_before_ply)

"""Tests for the self-play MCTS engine factory.

`CtfEngineFactory` is the zero-arg `engine_factory` the shared
`SelfPlayCollector` calls once per game (story 00000009, Step 3): it must build a
fresh `MCTSEngine` over the configured evaluator, carrying the self-play search
budget and exploration temperature through to each engine it builds.
"""

from game_engine_core.engines.mcts_engine import MCTSEngine

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_engine_factory import CtfEngineFactory
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator


def _evaluator() -> CtfNNEvaluator:
    return CtfNNEvaluator(CtfCrn())


def test_call_builds_mcts_engine_over_the_configured_evaluator():
    evaluator = _evaluator()
    engine = CtfEngineFactory(evaluator)()

    assert isinstance(engine, MCTSEngine)
    # The same evaluator instance the collector encodes with is the one the
    # engine searches with — one evaluator, two consumers.
    assert engine.evaluator is evaluator


def test_iterations_and_temperature_propagate_to_the_engine():
    evaluator = _evaluator()
    engine = CtfEngineFactory(evaluator, iterations=42, temperature=0.7)()

    assert engine.iterations == 42
    # MCTSEngine stores the sampling temperature privately and exposes no public
    # accessor; read the pinned engine's field directly to confirm it was wired.
    assert engine._temperature == 0.7


def test_each_call_returns_a_fresh_engine():
    factory = CtfEngineFactory(_evaluator())

    # The collector builds one engine per game so each game starts from a clean
    # search tree; distinct instances per call are the contract that guarantees
    # no tree state bleeds between games.
    assert factory() is not factory()

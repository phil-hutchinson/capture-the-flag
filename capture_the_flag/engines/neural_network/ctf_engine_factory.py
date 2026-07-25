from game_engine_core.engines.mcts_engine import MCTSEngine

from ...instrumentation.timed_search import TimedMCTSEngine
from .ctf_nn_evaluator import CtfNNEvaluator


class CtfEngineFactory:
    def __init__(self, evaluator: CtfNNEvaluator, iterations: int = 800, temperature: float = 1.0):
        self.evaluator = evaluator
        self.iterations = iterations
        self.temperature = temperature

    def __call__(self) -> MCTSEngine:
        # Timed rather than plain: the call into search is the most expensive
        # thing self-play does, and the timing costs nothing when no session is
        # active. Behaviour is identical either way.
        return TimedMCTSEngine(self.evaluator, iterations = self.iterations, temperature = self.temperature)


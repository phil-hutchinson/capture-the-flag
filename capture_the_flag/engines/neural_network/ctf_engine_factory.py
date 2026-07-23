from game_engine_core.engines.mcts_engine import MCTSEngine

from .ctf_nn_evaluator import CtfNNEvaluator


class CtfEngineFactory:
    def __init__(self, evaluator: CtfNNEvaluator, iterations: int = 800, temperature: float = 1.0):
        self.evaluator = evaluator
        self.iterations = iterations
        self.temperature = temperature

    def __call__(self) -> MCTSEngine:
        return MCTSEngine(self.evaluator, iterations = self.iterations, temperature = self.temperature)


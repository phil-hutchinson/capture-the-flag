"""Bootstrap smoke test.

Confirms the package imports and that its pinned game-engine-core dependency
resolves inside the environment. Expand or replace as the real implementation
lands.
"""

from game_engine_core.evaluators.null_evaluator import NullEvaluator

from capture_the_flag import SIMPLE_64


def test_board_dimensions():
    assert SIMPLE_64.columns == 8
    assert SIMPLE_64.rows == 8


def test_game_engine_core_dependency_available():
    # The pinned game-engine-core dependency resolves and is importable.
    assert NullEvaluator() is not None

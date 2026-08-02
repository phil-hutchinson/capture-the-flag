"""Bootstrap smoke test.

Confirms the package imports and that its pinned game-engine-core dependency
resolves inside the environment. Expand or replace as the real implementation
lands.
"""

from game_engine_core.evaluators.null_evaluator import NullEvaluator

from capture_the_flag import STANDARD_144


def test_board_dimensions():
    assert STANDARD_144.columns == 12
    assert STANDARD_144.rows == 12


def test_lake_pattern_spans_the_board():
    assert len(STANDARD_144.lake_pattern) == STANDARD_144.columns
    # Three 2x2 lakes => six lake columns per lake row.
    assert sum(STANDARD_144.lake_pattern) == 6


def test_game_engine_core_dependency_available():
    # The pinned game-engine-core dependency resolves and is importable.
    assert NullEvaluator() is not None

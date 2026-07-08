"""Bootstrap smoke test.

Confirms the package imports and that its pinned game-engine-core dependency
resolves inside the environment. Expand or replace as the real implementation
lands.
"""

from game_engine_core.evaluators.null_evaluator import NullEvaluator

from capture_the_flag import BOARD_COLUMNS, BOARD_ROWS, LAKE_PATTERN


def test_board_dimensions():
    assert BOARD_COLUMNS == 12
    assert BOARD_ROWS == 12


def test_lake_pattern_spans_the_board():
    assert len(LAKE_PATTERN) == BOARD_COLUMNS
    # Three 2x2 lakes => six lake columns per lake row.
    assert sum(LAKE_PATTERN) == 6


def test_game_engine_core_dependency_available():
    # The pinned game-engine-core dependency resolves and is importable.
    assert NullEvaluator() is not None

"""Capture the Flag — a two-phase, perfect-information battlefield board game.

Phase 1 is secret simultaneous placement; phase 2 is alternating perfect-
information play. The game is built on the game-engine-core framework, consumed
as a pinned dependency.

This package is currently a bootstrap: it exposes the board geometry as the
first concrete brick. The GamePosition / GamePly implementations, evaluators,
and training code land in later stories.
"""

from .board import BOARD_COLUMNS, BOARD_ROWS, LAKE_PATTERN

__all__ = ["BOARD_COLUMNS", "BOARD_ROWS", "LAKE_PATTERN"]

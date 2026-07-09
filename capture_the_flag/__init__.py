"""Capture the Flag — a two-phase, perfect-information battlefield board game.

Phase 1 is secret simultaneous placement; phase 2 is alternating perfect-
information play. The game is built on the game-engine-core framework, consumed
as a pinned dependency.

This package currently exposes the domain primitives — board geometry and
piece data — that everything else (position state, move generation, combat)
builds on. The GamePosition / GamePly implementations, evaluators, and
training code land in later stories.
"""

from .board import (
    BLACK_HOME_SQUARES,
    BOARD_COLUMNS,
    BOARD_ROWS,
    LAKE_PATTERN,
    LAKE_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
    orthogonal_neighbors,
    parse_square,
    path_between,
)
from .pieces import ARMY_ROSTER, ARMY_SIZE, Mobility, PieceType

__all__ = [
    "ARMY_ROSTER",
    "ARMY_SIZE",
    "BLACK_HOME_SQUARES",
    "BOARD_COLUMNS",
    "BOARD_ROWS",
    "LAKE_PATTERN",
    "LAKE_SQUARES",
    "WHITE_HOME_SQUARES",
    "Mobility",
    "PieceType",
    "Square",
    "orthogonal_neighbors",
    "parse_square",
    "path_between",
]

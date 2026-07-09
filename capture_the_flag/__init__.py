"""Capture the Flag — a two-phase, perfect-information battlefield board game.

Phase 1 is secret simultaneous placement; phase 2 is alternating perfect-
information play. The game is built on the game-engine-core framework, consumed
as a pinned dependency.

This package currently exposes the domain primitives (board geometry, piece
data), the position state container with legal move generation, combat
resolution, and the placement seam that everything else (transitions,
endings) builds on. Evaluators and training code land in later stories.
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
from .combat import CombatResult, resolve_combat
from .pieces import ARMY_ROSTER, ARMY_SIZE, Mobility, PieceType
from .placement import Placement, assemble_position, random_placement
from .ply import CtfPly
from .position import BreachabilityCache, CtfPosition
from .rendering import render_position_block
from .side import Side

__all__ = [
    "ARMY_ROSTER",
    "ARMY_SIZE",
    "BLACK_HOME_SQUARES",
    "BOARD_COLUMNS",
    "BOARD_ROWS",
    "LAKE_PATTERN",
    "LAKE_SQUARES",
    "WHITE_HOME_SQUARES",
    "BreachabilityCache",
    "CombatResult",
    "CtfPly",
    "CtfPosition",
    "Mobility",
    "Placement",
    "PieceType",
    "Side",
    "Square",
    "assemble_position",
    "orthogonal_neighbors",
    "parse_square",
    "path_between",
    "random_placement",
    "render_position_block",
    "resolve_combat",
]

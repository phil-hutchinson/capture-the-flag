"""Capture the Flag — a two-phase, perfect-information battlefield board game.

Phase 1 is secret simultaneous placement; phase 2 is alternating perfect-
information play. The game is built on the game-engine-core framework, consumed
as a pinned dependency.

This package now exposes a fully playable, `game-engine-core`-compatible
`CtfPosition`: board geometry and piece data, legal move generation, combat
resolution, ply application (transitions, clocks, and the breachability
cache), endings (`outcome`), and the placement seam. Evaluators and training
code land in later stories.
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
from .breachability import BreachabilityCache
from .combat import CombatResult, resolve_combat
from .outcome import compute_outcome
from .pieces import ARMY_ROSTER, ARMY_SIZE, Mobility, PieceType
from .placement import Placement, assemble_position, random_placement
from .ply import CtfPly
from .position import CtfPosition
from .reachability import compute_breachability
from .rendering import render_position_block
from .side import Side
from .transitions import apply_ply

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
    "apply_ply",
    "assemble_position",
    "compute_breachability",
    "compute_outcome",
    "orthogonal_neighbors",
    "parse_square",
    "path_between",
    "random_placement",
    "render_position_block",
    "resolve_combat",
]

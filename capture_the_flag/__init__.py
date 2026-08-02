"""Capture the Flag — a two-phase, perfect-information battlefield board game.

Phase 1 is secret simultaneous placement; phase 2 is alternating perfect-
information play. The game is built on the game-engine-core framework, consumed
as a pinned dependency.

This package now exposes a fully playable, `game-engine-core`-compatible
`CtfPosition` (board geometry and piece data, legal move generation, combat
resolution, ply application, and endings), the placement seam (random,
file-based, or programmatic), a `CtfGameUI` with human move entry, random, human,
and learned (neural) players reachable through a `make_player` factory, and a
match wrapper that plays a complete game. Training code lands in later stories.
"""

from .board import (
    STANDARD_144,
    BoardLayout,
    Square,
    parse_square,
    path_between,
)
from .combat import CombatResult, resolve_combat
from .game_logging import CtfGameLogging
from .game_setup import BATTLE_SETUP, GameSetup, resolve_setup
from .game_ui import CtfGameUI
from .game_view import render_game_view
from .match import MatchResult, build_initial_position, play_match
from .outcome import compute_outcome, compute_outcome_reason
from .pieces import STANDARD_BATTLE, ArmyComposition, Mobility, PieceType
from .placement import Placement, assemble_position, random_placement
from .placement_file import (
    DEFAULT_PLACEMENT_DIR,
    PlacementFileError,
    load_placement_file,
    parse_placement_file,
)
from .player import (
    CtfPlayer,
    HumanCtfPlayer,
    PlayerContext,
    RandomCtfPlayer,
    make_player,
)
from .ply import CtfPly, parse_ply
from .position import CtfPosition
from .record import (
    ACTIVE_EDITIONS,
    DEFAULT_EDITION,
    RulesetConfiguration,
    active_configuration,
    write_record,
)
from .rendering import parse_position_block, render_position_block
from .side import Side
from .transitions import apply_ply

__all__ = [
    "ACTIVE_EDITIONS",
    "BATTLE_SETUP",
    "DEFAULT_EDITION",
    "DEFAULT_PLACEMENT_DIR",
    "STANDARD_144",
    "STANDARD_BATTLE",
    "ArmyComposition",
    "BoardLayout",
    "CombatResult",
    "CtfGameLogging",
    "CtfGameUI",
    "CtfPlayer",
    "CtfPly",
    "CtfPosition",
    "GameSetup",
    "HumanCtfPlayer",
    "MatchResult",
    "Mobility",
    "Placement",
    "PieceType",
    "PlacementFileError",
    "PlayerContext",
    "RandomCtfPlayer",
    "RulesetConfiguration",
    "Side",
    "Square",
    "active_configuration",
    "apply_ply",
    "assemble_position",
    "build_initial_position",
    "compute_outcome",
    "compute_outcome_reason",
    "load_placement_file",
    "make_player",
    "parse_placement_file",
    "parse_ply",
    "parse_position_block",
    "parse_square",
    "path_between",
    "play_match",
    "random_placement",
    "render_game_view",
    "render_position_block",
    "resolve_setup",
    "resolve_combat",
    "write_record",
]

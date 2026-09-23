"""Capture the Flag — a single-phase, perfect-information battlefield board
game.

Every game begins from a generated starting position, fully visible to both
players from the first move, and proceeds by alternating play until the game
ends. The game is built on the game-engine-core framework, consumed as a pinned
dependency.

This package exposes a fully playable, `game-engine-core`-compatible
`CtfPosition` (board geometry and piece data, legal move generation, combat
resolution, ply application, and endings), a `CtfGameUI` with human move entry,
random, human, and learned (neural) players reachable through a `make_player`
factory, and a match wrapper that plays a complete game. Training code lands in
later stories.
"""

from .board import (
    BOARD_LAYOUTS,
    SIMPLE_64,
    BoardLayout,
    Square,
    parse_square,
    path_between,
)
from .combat import CombatResult, resolve_combat
from .game_logging import CtfGameLogging
from .game_setup import PRE_RELEASE_SETUP, GameSetup, resolve_setup, setup_for_ruleset
from .game_ui import CtfGameUI
from .game_view import render_game_view
from .match import MatchResult, build_initial_position, play_match
from .outcome import compute_outcome, compute_outcome_reason
from .pieces import (
    ARMY_COMPOSITIONS,
    STANDARD_ARMY,
    ArmyComposition,
    Mobility,
    PieceType,
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
from .start_position import (
    decode_position_id,
    generate_start_position,
    mirror_of,
    position_id,
    strength_threshold,
)
from .transitions import apply_ply

__all__ = [
    "ACTIVE_EDITIONS",
    "ARMY_COMPOSITIONS",
    "BOARD_LAYOUTS",
    "DEFAULT_EDITION",
    "PRE_RELEASE_SETUP",
    "SIMPLE_64",
    "STANDARD_ARMY",
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
    "PieceType",
    "PlayerContext",
    "RandomCtfPlayer",
    "RulesetConfiguration",
    "Side",
    "Square",
    "active_configuration",
    "apply_ply",
    "build_initial_position",
    "compute_outcome",
    "compute_outcome_reason",
    "decode_position_id",
    "generate_start_position",
    "make_player",
    "mirror_of",
    "parse_ply",
    "parse_position_block",
    "parse_square",
    "path_between",
    "play_match",
    "position_id",
    "render_game_view",
    "render_position_block",
    "resolve_combat",
    "resolve_setup",
    "setup_for_ruleset",
    "strength_threshold",
    "write_record",
]

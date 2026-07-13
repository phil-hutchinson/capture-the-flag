"""The match wrapper: phase-1 placement followed by phase-2 play.

Phase-1 placement has no equivalent in `game-engine-core` (a generic pre-play
step is one of the documented upstream requirements), so this wrapper
obtains both placements, assembles the starting `CtfPosition` via the
placement seam, and then hands phase-2 play to the library's unmodified
`StandardGame`.
"""

from dataclasses import dataclass
from typing import Literal

from game_engine_core.game.standard_game import StandardGame
from game_engine_core.models.game_result import GameResult
from game_engine_core.protocols.player import Player

from .game_logging import CtfGameLogging
from .game_ui import CtfGameUI
from .placement import Placement, assemble_position
from .player import CtfPlayer
from .ply import CtfPly
from .position import CtfPosition
from .side import Side


@dataclass(frozen=True)
class MatchResult:
    """A completed match: both placements plus the phase-2 `GameResult`."""

    white_placement: Placement
    black_placement: Placement
    game_result: GameResult


def play_match(
    white_player: CtfPlayer,
    black_player: CtfPlayer,
    game_ui: CtfGameUI | None = None,
    render_final_board: bool = True,
) -> MatchResult:
    """Play one complete match between `white_player` and `black_player`.

    `game_ui` is optional interactive display: pass `None` (the default) for
    headless play. Since v0.1.1, board rendering — including `render_final_board`
    — happens only when a `game_ui` is supplied; the game record is always fed by
    `CtfGameLogging` independently of the UI.
    """
    white_placement = white_player.get_placement(Side.WHITE)
    black_placement = black_player.get_placement(Side.BLACK)
    initial_position = assemble_position(white_placement, black_placement)

    players: dict[Literal[1, -1], Player[CtfPly, CtfPosition]] = {
        1: white_player,
        -1: black_player,
    }
    game = StandardGame(
        initial_position=initial_position,
        players=players,
        game_logging=CtfGameLogging(),
        game_ui=game_ui,
        render_final_board=render_final_board,
    )
    game_result = game.run()

    return MatchResult(
        white_placement=white_placement,
        black_placement=black_placement,
        game_result=game_result,
    )

"""The match wrapper: builds the starting position and plays a complete game.

`play_match` is the single-game helper: it builds the starting `CtfPosition`
and hands play to the library's `StandardGame`. `build_initial_position` is the
same start-position seam in the shape of `game-engine-core`'s tournament
`position_factory`, so batch and tournament runs get it through the library's
own runner.
"""

import random
from dataclasses import dataclass
from typing import Literal

from game_engine_core.game.standard_game import StandardGame
from game_engine_core.models.game_result import GameResult
from game_engine_core.protocols.player import Player

from .game_logging import CtfGameLogging
from .game_setup import GameSetup
from .game_ui import CtfGameUI
from .instrumentation.timing import region
from .player import CtfPlayer
from .ply import CtfPly
from .position import CtfPosition
from .start_position import generate_start_position
from .timing_regions import STARTING_POSITION


@dataclass(frozen=True)
class MatchResult:
    """A completed match: the `GameResult` from playing it out."""

    game_result: GameResult


def build_initial_position(
    _side_one: Player[CtfPly, CtfPosition],
    _side_other: Player[CtfPly, CtfPosition],
    setup: GameSetup,
    start_position: CtfPosition | None = None,
    rng: random.Random | None = None,
) -> CtfPosition:
    """`Capture the Flag`'s `position_factory` for the shared `Tournament`,
    matching game-engine-core v0.1.1's widened contract: the runner calls it once
    per game with the participants in side order, with the within-pairing
    alternation already applied.

    There is no placement phase to draw the position from (`rules.md` Section
    3), so the players themselves play no part in building it; the parameters
    exist only to satisfy the library's two-player `position_factory` contract.

    `start_position`, when given, is returned for every game the factory is
    asked for -- a whole batch replaying the one position named on the command
    line. Otherwise each call draws a fresh position from `rng` (a caller
    seeding it gets the same sequence of starting positions each time; defaults
    to a fresh `random.Random()` otherwise), matching `CtfPositionFactory`'s
    self-play seam.

    `setup` says which board and army are being played. The library's
    `position_factory` contract fixes the two-player signature, so a caller binds
    the setup ahead of time (`functools.partial`) rather than passing it per game
    — every game in a run is played under one setup.
    """
    # Timed: the shared runner plays a whole batch inside one call, so this
    # callback — invoked once per game — is where a timing report gets its
    # per-game structure from.
    with region(STARTING_POSITION):
        if start_position is not None:
            return start_position
        return generate_start_position(setup, rng)


def play_match(
    white_player: CtfPlayer,
    black_player: CtfPlayer,
    setup: GameSetup,
    start_position: CtfPosition | None = None,
    game_ui: CtfGameUI | None = None,
    render_final_board: bool = True,
) -> MatchResult:
    """Play one complete match between `white_player` and `black_player`.

    `start_position`, when given, is played as-is instead of a freshly
    generated one -- a caller (the single-game runner) resolves it up front,
    from a `--start-position` ID or a seeded draw, so it can announce the ID
    before play begins.

    `game_ui` is optional interactive display: pass `None` (the default) for
    headless play. Since v0.1.1, board rendering — including `render_final_board`
    — happens only when a `game_ui` is supplied; the game record is always fed by
    `CtfGameLogging` independently of the UI.
    """
    initial_position = (
        start_position if start_position is not None else generate_start_position(setup)
    )

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

    return MatchResult(game_result=game_result)

"""The match wrapper: builds the starting position and plays a complete game.

`play_match` is the single-game helper: it builds the starting `CtfPosition`
and hands play to the library's `StandardGame`. `build_initial_position` is the
same start-position seam in the shape of `game-engine-core`'s tournament
`position_factory`, so batch and tournament runs get it through the library's
own runner.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from game_engine_core.game.standard_game import StandardGame
from game_engine_core.models.game_result import GameResult
from game_engine_core.protocols.player import Player

from .board import Square
from .game_logging import CtfGameLogging
from .game_setup import GameSetup
from .game_ui import CtfGameUI
from .instrumentation.timing import region
from .pieces import PieceType
from .player import CtfPlayer
from .ply import CtfPly
from .position import CtfPosition
from .side import Side
from .timing_regions import STARTING_POSITION

_STUB_WHITE_ROW_1: tuple[PieceType, ...] = (
    PieceType.FLAG,
    PieceType.MILITIA,
    PieceType.MILITIA,
    PieceType.FOOT_SOLDIER,
    PieceType.FOOT_SOLDIER,
    PieceType.CHAMPION,
    PieceType.CHAMPION,
    PieceType.CHAMPION,
)
_STUB_WHITE_ROW_2: tuple[PieceType, ...] = (
    PieceType.PEASANT,
    PieceType.PEASANT,
    PieceType.PEASANT,
    PieceType.MILITIA,
    PieceType.FOOT_SOLDIER,
    PieceType.MASTER_OF_ARMS,
    PieceType.MASTER_OF_ARMS,
    PieceType.MASTER_OF_ARMS,
)
"""White's fixed row 1 and row 2, columns A-H. A placeholder for real generation
(`start-position.md` Sections 2-3, implemented in stories 00000049 steps 7-8):
the Flag on row 1, and the seven numbered pieces in its half (B1-D1, A2-D2)
summing to 12 — comfortably under the strength rule's 21 threshold, so this is
an arrangement uniform generation could itself have produced rather than merely
a legal-looking board. Black's half is this arrangement reflected top-to-bottom
(`start-position.md` Section 3's reflection branch, which is what a Flag on the
weak half always selects)."""


@dataclass(frozen=True)
class MatchResult:
    """A completed match: the phase-2 `GameResult`."""

    game_result: GameResult


def stub_start_position(setup: GameSetup) -> CtfPosition:
    """The fixed starting position every match begins from, standing in for
    `start-position.md`'s generated one until stories 00000049 steps 7-8 land.

    Fixed to the one board and army this build plays: an 8-wide, two-home-row
    layout and the 16-piece army, asserted here so a future setup this stub was
    never built for fails loudly rather than silently misdealing pieces.
    """
    assert setup.layout.columns == 8 and setup.layout.rows == 8, (
        f"the stub start position is fixed for an 8x8 board; "
        f"{setup.layout.layout_id} is not one"
    )
    assert setup.layout.home_rows == 2, (
        f"the stub start position is fixed for two home rows; "
        f"{setup.layout.layout_id} has {setup.layout.home_rows}"
    )
    assert setup.composition.size == 16, (
        f"the stub start position is fixed for the 16-piece army; "
        f"{setup.composition.composition_id} has {setup.composition.size}"
    )

    board: dict[Square, tuple[Side, PieceType]] = {}
    for column in range(8):
        board[Square(column, 1)] = (Side.WHITE, _STUB_WHITE_ROW_1[column])
        board[Square(column, 2)] = (Side.WHITE, _STUB_WHITE_ROW_2[column])
        # Reflection: column unchanged, row r -> rows + 1 - r.
        board[Square(column, 8)] = (Side.BLACK, _STUB_WHITE_ROW_1[column])
        board[Square(column, 7)] = (Side.BLACK, _STUB_WHITE_ROW_2[column])

    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=setup.layout,
    )


def build_initial_position(
    _side_one: Player[CtfPly, CtfPosition],
    _side_other: Player[CtfPly, CtfPosition],
    setup: GameSetup,
) -> CtfPosition:
    """`Capture the Flag`'s `position_factory` for the shared `Tournament`,
    matching game-engine-core v0.1.1's widened contract: the runner calls it once
    per game with the participants in side order, with the within-pairing
    alternation already applied.

    There is no placement phase to draw the position from (`rules.md` Section
    3), so the players themselves play no part in building it; the parameters
    exist only to satisfy the library's two-player `position_factory` contract.

    `setup` says which board and army are being played. The library's
    `position_factory` contract fixes the two-player signature, so a caller binds
    the setup ahead of time (`functools.partial`) rather than passing it per game
    — every game in a run is played under one setup.
    """
    # Timed: the shared runner plays a whole batch inside one call, so this
    # callback — invoked once per game — is where a timing report gets its
    # per-game structure from.
    with region(STARTING_POSITION):
        return stub_start_position(setup)


def play_match(
    white_player: CtfPlayer,
    black_player: CtfPlayer,
    setup: GameSetup,
    game_ui: CtfGameUI | None = None,
    render_final_board: bool = True,
) -> MatchResult:
    """Play one complete match between `white_player` and `black_player`.

    `game_ui` is optional interactive display: pass `None` (the default) for
    headless play. Since v0.1.1, board rendering — including `render_final_board`
    — happens only when a `game_ui` is supplied; the game record is always fed by
    `CtfGameLogging` independently of the UI.
    """
    initial_position = stub_start_position(setup)

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

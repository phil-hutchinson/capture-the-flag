"""Game endings (rules.md Section 6).

`outcome` is current-player-relative: `1` (active player wins), `0` (draw),
`-1` (active player loses), or `None` (ongoing). Conditions are checked in
the rulebook's own section order (6.1-6.5): Flag capture, the Unbreachable
Flag, no legal move, inactivity, no progress.
"""

from typing import TYPE_CHECKING, Literal

from .pieces import PieceType
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition

INACTIVITY_LIMIT = 50
PROGRESS_LIMIT = 80


def _has_flag(position: "CtfPosition", side: Side) -> bool:
    return any(
        piece_side is side and piece is PieceType.FLAG
        for piece_side, piece in position.board.values()
    )


def compute_outcome(position: "CtfPosition") -> Literal[1, 0, -1] | None:
    active = position.side_to_move
    opponent = active.opponent

    # 6.1 Win -- Flag capture.
    if not _has_flag(position, active):
        return -1
    if not _has_flag(position, opponent):
        return 1

    # 6.2 Win -- Unbreachable Flag.
    cache = position.breachability
    if cache is not None:
        white_wins = cache.white_flag_enclosed and not cache.black_sappers_available
        black_wins = cache.black_flag_enclosed and not cache.white_sappers_available
        if white_wins and black_wins:
            return 0
        if white_wins:
            return 1 if active is Side.WHITE else -1
        if black_wins:
            return 1 if active is Side.BLACK else -1

    # 6.3 Loss -- no legal move.
    if not position.legal_plies:
        return -1

    # 6.4 Loss -- inactivity.
    active_counter = (
        position.white_inactivity_counter
        if active is Side.WHITE
        else position.black_inactivity_counter
    )
    opponent_counter = (
        position.white_inactivity_counter
        if opponent is Side.WHITE
        else position.black_inactivity_counter
    )
    if active_counter >= INACTIVITY_LIMIT:
        return -1
    if opponent_counter >= INACTIVITY_LIMIT:
        return 1

    # 6.5 Draw -- no progress.
    if position.progress_counter >= PROGRESS_LIMIT:
        return 0

    return None

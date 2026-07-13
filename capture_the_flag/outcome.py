"""Game endings (rules.md Section 6).

`outcome` is current-player-relative: `1` (active player wins), `0` (draw),
`-1` (active player loses), or `None` (ongoing). Conditions follow the
rulebook's section order (6.1 Flag capture, 6.2 Unbreachable Flag, ...) with
one deliberate deviation: the conditions decided by the opponent's
just-completed ply -- their inactivity loss (6.4) and the shared no-progress
draw (6.5) -- are checked *before* the active player's no-legal-move loss
(6.3), because the game ends the moment the opponent's ply meets them, before
the active player is asked to move. See `compute_outcome` for the rationale.
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


# Reason vocabulary reported through `GamePosition.outcome_reason` and recorded
# in game-record files (`doc/ruleset/technical-notes.md`). One label per rulebook
# ending; both the win and draw variants of the Unbreachable Flag ending share the
# single label, since the record's outcome field already distinguishes them.
REASON_FLAG_CAPTURED = "Flag Captured"
REASON_UNBREACHABLE_FLAG = "Unbreachable Flag"
REASON_INACTIVITY = "Inactivity"
REASON_NO_PROGRESS = "No Progress"
REASON_NO_LEGAL_MOVE = "No Legal Move"


def compute_outcome(position: "CtfPosition") -> Literal[1, 0, -1] | None:
    """Current-player-relative outcome (rules.md Section 6), or `None` if ongoing."""
    return _evaluate(position)[0]


def compute_outcome_reason(position: "CtfPosition") -> str | None:
    """The reason label for a terminal position, or `None` while the game is ongoing.

    Shares its branch logic with `compute_outcome` (see `_evaluate`) so the outcome
    and its stated reason can never disagree.
    """
    return _evaluate(position)[1]


def _evaluate(
    position: "CtfPosition",
) -> tuple[Literal[1, 0, -1] | None, str | None]:
    """Decide the game's ending once, returning both the outcome and its reason.

    Single source of truth for `compute_outcome`/`compute_outcome_reason`: every
    terminal branch yields the outcome paired with the reason that produced it.
    """
    active = position.side_to_move
    opponent = active.opponent

    # 6.1 Win -- Flag capture.
    if not _has_flag(position, active):
        return -1, REASON_FLAG_CAPTURED
    if not _has_flag(position, opponent):
        return 1, REASON_FLAG_CAPTURED

    # 6.2 Win -- Unbreachable Flag.
    cache = position.breachability
    if cache is not None:
        white_wins = cache.white_flag_enclosed and not cache.black_sappers_available
        black_wins = cache.black_flag_enclosed and not cache.white_sappers_available
        if white_wins and black_wins:
            return 0, REASON_UNBREACHABLE_FLAG
        if white_wins:
            return (1 if active is Side.WHITE else -1), REASON_UNBREACHABLE_FLAG
        if black_wins:
            return (1 if active is Side.BLACK else -1), REASON_UNBREACHABLE_FLAG

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

    # Conditions attributable to the opponent's just-completed ply end the game
    # "the moment [they are] met" (rules.md Section 6) -- before the active
    # player is asked to move -- so they precede the active player's
    # no-legal-move loss (6.3). The opponent's inactivity loss (6.4) and the
    # shared no-progress draw (6.5) are both such previous-ply conditions; the
    # rulebook lists 6.4 before 6.5, so a single non-attack ply that trips both
    # (it raises inactivity *and* progress) resolves as the opponent's loss.
    if opponent_counter >= INACTIVITY_LIMIT:
        return 1, REASON_INACTIVITY
    if position.progress_counter >= PROGRESS_LIMIT:
        return 0, REASON_NO_PROGRESS

    # 6.3 Loss -- no legal move.
    if not position.legal_plies:
        return -1, REASON_NO_LEGAL_MOVE

    # 6.4 Loss -- inactivity (the active player's own counter). Unreachable
    # under normal play -- that counter only advances on the active player's
    # own plies, so it would have ended the game at the close of the previous
    # active turn -- but kept for completeness/defence.
    if active_counter >= INACTIVITY_LIMIT:
        return -1, REASON_INACTIVITY

    return None, None

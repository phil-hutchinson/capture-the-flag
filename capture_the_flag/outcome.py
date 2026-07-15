"""Game endings (rules.md Section 5).

`outcome` is current-player-relative: `1` (active player wins), `0` (draw),
`-1` (active player loses), or `None` (ongoing). Conditions follow the rulebook's
section order (5.1 Flag capture, 5.2 No legal move, 5.3 Inactivity draw) with one
deliberate deviation: the inactivity draw (5.3) is checked *before* the active
player's no-legal-move loss (5.2), because the shared counter reaches its limit at
the close of the opponent's just-completed ply -- the moment the draw is met --
before the active player is asked to move. See `_evaluate` for the rationale.
"""

from typing import TYPE_CHECKING, Literal

from .pieces import PieceType
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition

INACTIVITY_LIMIT = 50


def _has_flag(position: "CtfPosition", side: Side) -> bool:
    return any(
        piece_side is side and piece is PieceType.FLAG
        for piece_side, piece in position.board.values()
    )


# Reason vocabulary reported through `GamePosition.outcome_reason` and recorded
# in game-record files (`doc/ruleset/technical-notes.md`). One label per rulebook
# ending.
REASON_FLAG_CAPTURED = "Flag Captured"
REASON_INACTIVITY = "Inactivity"
REASON_NO_LEGAL_MOVE = "No Legal Move"


def compute_outcome(position: "CtfPosition") -> Literal[1, 0, -1] | None:
    """Current-player-relative outcome (rules.md Section 5), or `None` if ongoing."""
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

    # 5.1 Win -- Flag capture.
    if not _has_flag(position, active):
        return -1, REASON_FLAG_CAPTURED
    if not _has_flag(position, opponent):
        return 1, REASON_FLAG_CAPTURED

    # 5.3 Draw -- Inactivity. The shared counter reaches its limit on the
    # opponent's just-completed ply, so the game ends "the moment [it is] met"
    # (rules.md Section 5) -- before the active player is asked to move -- and it
    # therefore precedes the active player's no-legal-move loss (5.2).
    if position.inactivity_counter >= INACTIVITY_LIMIT:
        return 0, REASON_INACTIVITY

    # 5.2 Loss -- no legal move.
    if not position.legal_plies:
        return -1, REASON_NO_LEGAL_MOVE

    return None, None

"""Game endings (rules.md Section 5).

`outcome` is current-player-relative: `1` (active player wins), `0` (draw),
`-1` (active player loses), or `None` (ongoing). Conditions follow the
rulebook's section order: 5.1 Flag capture, 5.2 Attrition, 5.3 Mutual
attrition, 5.4 Inactivity draw -- except that mutual attrition (both players
left with no numbered pieces) is tested *before* the single-sided attrition
check it would otherwise satisfy first. See `_evaluate`.
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


def _has_army(position: "CtfPosition", side: Side) -> bool:
    """Whether `side` holds any numbered piece (rules.md Section 5.2,
    Attrition). The Flag does not count: a player holding nothing but their
    Flag has no army."""
    return any(
        piece_side is side and piece.rank is not None
        for piece_side, piece in position.board.values()
    )


# Reason vocabulary reported through `GamePosition.outcome_reason` and recorded
# in game-record files (`doc/ruleset/technical-notes.md`). One label per rulebook
# ending.
REASON_FLAG_CAPTURED = "Flag Captured"
REASON_ATTRITION = "Attrition"
REASON_MUTUAL_ATTRITION = "Mutual Attrition"
REASON_INACTIVITY = "Inactivity"


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

    active_has_army = _has_army(position, active)
    opponent_has_army = _has_army(position, opponent)

    # 5.3 Draw -- Mutual attrition. Tested before the single-sided case below:
    # a single ply that empties both armies at once (a trade of each side's
    # last piece) is a draw, not a win for whichever side happens to be
    # "active" next.
    if not active_has_army and not opponent_has_army:
        return 0, REASON_MUTUAL_ATTRITION

    # 5.2 Loss -- Attrition.
    if not active_has_army:
        return -1, REASON_ATTRITION
    if not opponent_has_army:
        return 1, REASON_ATTRITION

    # 5.4 Draw -- Inactivity.
    if position.inactivity_counter >= INACTIVITY_LIMIT:
        return 0, REASON_INACTIVITY

    # No stalemate can arise under this ruleset: a player who still has an
    # army always has a legal move. Kept as an assertion, not an ending --
    # story 00000049 step 16 replaces the former No Legal Move ending with
    # attrition above.
    assert position.legal_plies, "a player with an army always has a legal move"
    return None, None

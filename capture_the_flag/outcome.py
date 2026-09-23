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

INACTIVITY_LIMIT = 40


def _survey(position: "CtfPosition") -> tuple[bool, bool, bool, bool]:
    """Whether each side holds a Flag and whether it holds an army, in one
    pass: `(White flag, White army, Black flag, Black army)`.

    One pass rather than a predicate per question, because `outcome` is the
    pipeline's most-called seam and Section 5 needs all four answers for every
    position the first of them does not decide. Measured over 6,062 positions
    from 30 random games, against the four short-circuiting scans this
    replaced: 13.5ms to 3.3ms.

    Flat locals and a positional result rather than a mapping keyed by side:
    an earlier version accumulating into a `dict[Side, tuple[bool, bool]]` was
    *slower* than the four scans it replaced, since a dict read plus a tuple
    allocation per piece costs more than the scanning did. The early return
    matters for the same reason -- the answer is usually settled within a few
    pieces, and the full walk is what made the one-pass version lose.

    "Army" excludes the Flag, which is what Section 5.2 means by attrition: a
    player holding nothing but their Flag has no army.
    """
    white_flag = white_army = black_flag = black_army = False
    for piece_side, piece in position.board.values():
        if piece_side is Side.WHITE:
            if piece is PieceType.FLAG:
                white_flag = True
            elif piece.rank is not None:
                white_army = True
        else:
            if piece is PieceType.FLAG:
                black_flag = True
            elif piece.rank is not None:
                black_army = True
        if white_flag and white_army and black_flag and black_army:
            return True, True, True, True
    return white_flag, white_army, black_flag, black_army


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
    white_flag, white_army, black_flag, black_army = _survey(position)
    if position.side_to_move is Side.WHITE:
        active_has_flag, active_has_army = white_flag, white_army
        opponent_has_flag, opponent_has_army = black_flag, black_army
    else:
        active_has_flag, active_has_army = black_flag, black_army
        opponent_has_flag, opponent_has_army = white_flag, white_army

    # 5.1 Win -- Flag capture.
    if not active_has_flag:
        return -1, REASON_FLAG_CAPTURED
    if not opponent_has_flag:
        return 1, REASON_FLAG_CAPTURED

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

    # Nothing left to test: a player who still has an army always has a legal
    # ply, so there is no ending here for the "no legal move" case major 2 lost
    # the game for. Step 16 of story 00000049 replaced it with the attrition
    # check above, and `technical-notes.md` ("Attrition replaced 'no legal
    # move'") proves the boxed-in state unreachable on a lake-free board --
    # every numbered piece stuck would need the occupied set's whole on-board
    # boundary held by friendly non-numbered pieces, and there is one of those.
    #
    # Deliberately not asserted: the assertion would have to rebuild the ply
    # set on every non-terminal evaluation to re-check a published proof, which
    # measured at roughly half of engine runtime. Anyone reintroducing
    # impassable terrain restores the ending, not the assertion.
    return None, None

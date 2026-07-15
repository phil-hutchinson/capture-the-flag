"""Combat resolution for Capture the Flag (rules.md Section 4.3).

Pure rules over `(position, attacker square, defender square)`: the pieces on
each square determine rank, and the board context determines the special cases
-- Flag capture (always an attacker win), Tower attacks (always a mutual loss),
and the formation bonus, under which a piece with a friendly equal-rank piece
within one square draws against a piece one rank higher instead of losing.
Legality of the attack itself is a move-generation concern (see `moves.py`);
this module only decides the *result* of an attack already determined legal.
"""

from enum import Enum
from typing import TYPE_CHECKING

from .board import Square
from .pieces import PieceType
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition


class CombatResult(Enum):
    ATTACKER_WINS = "attacker_wins"
    ATTACKER_LOSES = "attacker_loses"
    MUTUAL_LOSS = "mutual_loss"


# The eight squares surrounding a square (orthogonal and diagonal): the
# neighbourhood used for the formation bonus (rules.md Section 4.3).
_SURROUNDING = tuple(
    (dc, dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)
)


def _has_formation_bonus(
    position: "CtfPosition", square: Square, side: Side, rank: int
) -> bool:
    """Whether a friendly piece of the same `rank` stands within one square of
    `square` (rules.md Section 4.3, formation bonus).

    Off-board and empty neighbours simply have no occupant in `position.board`,
    so they contribute nothing without separate handling.
    """
    for dc, dr in _SURROUNDING:
        occupant = position.board.get(Square(square.column + dc, square.row + dr))
        if occupant is None:
            continue
        occupant_side, occupant_piece = occupant
        if occupant_side is side and occupant_piece.rank == rank:
            return True
    return False


def resolve_combat(
    position: "CtfPosition", attacker: Square, defender: Square
) -> CombatResult:
    """Resolve an attack from `attacker` onto `defender` in `position`.

    Assumes `attacker` and `defender` are a legal attack (see `moves.py`):
    orthogonally in line and occupied by opposing sides. The attacker is always
    a mobile, numbered piece (Towers and the Flag never attack).
    """
    attacker_side, attacker_piece = position.board[attacker]
    defender_side, defender_piece = position.board[defender]

    # Capturing the Flag is an immediate win; attacking a Tower is a mutual loss
    # regardless of the attacker's rank (rules.md Section 4.3).
    if defender_piece is PieceType.FLAG:
        return CombatResult.ATTACKER_WINS
    if defender_piece is PieceType.TOWER:
        return CombatResult.MUTUAL_LOSS

    attacker_rank = attacker_piece.rank
    defender_rank = defender_piece.rank
    assert attacker_rank is not None, "a Tower or Flag cannot attack"
    assert defender_rank is not None, "Tower/Flag defenders are handled above"

    # Equal rank is always a draw; the formation bonus only ever rescues the
    # weaker piece in a one-rank mismatch, so it cannot change this outcome.
    if attacker_rank == defender_rank:
        return CombatResult.MUTUAL_LOSS

    if attacker_rank < defender_rank:
        # The attacker is stronger. The defender loses unless it is exactly one
        # rank weaker and has the formation bonus, which turns its loss into a
        # draw (both removed).
        if defender_rank == attacker_rank + 1 and _has_formation_bonus(
            position, defender, defender_side, defender_rank
        ):
            return CombatResult.MUTUAL_LOSS
        return CombatResult.ATTACKER_WINS

    # The attacker is weaker. It loses unless it is exactly one rank weaker and
    # has the formation bonus, checked at its pre-move square.
    if attacker_rank == defender_rank + 1 and _has_formation_bonus(
        position, attacker, attacker_side, attacker_rank
    ):
        return CombatResult.MUTUAL_LOSS
    return CombatResult.ATTACKER_LOSES

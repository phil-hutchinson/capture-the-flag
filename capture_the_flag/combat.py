"""Combat resolution for Capture the Flag (rules.md Section 4.3).

Pure rules over `(position, attacker square, defender square)`: the pieces on
each square determine rank, and the board context determines the special
cases -- Flag capture, Sapper vs. Tower (and the non-Sapper complete
sacrifice), the Assassin (offense and defense, including the Assassin-vs-
Assassin and Assassin-vs-Tower exceptions), the Knight-vs-Knight charge
exception, and the Archer's defensive support. Legality of the attack itself
is a move-generation concern (see `moves.py`); this module only decides the
*result* of an attack that has already been determined to be legal.
"""

from enum import Enum
from typing import TYPE_CHECKING

from .board import Square, path_between
from .pieces import PieceType
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition


class CombatResult(Enum):
    ATTACKER_WINS = "attacker_wins"
    ATTACKER_LOSES = "attacker_loses"
    MUTUAL_LOSS = "mutual_loss"


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _attack_direction(attacker: Square, defender: Square) -> tuple[int, int]:
    return (
        _sign(defender.column - attacker.column),
        _sign(defender.row - attacker.row),
    )


def _has_archer_support(
    position: "CtfPosition",
    attacker: Square,
    defender: Square,
    defender_side: Side,
) -> bool:
    """Whether a friendly Archer stands one square beyond `defender`, along
    the exact line `attacker` traveled (rules.md Section 4.3, Archer support).

    A trigger square that is off-board, a lake, or otherwise unoccupied has
    no occupant in `position.board`, so it naturally yields no support
    without needing separate handling.
    """
    dc, dr = _attack_direction(attacker, defender)
    trigger = Square(defender.column + dc, defender.row + dr)
    occupant = position.board.get(trigger)
    if occupant is None:
        return False
    side, piece = occupant
    return side is defender_side and piece is PieceType.ARCHER


def resolve_combat(
    position: "CtfPosition", attacker: Square, defender: Square
) -> CombatResult:
    """Resolve an attack from `attacker` onto `defender` in `position`.

    Assumes `attacker` and `defender` are a legal attack (see `moves.py`):
    the two squares are collinear, and `attacker`/`defender` are occupied by
    opposing sides.
    """
    _attacker_side, attacker_piece = position.board[attacker]
    defender_side, defender_piece = position.board[defender]

    if defender_piece is PieceType.FLAG:
        base_result = CombatResult.ATTACKER_WINS
    elif defender_piece is PieceType.TOWER:
        base_result = (
            CombatResult.ATTACKER_WINS
            if attacker_piece is PieceType.SAPPER
            else CombatResult.ATTACKER_LOSES
        )
    elif attacker_piece is PieceType.ASSASSIN:
        base_result = CombatResult.ATTACKER_WINS
    elif defender_piece is PieceType.ASSASSIN:
        base_result = CombatResult.ATTACKER_WINS
    else:
        path = path_between(attacker, defender)
        assert path is not None, "combat resolution requires collinear squares"
        distance = len(path) + 1
        if (
            attacker_piece is PieceType.KNIGHT
            and defender_piece is PieceType.KNIGHT
            and distance >= 2
        ):
            base_result = CombatResult.ATTACKER_WINS
        else:
            attacker_rank = attacker_piece.rank
            defender_rank = defender_piece.rank
            assert attacker_rank is not None
            assert defender_rank is not None
            if attacker_rank < defender_rank:
                base_result = CombatResult.ATTACKER_WINS
            elif attacker_rank > defender_rank:
                base_result = CombatResult.ATTACKER_LOSES
            else:
                base_result = CombatResult.MUTUAL_LOSS

    if base_result is CombatResult.ATTACKER_WINS and _has_archer_support(
        position, attacker, defender, defender_side
    ):
        return CombatResult.MUTUAL_LOSS
    return base_result

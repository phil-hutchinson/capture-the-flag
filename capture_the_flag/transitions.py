"""Ply application: board transitions and the inactivity clock
(rules.md Sections 4.3, 5.3).
"""

from types import MappingProxyType

from .combat import CombatResult, resolve_combat
from .ply import CtfPly
from .position import CtfPosition


def apply_ply(position: CtfPosition, ply: CtfPly) -> CtfPosition:
    """The successor position after applying `ply` to `position`."""
    mover = position.side_to_move
    opponent = mover.opponent

    destination_occupant = position.board.get(ply.destination)
    is_attack = destination_occupant is not None
    result = (
        resolve_combat(position, ply.source, ply.destination) if is_attack else None
    )

    new_board = dict(position.board)
    mover_side, mover_piece = new_board.pop(ply.source)

    if not is_attack:
        new_board[ply.destination] = (mover_side, mover_piece)
    elif result is CombatResult.ATTACKER_WINS:
        new_board[ply.destination] = (mover_side, mover_piece)
    elif result is CombatResult.ATTACKER_LOSES:
        # The defender survives untouched at the destination.
        pass
    else:
        assert result is CombatResult.MUTUAL_LOSS
        del new_board[ply.destination]

    # Inactivity clock (Section 5.3): every attack removes at least one piece --
    # a winning attack the defender, a complete sacrifice the attacker, a mutual
    # loss (including tower destruction) both -- so any attack resets the shared
    # counter, and every non-attacking ply raises it by 1.
    new_inactivity_counter = 0 if is_attack else position.inactivity_counter + 1

    return CtfPosition(
        board=MappingProxyType(new_board),
        side_to_move=opponent,
        inactivity_counter=new_inactivity_counter,
    )

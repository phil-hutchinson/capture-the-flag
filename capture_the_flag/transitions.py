"""Ply application: board transitions, rank reduction, and the inactivity
clock (rules.md Section 4.3, "Rank reduction" and Section 5.4).

`resolve_combat` (see `combat.py`) only decides who survives; reducing the
survivor by one rank happens here, as the board is rebuilt.
"""

from types import MappingProxyType

from .combat import CombatResult, resolve_combat
from .pieces import PieceType
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
        # Capturing the Flag is not combat, so it reduces nothing (rules.md
        # Section 4.3); otherwise the attacker survives and is reduced.
        _, defender_piece = destination_occupant
        winner = (
            mover_piece
            if defender_piece is PieceType.FLAG
            else mover_piece.reduced()
        )
        new_board[ply.destination] = (mover_side, winner)
    elif result is CombatResult.ATTACKER_LOSES:
        # The defender survives, reduced by one rank.
        defender_side, defender_piece = destination_occupant
        new_board[ply.destination] = (defender_side, defender_piece.reduced())
    else:
        assert result is CombatResult.MUTUAL_LOSS
        # A draw leaves no survivor, so nothing is reduced.
        del new_board[ply.destination]

    # Inactivity clock (Section 5.4): every attack removes at least one piece --
    # a winning attack the defender, a complete sacrifice the attacker, a mutual
    # loss both -- so any attack resets the shared counter, and every
    # non-attacking ply raises it by 1.
    new_inactivity_counter = 0 if is_attack else position.inactivity_counter + 1

    return CtfPosition(
        board=MappingProxyType(new_board),
        side_to_move=opponent,
        inactivity_counter=new_inactivity_counter,
        layout=position.layout,
        ply_count=position.ply_count + 1,
    )

"""Ply application: transitions, clocks, and the breachability cache
(rules.md Sections 4.3, 6.4, 6.5).
"""

from types import MappingProxyType

from .combat import CombatResult, resolve_combat
from .pieces import PieceType
from .ply import CtfPly
from .position import CtfPosition
from .reachability import compute_breachability
from .side import Side

_CAPTURING_RESULTS = (CombatResult.ATTACKER_WINS, CombatResult.MUTUAL_LOSS)
_SACRIFICIAL_RESULTS = (CombatResult.ATTACKER_LOSES, CombatResult.MUTUAL_LOSS)


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

    removed_pieces: list[PieceType] = []
    if not is_attack:
        new_board[ply.destination] = (mover_side, mover_piece)
    elif result is CombatResult.ATTACKER_WINS:
        assert destination_occupant is not None
        removed_pieces.append(destination_occupant[1])
        new_board[ply.destination] = (mover_side, mover_piece)
    elif result is CombatResult.ATTACKER_LOSES:
        removed_pieces.append(mover_piece)
        # The defender survives untouched at the destination.
    else:
        assert result is CombatResult.MUTUAL_LOSS
        assert destination_occupant is not None
        removed_pieces.append(mover_piece)
        removed_pieces.append(destination_occupant[1])
        del new_board[ply.destination]

    # Inactivity clocks (Section 6.4): an attack always resets the mover's own
    # counter; a non-attack raises it by 1. A sacrificial attack (the mover's
    # attacker not surviving) also resets the opponent's counter; otherwise
    # the opponent's counter carries forward unchanged.
    mover_counter = (
        position.white_inactivity_counter
        if mover is Side.WHITE
        else position.black_inactivity_counter
    )
    opponent_counter = (
        position.white_inactivity_counter
        if opponent is Side.WHITE
        else position.black_inactivity_counter
    )
    new_mover_counter = 0 if is_attack else mover_counter + 1
    new_opponent_counter = (
        0 if is_attack and result in _SACRIFICIAL_RESULTS else opponent_counter
    )
    white_counter, black_counter = (
        (new_mover_counter, new_opponent_counter)
        if mover is Side.WHITE
        else (new_opponent_counter, new_mover_counter)
    )

    # Progress clock (Section 6.5): any capture resets it; a complete
    # sacrifice (or a plain move) does not.
    captured = is_attack and result in _CAPTURING_RESULTS
    new_progress_counter = 0 if captured else position.progress_counter + 1

    # Recompute the Unbreachable Flag cache only when a wall changed -- a Tower
    # or Sapper was removed. A captured Flag ends the game (Section 6.1), so a
    # ply that removes a Flag is skipped: the cache is dead state, and
    # `compute_breachability` would fail to locate the now-removed Flag.
    breachability = position.breachability
    if PieceType.FLAG not in removed_pieces and any(
        piece in (PieceType.TOWER, PieceType.SAPPER) for piece in removed_pieces
    ):
        breachability = compute_breachability(new_board)

    return CtfPosition(
        board=MappingProxyType(new_board),
        side_to_move=opponent,
        white_inactivity_counter=white_counter,
        black_inactivity_counter=black_counter,
        progress_counter=new_progress_counter,
        breachability=breachability,
    )

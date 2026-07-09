"""Legal move generation for Capture the Flag.

Implements `rules.md` Section 4.2 (Movement): the baseline one-square
orthogonal step, the Knight's charge, and the Skirmisher's rush, with lake,
blocking, and friendly-occupancy restrictions. Legality does not depend on
combat outcome — sacrificial attacks are always legal (Section 4.3); combat
resolution (a later story) determines the *result* of an attack ply, not
whether the ply exists.
"""

from typing import TYPE_CHECKING, NamedTuple

from .board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from .pieces import Mobility, PieceType
from .ply import CtfPly
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition

_DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0))


class _Reach(NamedTuple):
    square: Square
    distance: int
    is_attack: bool


def _walk(
    position: "CtfPosition", source: Square, side: Side, max_distance: int
) -> list[_Reach]:
    """Squares reachable from `source`, walking up to `max_distance` squares
    in each orthogonal direction.

    Stops, in each direction, at the board edge, a lake, or the first
    occupied square: an enemy-occupied square is included as a reachable
    (attack) destination, but nothing beyond it is; a friendly-occupied
    square blocks the direction entirely (not itself included).
    """
    reachable: list[_Reach] = []
    for dc, dr in _DIRECTIONS:
        for distance in range(1, max_distance + 1):
            square = Square(
                source.column + dc * distance, source.row + dr * distance
            )
            if not (
                0 <= square.column < BOARD_COLUMNS and 1 <= square.row <= BOARD_ROWS
            ):
                break
            if square in LAKE_SQUARES:
                break
            occupant = position.board.get(square)
            if occupant is None:
                reachable.append(_Reach(square, distance, is_attack=False))
                continue
            occupant_side, _piece = occupant
            if occupant_side is side:
                break
            reachable.append(_Reach(square, distance, is_attack=True))
            break
    return reachable


def _plies_from_square(
    position: "CtfPosition", source: Square, side: Side, piece: PieceType
) -> list[CtfPly]:
    mobility = piece.mobility
    if mobility is Mobility.IMMOBILE:
        return []

    if mobility is Mobility.KNIGHT_CHARGE:
        plies = []
        for reach in _walk(position, source, side, max_distance=3):
            if reach.distance == 1:
                # An adjacent step or ordinary attack — not a charge.
                plies.append(CtfPly(source, reach.square))
            elif reach.is_attack:
                # A 2-3 square charge: attack-only, forbidden vs. Halberdier.
                _defender_side, defender = position.board[reach.square]
                if defender is not PieceType.HALBERDIER:
                    plies.append(CtfPly(source, reach.square))
        return plies

    max_distance = 3 if mobility is Mobility.SKIRMISHER_RUSH else 1
    return [
        CtfPly(source, reach.square)
        for reach in _walk(position, source, side, max_distance)
    ]


def legal_plies(position: "CtfPosition") -> tuple[CtfPly, ...]:
    """Every legal ply for the side to move in `position`."""
    side = position.side_to_move
    plies: list[CtfPly] = []
    for square, (occupant_side, piece) in position.board.items():
        if occupant_side is side:
            plies.extend(_plies_from_square(position, square, side, piece))
    return tuple(plies)

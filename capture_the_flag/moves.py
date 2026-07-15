"""Legal move generation for Capture the Flag.

Implements `rules.md` Section 4.2 (Movement): a mobile piece steps one square
orthogonally, or two squares orthogonally through a clear path when it is
*unencumbered* (no enemy piece in any of its eight surrounding squares); an
encumbered piece is limited to one square. Legality does not depend on combat
outcome -- sacrificial attacks are always legal (Section 4.3); combat resolution
(see `combat.py`) determines the *result* of an attack ply, not whether it
exists.
"""

from typing import TYPE_CHECKING

from .board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from .pieces import Mobility, PieceType
from .ply import CtfPly
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition

_DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0))

# The eight squares surrounding a square (orthogonal and diagonal): the
# neighbourhood that determines encumbrance (rules.md Section 4.2).
_SURROUNDING = tuple(
    (dc, dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1) if (dc, dr) != (0, 0)
)


def _is_encumbered(position: "CtfPosition", source: Square, side: Side) -> bool:
    """Whether an enemy piece stands in any of the eight squares surrounding
    `source` (rules.md Section 4.2). An encumbered piece may move only one
    square; an unencumbered one may move two.
    """
    for dc, dr in _SURROUNDING:
        occupant = position.board.get(Square(source.column + dc, source.row + dr))
        if occupant is not None and occupant[0] is not side:
            return True
    return False


def _reachable_squares(
    position: "CtfPosition", source: Square, side: Side, max_distance: int
) -> list[Square]:
    """Squares reachable from `source`, walking up to `max_distance` squares in
    each orthogonal direction.

    Stops, in each direction, at the board edge, a lake, or the first occupied
    square: an enemy-occupied square is included as a reachable (attack)
    destination, but nothing beyond it is; a friendly-occupied square blocks the
    direction entirely (not itself included). A multi-square move therefore
    requires an empty intermediate path.
    """
    reachable: list[Square] = []
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
                reachable.append(square)
                continue
            occupant_side, _piece = occupant
            if occupant_side is side:
                break
            reachable.append(square)
            break
    return reachable


def _plies_from_square(
    position: "CtfPosition", source: Square, side: Side, piece: PieceType
) -> list[CtfPly]:
    if piece.mobility is Mobility.IMMOBILE:
        return []
    max_distance = 1 if _is_encumbered(position, source, side) else 2
    return [
        CtfPly(source, square)
        for square in _reachable_squares(position, source, side, max_distance)
    ]


def legal_plies(position: "CtfPosition") -> tuple[CtfPly, ...]:
    """Every legal ply for the side to move in `position`."""
    side = position.side_to_move
    plies: list[CtfPly] = []
    for square, (occupant_side, piece) in position.board.items():
        if occupant_side is side:
            plies.extend(_plies_from_square(position, square, side, piece))
    return tuple(plies)

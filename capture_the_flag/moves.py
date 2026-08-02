"""Legal move generation for Capture the Flag.

Implements `rules.md` Section 4.2 (Movement): a mobile piece steps one square
orthogonally, or two squares orthogonally through a clear path when it is
*unencumbered* (no enemy piece in any of its eight surrounding squares); an
encumbered piece is limited to one square. It may additionally attack one square
diagonally, which since major 2 is baseline behaviour rather than a variant
(Section 4.3, "Diagonal attacks"). Legality does not depend on combat outcome --
sacrificial attacks are always legal (Section 4.3); combat resolution (see
`combat.py`) determines the *result* of an attack ply, not whether it exists.

The diagonal is an *attacking* direction and nothing else, which is what keeps
it from being a general mobility increase: it never reaches an empty square, and
it never reaches a Tower or the Flag. Those two restrictions live here rather
than in `combat.py`, because they decide whether the ply exists at all -- a
diagonal attack that is generated resolves by exactly the rules an orthogonal
one does.
"""

from typing import TYPE_CHECKING

from .board import Square
from .pieces import Mobility, PieceType
from .ply import CtfPly
from .side import Side

if TYPE_CHECKING:
    from .position import CtfPosition

_DIRECTIONS = ((0, 1), (0, -1), (1, 0), (-1, 0))

# The four immediate diagonals, along which a piece may attack but never move
# (rules.md Section 4.3). One square only: there is no two-square diagonal, and
# no separate distance bound is needed to say so -- a piece with an enemy on its
# diagonal is encumbered by definition, so the unencumbered bonus can never be
# in play at the moment a diagonal attack is available.
_DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))

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
    layout = position.layout
    reachable: list[Square] = []
    for dc, dr in _DIRECTIONS:
        for distance in range(1, max_distance + 1):
            square = Square(
                source.column + dc * distance, source.row + dr * distance
            )
            if not layout.contains(square):
                break
            if layout.is_lake(square):
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


def _diagonal_attack_squares(
    position: "CtfPosition", source: Square, side: Side
) -> list[Square]:
    """The immediate diagonal squares `source` may attack (rules.md Section 4.3).

    A diagonal square qualifies only when it holds an enemy **movable** piece: a
    Tower or the Flag may not be attacked diagonally, which is what leaves the
    Flag capturable from an orthogonally adjacent square alone (Section 5.1).

    Two things fall out of requiring an occupant rather than being checked
    separately. An empty diagonal is never a destination, so the attack-only rule
    needs no second test; and a lake square never holds a piece, so a lake is
    excluded without naming it. Note this is exactly why a lake *corner* does not
    block: a one-square diagonal has no intermediate square to clear, so only the
    attacked square itself has to be open, and one holding a piece always is.

    Off-board neighbours are absent from `position.board` and so contribute
    nothing, in the same way the encumbrance and formation-bonus scans rely on.
    """
    attackable: list[Square] = []
    for dc, dr in _DIAGONALS:
        square = Square(source.column + dc, source.row + dr)
        occupant = position.board.get(square)
        if occupant is None:
            continue
        occupant_side, occupant_piece = occupant
        if occupant_side is not side and occupant_piece.mobility is Mobility.MOBILE:
            attackable.append(square)
    return attackable


def _plies_from_square(
    position: "CtfPosition", source: Square, side: Side, piece: PieceType
) -> list[CtfPly]:
    if piece.mobility is Mobility.IMMOBILE:
        return []
    max_distance = 1 if _is_encumbered(position, source, side) else 2
    destinations = _reachable_squares(position, source, side, max_distance)
    destinations += _diagonal_attack_squares(position, source, side)
    return [CtfPly(source, square) for square in destinations]


def legal_plies(position: "CtfPosition") -> tuple[CtfPly, ...]:
    """Every legal ply for the side to move in `position`."""
    side = position.side_to_move
    plies: list[CtfPly] = []
    for square, (occupant_side, piece) in position.board.items():
        if occupant_side is side:
            plies.extend(_plies_from_square(position, square, side, piece))
    return tuple(plies)

"""Legal move generation for Capture the Flag.

Implements `rules.md` Section 4.2 (Movement): a mobile piece steps one square
orthogonally, or two squares orthogonally through a clear path when it is
*unencumbered in that direction of travel* (no enemy piece on any of the five
squares ahead of or beside it, judged separately for each of the four
directions); a direction encumbered this way is limited to one square, while
the other three are unaffected. It may additionally attack one square
diagonally, which since major 2 is baseline behaviour rather than a variant
(Section 4.3, "Diagonal attacks"). Legality does not depend on combat outcome --
sacrificial attacks are always legal (Section 4.3); combat resolution (see
`combat.py`) determines the *result* of an attack ply, not whether it exists.

The diagonal is an *attacking* direction and nothing else, which is what keeps
it from being a general mobility increase: it never reaches an empty square,
and it requires an open path (Section 4.4) -- at least one of the two squares
orthogonally adjacent to both attacker and target must be empty. Those
restrictions live here rather than in `combat.py`, because they decide whether
the ply exists at all -- a diagonal attack that is generated resolves by
exactly the rules an orthogonal one does, against any enemy piece including the
Flag.
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
# (rules.md Section 4.3). One square only: `_diagonal_attack_squares` never
# reaches beyond distance one, so there is no two-square diagonal regardless of
# encumbrance in any orthogonal direction.
_DIAGONALS = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _is_encumbered_in_direction(
    position: "CtfPosition", source: Square, side: Side, direction: tuple[int, int]
) -> bool:
    """Whether an enemy piece stands on any of the five squares ahead of or
    beside `source` in `direction` (rules.md Section 4.2): the direction itself,
    its two diagonals ahead, and the two squares directly to either side. The
    three squares behind -- the reverse direction and its two diagonals -- do
    not encumber.

    Judged only from `source`'s own neighbourhood, as before -- what stands near
    the destination square does not matter.
    """
    dc, dr = direction
    perp = (-dr, dc)
    offsets = (
        (dc, dr),
        (dc + perp[0], dr + perp[1]),
        (dc - perp[0], dr - perp[1]),
        perp,
        (-perp[0], -perp[1]),
    )
    for odc, odr in offsets:
        occupant = position.board.get(Square(source.column + odc, source.row + odr))
        if occupant is not None and occupant[0] is not side:
            return True
    return False


def _reachable_squares(
    position: "CtfPosition", source: Square, side: Side, allow_two_square: bool
) -> list[Square]:
    """Squares reachable from `source`, walking up to two squares in each
    orthogonal direction the piece is unencumbered in, and one square in every
    other direction. `allow_two_square` is false for the game's first ply
    (story 00000049 step 11), which drops the two-square bonus outright.

    Stops, in each direction, at the board edge or the first occupied square: an
    enemy-occupied square is included as a reachable (attack) destination, but
    nothing beyond it is; a friendly-occupied square blocks the direction
    entirely (not itself included). A multi-square move therefore requires an
    empty intermediate path.
    """
    layout = position.layout
    reachable: list[Square] = []
    for direction in _DIRECTIONS:
        dc, dr = direction
        max_distance = 1
        if allow_two_square and not _is_encumbered_in_direction(
            position, source, side, direction
        ):
            max_distance = 2
        for distance in range(1, max_distance + 1):
            square = Square(
                source.column + dc * distance, source.row + dr * distance
            )
            if not layout.contains(square):
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
    """The immediate diagonal squares `source` may attack (rules.md Section 4.4).

    Any enemy piece qualifies, the Flag included -- there is no movable-target
    restriction, which is what leaves the Flag capturable diagonally as well as
    orthogonally (Section 5.1).

    Requiring an occupant rather than checking separately is also what keeps an
    empty diagonal from ever being a destination -- the attack-only rule needs
    no second test.

    The attack additionally needs an **open path**: at least one of the two
    squares orthogonally adjacent to both `source` and the diagonal square must
    be empty, regardless of which side occupies the other. Those two squares are
    always on the board whenever the diagonal square is, since each shares one
    coordinate with `source` and the other with the diagonal square.

    Off-board neighbours are absent from `position.board` and so contribute
    nothing, in the same way the encumbrance and formation-bonus scans rely on.
    """
    attackable: list[Square] = []
    for dc, dr in _DIAGONALS:
        square = Square(source.column + dc, source.row + dr)
        occupant = position.board.get(square)
        if occupant is None:
            continue
        occupant_side, _occupant_piece = occupant
        if occupant_side is side:
            continue
        flank_a = position.board.get(Square(source.column + dc, source.row))
        flank_b = position.board.get(Square(source.column, source.row + dr))
        if flank_a is not None and flank_b is not None:
            continue
        attackable.append(square)
    return attackable

def _initial_plies_from_square(
    position: "CtfPosition", source: Square, side: Side, piece: PieceType    
) -> list[CtfPly]:
    if piece.mobility is Mobility.IMMOBILE:
        return []
    destinations = _reachable_squares(position, source, side, False)
    destinations += _diagonal_attack_squares(position, source, side)
    return [CtfPly(source, square) for square in destinations]

def _plies_from_square(
    position: "CtfPosition", source: Square, side: Side, piece: PieceType
) -> list[CtfPly]:
    if piece.mobility is Mobility.IMMOBILE:
        return []
    destinations = _reachable_squares(position, source, side, True)
    destinations += _diagonal_attack_squares(position, source, side)
    return [CtfPly(source, square) for square in destinations]

def _initial_legal_plies(position: "CtfPosition") -> tuple[CtfPly, ...]:
    """Every legal ply for the side to move in `position`."""
    side = position.side_to_move
    plies: list[CtfPly] = []
    for square, (occupant_side, piece) in position.board.items():
        if occupant_side is side:
            plies.extend(_initial_plies_from_square(position, square, side, piece))
    return tuple(plies)

def legal_plies(position: "CtfPosition") -> tuple[CtfPly, ...]:
    """Every legal ply for the side to move in `position`."""
    if position.ply_count == 0:
        return _initial_legal_plies(position)
    side = position.side_to_move
    plies: list[CtfPly] = []
    for square, (occupant_side, piece) in position.board.items():
        if occupant_side is side:
            plies.extend(_plies_from_square(position, square, side, piece))
    return tuple(plies)

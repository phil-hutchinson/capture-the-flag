"""Phase-1 placement: the seam between a side's home-zone arrangement and a
`CtfPosition`, plus a uniformly-random legal placement generator.

`assemble_position` is the one seam later stories plug into: any placement
producer (human entry, a heuristic, a learned policy) need only produce a
`Placement` — a completely filled home zone matching the army roster — and
hand it here, without the rest of the game needing to know how it was made.
"""

import random
from collections.abc import Mapping
from types import MappingProxyType

from .board import BLACK_HOME_SQUARES, WHITE_HOME_SQUARES, Square
from .pieces import ARMY_ROSTER, PieceType
from .position import CtfPosition
from .side import Side

Placement = Mapping[Square, PieceType]
"""One side's full 48-square home-zone arrangement: every home square filled,
one piece per square, matching `ARMY_ROSTER` exactly."""

_HOME_SQUARES: dict[Side, frozenset[Square]] = {
    Side.WHITE: WHITE_HOME_SQUARES,
    Side.BLACK: BLACK_HOME_SQUARES,
}


def random_placement(side: Side, rng: random.Random | None = None) -> Placement:
    """A uniformly random legal placement for `side`.

    `rng` defaults to a fresh `random.Random()`; pass a seeded one for
    reproducible output.
    """
    rng = rng if rng is not None else random.Random()
    squares = sorted(_HOME_SQUARES[side])
    rng.shuffle(squares)
    pieces = [piece for piece, count in ARMY_ROSTER.items() for _ in range(count)]
    return dict(zip(squares, pieces, strict=True))


def _validate_placement(side: Side, placement: Placement) -> None:
    expected_squares = _HOME_SQUARES[side]
    if set(placement.keys()) != expected_squares:
        raise ValueError(
            f"{side.name} placement must fill exactly its 48-square home zone"
        )
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    if counts != ARMY_ROSTER:
        raise ValueError(f"{side.name} placement does not match the army roster")


def assemble_position(
    white_placement: Placement, black_placement: Placement
) -> CtfPosition:
    """Build the phase-2 starting `CtfPosition` from a White and a Black
    placement: White to move, the inactivity counter at 0.
    """
    _validate_placement(Side.WHITE, white_placement)
    _validate_placement(Side.BLACK, black_placement)

    board: dict[Square, tuple[Side, PieceType]] = {}
    for square, piece in white_placement.items():
        board[square] = (Side.WHITE, piece)
    for square, piece in black_placement.items():
        board[square] = (Side.BLACK, piece)

    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
    )

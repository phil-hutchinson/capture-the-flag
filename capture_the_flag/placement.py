"""Phase-1 placement: the seam between a side's home-zone arrangement and a
`CtfPosition`, plus a uniformly-random legal placement generator.

`assemble_position` is the one seam later stories plug into: any placement
producer (human entry, a heuristic, a learned policy) need only produce a
`Placement` — the setup's army placed in its home zone, matching that army's
composition and respecting the Tower spacing rule — and hand it here, without the
rest of the game needing to know how it was made.
"""

import itertools
import random
from collections.abc import Mapping
from types import MappingProxyType

from .board import Square
from .game_setup import GameSetup
from .pieces import PieceType
from .position import CtfPosition
from .side import Side

Placement = Mapping[Square, PieceType]
"""One side's home-zone arrangement: some of its home squares filled and the rest
left empty, one piece per square, matching the setup's army composition, and with
no two Towers within one square of each other (rules.md Section 3)."""


def _closed_neighbourhood(square: Square) -> set[Square]:
    """`square` together with its eight surrounding squares. Placing a Tower on
    `square` forbids a second Tower anywhere in this set (rules.md Section 3)."""
    return {
        Square(square.column + dc, square.row + dr)
        for dc in (-1, 0, 1)
        for dr in (-1, 0, 1)
    }


def _towers_too_close(a: Square, b: Square) -> bool:
    """Whether two Towers on `a` and `b` violate the spacing rule -- i.e. lie
    within one square of each other, orthogonally or diagonally."""
    return max(abs(a.column - b.column), abs(a.row - b.row)) <= 1


def random_placement(
    side: Side, setup: GameSetup, rng: random.Random | None = None
) -> Placement:
    """A near-uniformly random legal placement for `side`: pieces dropped onto
    the board (never the inverse), Towers first so their spacing is easy to
    honour. Non-Tower arrangements are drawn uniformly; the greedy Tower-first
    walk keeps every layout legal but leaves the Tower configuration only
    approximately uniform, which is sufficient for random play and test data.

    `rng` defaults to a fresh `random.Random()`; pass a seeded one for
    reproducible output.
    """
    rng = rng if rng is not None else random.Random()
    home = setup.layout.home_squares(side)
    placement: dict[Square, PieceType] = {}

    # Drop the Towers first, shrinking the set of squares still legal for a Tower
    # after each placement. Every Tower removes at most its nine-square closed
    # neighbourhood, so the walk never stalls as long as the home zone has more
    # than 9 x (towers - 1) squares: Battle places 6 in 48, leaving at least 3
    # candidates for the sixth, and Skirmish 3 in 24, leaving at least 6 for the
    # third. The bound is per-setup since major 2 and has to be re-derived for any
    # new board and army pairing, not assumed from Battle.
    tower_candidates = set(home)
    for _ in range(setup.composition.count(PieceType.TOWER)):
        square = rng.choice(sorted(tower_candidates))
        placement[square] = PieceType.TOWER
        tower_candidates -= _closed_neighbourhood(square)

    # Scatter the remaining pieces over the still-empty home squares. Shuffling
    # the open squares and zipping the (unconstrained) pieces onto the first of
    # them keeps every non-Tower arrangement equally likely; the surplus squares
    # past the piece count stay empty.
    open_squares = sorted(home - placement.keys())
    rng.shuffle(open_squares)
    other_pieces = [
        piece
        for piece, count in setup.composition.counts.items()
        if piece is not PieceType.TOWER
        for _ in range(count)
    ]
    for square, piece in zip(open_squares, other_pieces, strict=False):
        placement[square] = piece
    return placement


def _validate_placement(side: Side, placement: Placement, setup: GameSetup) -> None:
    home = setup.layout.home_squares(side)
    if not placement.keys() <= home:
        raise ValueError(
            f"{side.name} placement must lie entirely within its home zone"
        )
    counts: dict[PieceType, int] = {}
    for piece in placement.values():
        counts[piece] = counts.get(piece, 0) + 1
    if any(counts.get(p, 0) != setup.composition.count(p) for p in PieceType):
        raise ValueError(
            f"{side.name} placement does not match the "
            f"{setup.composition.size}-piece "
            f"{setup.composition.composition_id} army"
        )
    towers = [square for square, piece in placement.items() if piece is PieceType.TOWER]
    if any(_towers_too_close(a, b) for a, b in itertools.combinations(towers, 2)):
        raise ValueError(f"{side.name} placement has two Towers within one square")


def assemble_position(
    white_placement: Placement, black_placement: Placement, setup: GameSetup
) -> CtfPosition:
    """Build the phase-2 starting `CtfPosition` from a White and a Black
    placement: White to move, the inactivity counter at 0.
    """
    _validate_placement(Side.WHITE, white_placement, setup)
    _validate_placement(Side.BLACK, black_placement, setup)

    board: dict[Square, tuple[Side, PieceType]] = {}
    for square, piece in white_placement.items():
        board[square] = (Side.WHITE, piece)
    for square, piece in black_placement.items():
        board[square] = (Side.BLACK, piece)

    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=setup.layout,
    )

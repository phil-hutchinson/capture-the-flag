"""Starting-position generation for Capture the Flag (`doc/ruleset/start-position.md`).

There is no placement phase (`rules.md` Section 3): every game begins from a
starting position drawn from the constrained set that document defines, rather
than from choices either player makes. `generate_start_position` is the single
seam that replaces the phase-1 placement stories 1-48 built, exactly the way
`placement.random_placement` used to be the seam a game's opening squares came
from.

Generation is two steps, `start-position.md` Sections 2-3:

1. **White's arrangement** is drawn uniformly from the constrained set: the Flag
   on a uniform square of White's back row, the remaining numbered pieces
   shuffled uniformly into the rest of White's home zone.
2. **Black's arrangement** is derived from White's by the strength rule, never
   drawn independently: sum the ranks of the numbered pieces sharing the Flag's
   column half, and turn White's whole arrangement 180 degrees if that sum meets
   the threshold, or reflect it top-to-bottom otherwise. Both turns are pure
   board geometry -- the same 180-degree rotation and top-to-bottom mirror move
   generation and combat already reason about -- so deriving Black's army costs
   nothing beyond picking which one to apply.

Written in terms of `setup.layout` and `setup.composition` rather than the
board's and army's actual sizes, matching every other seam in this package
(`moves.py`, `combat.py`, the tensor layout) that takes its geometry from the
position or the setup rather than from a module constant. Only one board and
army are published at major 3, but the seam does not assume that will stay
true.
"""

import random
from types import MappingProxyType

from .board import BoardLayout, Square
from .game_setup import GameSetup
from .pieces import ArmyComposition, PieceType
from .position import CtfPosition
from .side import Side


def generate_start_position(
    setup: GameSetup, rng: random.Random | None = None
) -> CtfPosition:
    """A starting `CtfPosition` for `setup`, drawn from the constrained set
    `start-position.md` defines: White to move, the inactivity counter at 0.

    `rng` defaults to a fresh `random.Random()`; pass a seeded one for
    reproducible output. **Never generate by drawing a random position ID** --
    the ID (Section 5) is sparse, so almost no code names a real position; this
    function is the only legitimate generator.
    """
    rng = rng if rng is not None else random.Random()
    white_arrangement = _generate_white_arrangement(setup, rng)
    black_arrangement = _derive_black_arrangement(white_arrangement, setup)

    board: dict[Square, tuple[Side, PieceType]] = {}
    for square, piece in white_arrangement.items():
        board[square] = (Side.WHITE, piece)
    for square, piece in black_arrangement.items():
        board[square] = (Side.BLACK, piece)

    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=setup.layout,
    )


def _generate_white_arrangement(
    setup: GameSetup, rng: random.Random
) -> dict[Square, PieceType]:
    """White's half of the constrained set (`start-position.md` Section 2): the
    Flag on a uniformly chosen square of White's back row, the remaining
    numbered pieces shuffled uniformly into the rest of White's home zone.

    `GameSetup` already guarantees the army fills the home zone exactly (one
    piece per square, `game_setup.py`), so the numbered-piece count always
    matches the squares left once the Flag is placed.
    """
    layout = setup.layout
    back_row = layout.white_home_rows[0]
    flag_square = rng.choice([Square(column, back_row) for column in range(layout.columns)])

    numbered_pieces = [
        piece
        for piece, count in setup.composition.counts.items()
        if piece is not PieceType.FLAG
        for _ in range(count)
    ]
    remaining_squares = sorted(layout.white_home_squares - {flag_square})
    rng.shuffle(remaining_squares)

    arrangement: dict[Square, PieceType] = {flag_square: PieceType.FLAG}
    arrangement.update(zip(remaining_squares, numbered_pieces, strict=True))
    return arrangement


def _derive_black_arrangement(
    white_arrangement: dict[Square, PieceType], setup: GameSetup
) -> dict[Square, PieceType]:
    """Black's arrangement: White's, turned by the strength rule
    (`start-position.md` Section 3)."""
    layout = setup.layout
    flag_square = next(
        square
        for square, piece in white_arrangement.items()
        if piece is PieceType.FLAG
    )
    strength = _flag_half_strength(white_arrangement, flag_square, layout)
    turn = _half_turn if strength >= strength_threshold(setup) else _reflect
    return {turn(square, layout): piece for square, piece in white_arrangement.items()}


def _numbered_rank(piece: PieceType) -> int:
    """`piece.rank`, asserted non-`None`: only ever called on a numbered piece,
    never the Flag, which callers filter out first."""
    assert piece.rank is not None, "the Flag has no rank"
    return piece.rank


def _half_boundary(layout: BoardLayout) -> int:
    """The column index (0-based) that starts the right half of `layout`'s
    board (`start-position.md` Section 3: columns A-D and E-H at major 3).

    The strength rule splits the board into two equal column halves, so this is
    only meaningful for an even-width board -- the one published board is one,
    and nothing here assumes a specific width beyond that.
    """
    assert layout.columns % 2 == 0, (
        f"the strength rule splits the board into two equal halves by column; "
        f"{layout.layout_id} has an odd width ({layout.columns})"
    )
    return layout.columns // 2


def _flag_half_squares(flag_square: Square, layout: BoardLayout) -> frozenset[Square]:
    """Every White home square sharing the Flag's column half, Flag included."""
    boundary = _half_boundary(layout)
    flag_in_left_half = flag_square.column < boundary
    return frozenset(
        square
        for square in layout.white_home_squares
        if (square.column < boundary) == flag_in_left_half
    )


def _flag_half_strength(
    white_arrangement: dict[Square, PieceType], flag_square: Square, layout: BoardLayout
) -> int:
    """`S`: the sum of the ranks of the numbered pieces sharing the Flag's
    column half (`start-position.md` Section 3)."""
    half_squares = _flag_half_squares(flag_square, layout)
    return sum(
        _numbered_rank(piece)
        for square, piece in white_arrangement.items()
        if square in half_squares and piece is not PieceType.FLAG
    )


def _total_numbered_rank(composition: ArmyComposition) -> int:
    """The sum of every numbered piece's rank across the whole army -- `45` for
    three each of ranks 1-5, the `total rank` `start-position.md` Section 3
    weighs a half's strength against."""
    return sum(
        _numbered_rank(piece) * composition.count(piece)
        for piece in PieceType
        if piece is not PieceType.FLAG
    )


def strength_threshold(setup: GameSetup) -> int:
    """The smallest flag-half strength `S` that selects the half-turn branch of
    the strength rule (`start-position.md` Section 3): `22` for three each of
    ranks 1-5, derived rather than written as that literal so a future army
    recomputes its own threshold instead of inheriting one that fit a different
    roster.

    Written in the threshold form the document prefers -- one product, one
    floor division, one comparison -- rather than the equivalent
    "compare the two halves' strongest pieces" form it motivates the rule with:
    `S` selects the half-turn branch once it exceeds a flag's-half share of the
    total rank, i.e. the smallest integer strictly greater than
    `(numbered pieces per half / total numbered pieces) x total rank`.
    """
    half_squares = _half_boundary(setup.layout) * setup.layout.home_rows
    numbered_per_half = half_squares - 1  # the Flag occupies one of them
    total_numbered = setup.composition.size - 1
    total_rank = _total_numbered_rank(setup.composition)
    return (numbered_per_half * total_rank) // total_numbered + 1


def _half_turn(square: Square, layout: BoardLayout) -> Square:
    """White's square turned 180 degrees: the strength rule's half-turn branch,
    the same rotation `ctf_nn_evaluator.rotate_square` applies for the
    side-to-move perspective transform -- two different rules that happen to
    need the same geometry."""
    return Square(layout.columns - 1 - square.column, layout.rows + 1 - square.row)


def _reflect(square: Square, layout: BoardLayout) -> Square:
    """White's square mirrored top-to-bottom: the strength rule's reflection
    branch. Column unchanged; row flipped about the board's midline."""
    return Square(square.column, layout.rows + 1 - square.row)

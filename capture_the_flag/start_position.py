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

3. **The position ID** (Section 5) names a startable position by White's
   arrangement alone -- Black follows from it by the same strength rule -- as a
   16-character string, one hexadecimal digit per White home square, read row
   by row from White's back row, each row A to H. `position_id` encodes;
   `decode_position_id` decodes and validates against exactly the constrained
   set Section 1 through 3 build; `mirror_of` is the Section 4 helper the
   generator itself must never call.

Written in terms of `setup.layout` and `setup.composition` rather than the
board's and army's actual sizes, matching every other seam in this package
(`moves.py`, `combat.py`, the tensor layout) that takes its geometry from the
position or the setup rather than from a module constant. Only one board and
army are published at major 3, but the seam does not assume that will stay
true. The digit scheme follows this all the way down: a numbered piece encodes
as the hexadecimal digit of its rank, not as a table keyed to the five ranks
major 3 happens to have, so a later rank above 5 (hex digits `6`-`E` are
reserved precisely for this, Section 5 "Reserved digits") encodes and decodes
with no change here.
"""

import random
from collections import Counter
from collections.abc import Mapping
from types import MappingProxyType

from .board import BoardLayout, Square
from .game_setup import GameSetup
from .pieces import ArmyComposition, PieceType
from .position import CtfPosition
from .side import Side

_FLAG_DIGIT = "F"
_EMPTY_DIGIT = "0"

_PIECE_BY_RANK: Mapping[int, PieceType] = {
    piece.rank: piece for piece in PieceType if piece.rank is not None
}


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
    return _assemble_position(white_arrangement, setup)


def _assemble_position(
    white_arrangement: dict[Square, PieceType], setup: GameSetup
) -> CtfPosition:
    """The full starting `CtfPosition` for a White arrangement already known to
    be a member of the constrained set: Black derived by the strength rule,
    White to move, the inactivity counter at 0.

    Shared by `generate_start_position` (White drawn fresh) and
    `decode_position_id` (White read off a position ID) -- deriving Black and
    assembling the board is the same step either way.
    """
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


def _white_squares_in_id_order(layout: BoardLayout) -> tuple[Square, ...]:
    """White's home squares in the order a position ID reads them
    (`start-position.md` Section 5): row by row from the back row, each row A
    to H."""
    return tuple(
        Square(column, row)
        for row in layout.white_home_rows
        for column in range(layout.columns)
    )


def _digit_for(piece: PieceType | None) -> str:
    """The hexadecimal digit one square's occupant encodes as: `0` for empty,
    `F` for the Flag, otherwise the hex digit of the piece's rank -- `1`-`5` at
    major 3, with `6`-`E` reserved for ranks no current army fields
    (`start-position.md` Section 5, "Reserved digits")."""
    if piece is None:
        return _EMPTY_DIGIT
    if piece is PieceType.FLAG:
        return _FLAG_DIGIT
    return format(_numbered_rank(piece), "X")


def _piece_for(digit: str) -> PieceType | None:
    """The inverse of `_digit_for`. Raises `ValueError` naming the digit for
    anything not `0`, `F`, or the hex digit of a rank some `PieceType`
    actually has -- a code using a currently-reserved digit names no piece,
    same as one using a non-hexadecimal character."""
    if digit == _EMPTY_DIGIT:
        return None
    if digit == _FLAG_DIGIT:
        return PieceType.FLAG
    try:
        rank = int(digit, 16)
    except ValueError:
        raise ValueError(
            f"{digit!r} is not a valid position-ID digit (expected 0-9, A-F)"
        ) from None
    piece = _PIECE_BY_RANK.get(rank)
    if piece is None:
        raise ValueError(f"{digit!r} names rank {rank}, which no piece type has")
    return piece


def _encode_white_arrangement(
    arrangement: Mapping[Square, PieceType], layout: BoardLayout
) -> str:
    return "".join(
        _digit_for(arrangement.get(square))
        for square in _white_squares_in_id_order(layout)
    )


def position_id(position: CtfPosition) -> str:
    """The 16-character position ID naming `position`'s White arrangement
    (`start-position.md` Section 5): intended for a starting position, since
    the ID names one of those, not an arbitrary point in a game.

    Black is not read: it always follows from White by the strength rule
    (Section 3), so the ID names the whole position from White's side alone.
    """
    white_arrangement = {
        square: piece
        for square, (side, piece) in position.board.items()
        if side is Side.WHITE
    }
    return _encode_white_arrangement(white_arrangement, position.layout)


def _decode_white_arrangement(code: str, setup: GameSetup) -> dict[Square, PieceType]:
    """`code`'s White arrangement, validated against the constrained set
    `start-position.md` Sections 1-2 define for `setup`'s army: the right
    length, exactly the piece counts `setup.composition` fields, and the Flag
    on White's back row. Raises `ValueError` naming whichever check fails
    first.

    `code` must already be upper-cased -- every caller here normalises once, at
    the public entry point, rather than each internal step normalising again.
    """
    layout = setup.layout
    squares = _white_squares_in_id_order(layout)
    if len(code) != len(squares):
        raise ValueError(
            f"a position ID must be {len(squares)} characters, got "
            f"{len(code)} ({code!r})"
        )

    arrangement: dict[Square, PieceType] = {}
    for square, digit in zip(squares, code, strict=True):
        piece = _piece_for(digit)
        if piece is not None:
            arrangement[square] = piece

    counts = Counter(arrangement.values())
    expected_counts = Counter(setup.composition.counts)
    if counts != expected_counts:
        raise ValueError(
            f"{code!r} does not field the {setup.composition.composition_id} "
            f"army: expected {dict(expected_counts)}, got {dict(counts)}"
        )

    flag_square = next(
        square for square, piece in arrangement.items() if piece is PieceType.FLAG
    )
    back_row = layout.white_home_rows[0]
    if flag_square.row != back_row:
        raise ValueError(
            f"{code!r} places the Flag on row {flag_square.row}, but the Flag "
            f"must stand on White's back row (row {back_row}, "
            "start-position.md Section 1)"
        )

    return arrangement


def decode_position_id(code: str, setup: GameSetup) -> CtfPosition:
    """The starting `CtfPosition` named by `code` for `setup`
    (`start-position.md` Section 5): White's arrangement decoded and validated
    against the constrained set, Black derived by the strength rule exactly as
    `generate_start_position` derives it.

    `code` is upper-cased before anything else: `start-position.md` Section 5
    defines comparison, sorting and storage on the upper-cased form alone, so a
    lowercase code is accepted but never compared or stored as typed.

    Raises `ValueError` naming what is wrong when `code` does not name a
    startable position for `setup`'s army -- wrong length, wrong piece counts,
    or a Flag off White's back row.
    """
    white_arrangement = _decode_white_arrangement(code.upper(), setup)
    return _assemble_position(white_arrangement, setup)


def mirror_of(code: str, setup: GameSetup) -> str:
    """The position ID of `code`'s left-right mirror image
    (`start-position.md` Section 4): the same arrangement with every column
    reflected (`c` -> `columns - 1 - c`) and every row unchanged.

    For study or for pairing a position with its mirror twin. **Never called by
    `generate_start_position`**: collapsing each mirror pair to one
    representative would draw only ever the same half of the constrained set,
    which is exactly the bias Section 4 says generation must not introduce.
    """
    layout = setup.layout
    white_arrangement = _decode_white_arrangement(code.upper(), setup)
    mirrored = {
        Square(layout.columns - 1 - square.column, square.row): piece
        for square, piece in white_arrangement.items()
    }
    return _encode_white_arrangement(mirrored, layout)

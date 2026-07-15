"""Piece domain data for Capture the Flag.

Static rank, symbol, army-roster, and mobility data from the rules
(`doc/ruleset/rules.md` Section 2.2) and the position-block notation
(`doc/ruleset/technical-notes.md`). Combat resolution and move legality live in
`combat.py` and `moves.py`; this module only carries the static facts both
depend on.
"""

from enum import Enum


class Mobility(Enum):
    """How a piece is permitted to move, independent of combat legality.

    Under the revamped ruleset every mobile piece shares one movement rule (a
    one-square orthogonal step, extended to two when unencumbered — see
    `moves.py`), so mobility is a simple binary: the Tower and Flag never move,
    everything else does.
    """

    IMMOBILE = "immobile"
    MOBILE = "mobile"


class PieceType(Enum):
    """One of the eight piece types, with its rank, symbol, and army count.

    `rank` is `None` for the two pieces that never fight by rank (Tower, Flag);
    the six numbered pieces form a strict strength order from rank 1 (strongest)
    to rank 6 (weakest).
    """

    MASTER_OF_ARMS = ("1", "Master-of-Arms", 1, 3, Mobility.MOBILE)
    CHAMPION = ("2", "Champion", 2, 3, Mobility.MOBILE)
    KNIGHT = ("3", "Knight", 3, 3, Mobility.MOBILE)
    HALBERDIER = ("4", "Halberdier", 4, 3, Mobility.MOBILE)
    FOOT_SOLDIER = ("5", "Foot Soldier", 5, 3, Mobility.MOBILE)
    MILITIA = ("6", "Militia", 6, 3, Mobility.MOBILE)
    TOWER = ("T", "Tower", None, 6, Mobility.IMMOBILE)
    FLAG = ("F", "Flag", None, 1, Mobility.IMMOBILE)

    def __init__(
        self,
        symbol: str,
        piece_name: str,
        rank: int | None,
        army_count: int,
        mobility: Mobility,
    ) -> None:
        self.symbol = symbol
        self.piece_name = piece_name
        self.rank = rank
        self.army_count = army_count
        self.mobility = mobility


# Per-piece counts in one 25-piece army, keyed by piece type.
ARMY_ROSTER: dict[PieceType, int] = {piece: piece.army_count for piece in PieceType}

ARMY_SIZE = sum(ARMY_ROSTER.values())

# The symbol -> piece inverse of `PieceType.symbol`, shared by the modules that
# parse position blocks and placement files.
PIECE_BY_SYMBOL: dict[str, PieceType] = {piece.symbol: piece for piece in PieceType}

"""Piece domain data for Capture the Flag.

Static rank, symbol, army-roster, and mobility data from the rules
(`doc/ruleset/rules.md` Section 2.2) and the position-block notation
(`.local/game-notation-suggestion.md`). Combat resolution and move legality
are implemented in later stories; this module only carries the static facts
both depend on.
"""

from enum import Enum


class Mobility(Enum):
    """How a piece is permitted to move, independent of combat legality."""

    IMMOBILE = "immobile"
    BASELINE = "baseline"  # one square orthogonally, move or attack
    KNIGHT_CHARGE = "knight_charge"  # 2-3 squares in a clear line, attack-only
    SKIRMISHER_RUSH = "skirmisher_rush"  # up to 3 squares in a clear line, move or attack


class PieceType(Enum):
    """One of the twelve piece types, with its rank, symbol, and army count.

    `rank` is `None` for the three pieces that resolve combat outside the
    numbered strength order (Assassin, Tower, Flag) rather than by rank.
    """

    LORD_MARSHAL = ("1", "Lord Marshal", 1, 1, Mobility.BASELINE)
    CHAMPION = ("2", "Champion", 2, 2, Mobility.BASELINE)
    KNIGHT = ("3", "Knight", 3, 4, Mobility.KNIGHT_CHARGE)
    INFANTRY = ("4", "Infantry", 4, 4, Mobility.BASELINE)
    HALBERDIER = ("5", "Halberdier", 5, 6, Mobility.BASELINE)
    MILITIA = ("6", "Militia", 6, 6, Mobility.BASELINE)
    SKIRMISHER = ("7", "Skirmisher", 7, 6, Mobility.SKIRMISHER_RUSH)
    ARCHER = ("8", "Archer", 8, 3, Mobility.BASELINE)
    SAPPER = ("9", "Sapper", 9, 8, Mobility.BASELINE)
    ASSASSIN = ("A", "Assassin", None, 1, Mobility.BASELINE)
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


# Per-piece counts in one 48-piece army, keyed by piece type.
ARMY_ROSTER: dict[PieceType, int] = {piece: piece.army_count for piece in PieceType}

ARMY_SIZE = sum(ARMY_ROSTER.values())

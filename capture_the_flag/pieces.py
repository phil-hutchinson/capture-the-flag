"""Piece domain data for Capture the Flag.

Static rank, symbol, and mobility data from the rules
(`doc/ruleset/rules.md` Section 2.2) and the position-block notation
(`doc/ruleset/technical-notes.md`), plus `ArmyComposition`: how many of each
piece one army holds. Combat resolution and move legality live in `combat.py`
and `moves.py`; this module only carries the static facts both depend on.

**How many of a piece exists is not a property of the piece.** Since major 2 it
is the resolved value of the `ARMY_COMPOSITION` flag, so it lives on a
composition value rather than on the `PieceType` member — a count on the enum
would be a single global army by construction, which is exactly what two live
rulesets cannot have. What a piece *is* (its symbol, name, rank, and whether it
moves) is the same under every composition and stays on the enum.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType


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
    """One of the eight piece types, with its rank, symbol, and mobility.

    `rank` is `None` for the two pieces that never fight by rank (Tower, Flag);
    the six numbered pieces form a strict strength order from rank 1 (strongest)
    to rank 6 (weakest).

    Every piece type is defined here whether or not a given army fields any: the
    enum is the vocabulary of the game, and how many of each an army holds is an
    `ArmyComposition` question. A composition that omits a rank does not make
    that rank cease to exist — a record written under another composition still
    has to name it.
    """

    MASTER_OF_ARMS = ("1", "Master-of-Arms", 1, Mobility.MOBILE)
    CHAMPION = ("2", "Champion", 2, Mobility.MOBILE)
    KNIGHT = ("3", "Knight", 3, Mobility.MOBILE)
    HALBERDIER = ("4", "Halberdier", 4, Mobility.MOBILE)
    FOOT_SOLDIER = ("5", "Foot Soldier", 5, Mobility.MOBILE)
    MILITIA = ("6", "Militia", 6, Mobility.MOBILE)
    TOWER = ("T", "Tower", None, Mobility.IMMOBILE)
    FLAG = ("F", "Flag", None, Mobility.IMMOBILE)

    def __init__(
        self,
        symbol: str,
        piece_name: str,
        rank: int | None,
        mobility: Mobility,
    ) -> None:
        self.symbol = symbol
        self.piece_name = piece_name
        self.rank = rank
        self.mobility = mobility


@dataclass(frozen=True)
class ArmyComposition:
    """One army: how many of each piece type a player commands.

    `composition_id` is the published `ARMY_COMPOSITION` value label, permanent
    once published and what a record or checkpoint resolves back to — so it
    belongs on the composition rather than beside it, exactly as `layout_id` does
    on `BoardLayout`.

    `counts` names only the piece types the army actually fields. A type absent
    from it has a count of zero, which `count` returns without the caller having
    to know whether the composition mentions it: `standard_skirmish` fields no
    Foot Soldier, and code that asks how many there are wants 0, not a KeyError.
    """

    composition_id: str
    counts: Mapping[PieceType, int]
    size: int = field(init=False, compare=False)

    def __post_init__(self) -> None:
        if any(count < 1 for count in self.counts.values()):
            raise ValueError(
                f"{self.composition_id}: a piece type present in an army must "
                "have a count of at least 1; omit it instead"
            )
        if self.counts.get(PieceType.FLAG) != 1:
            raise ValueError(
                f"{self.composition_id}: an army has exactly one Flag, since "
                "capturing it ends the game (rules.md Section 5.1)"
            )
        object.__setattr__(self, "counts", MappingProxyType(dict(self.counts)))
        object.__setattr__(self, "size", sum(self.counts.values()))

    def __hash__(self) -> int:
        """Hash by content: the generated `__hash__` a frozen dataclass supplies
        would raise on the mapping field, as `record.Edition` does for the same
        reason."""
        return hash((self.composition_id, frozenset(self.counts.items())))

    def count(self, piece: PieceType) -> int:
        """How many of `piece` this army fields — 0 if it fields none."""
        return self.counts.get(piece, 0)


STANDARD_BATTLE: ArmyComposition = ArmyComposition(
    composition_id="standard_battle",
    counts={
        PieceType.MASTER_OF_ARMS: 3,
        PieceType.CHAMPION: 3,
        PieceType.KNIGHT: 3,
        PieceType.HALBERDIER: 3,
        PieceType.FOOT_SOLDIER: 3,
        PieceType.MILITIA: 3,
        PieceType.TOWER: 6,
        PieceType.FLAG: 1,
    },
)
"""The Battle army: 3 each of ranks 1-6, 6 Towers, 1 Flag — 25 pieces."""

STANDARD_SKIRMISH: ArmyComposition = ArmyComposition(
    composition_id="standard_skirmish",
    counts={
        PieceType.MASTER_OF_ARMS: 3,
        PieceType.CHAMPION: 3,
        PieceType.KNIGHT: 3,
        PieceType.HALBERDIER: 3,
        PieceType.TOWER: 3,
        PieceType.FLAG: 1,
    },
)
"""The Skirmish army: 3 each of ranks 1-4, 3 Towers, 1 Flag — 16 pieces.

The top four ranks only; Foot Soldier and Militia do not appear, and `count`
answers 0 for them rather than raising."""

ARMY_COMPOSITIONS: dict[str, ArmyComposition] = {
    composition.composition_id: composition
    for composition in (STANDARD_BATTLE, STANDARD_SKIRMISH)
}
"""Every `ARMY_COMPOSITION` value this build can actually field, keyed by its
label — the army-side counterpart of `board.BOARD_LAYOUTS`, and implementability
rather than publication for the same reason."""


# The symbol -> piece inverse of `PieceType.symbol`, shared by the modules that
# parse position blocks and placement files.
PIECE_BY_SYMBOL: dict[str, PieceType] = {piece.symbol: piece for piece in PieceType}

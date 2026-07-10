"""Tests for static piece domain data: symbols, ranks, and the army roster."""

from capture_the_flag.pieces import ARMY_ROSTER, ARMY_SIZE, Mobility, PieceType

# Per-rank quantities from doc/ruleset/rules.md Section 2.2.
EXPECTED_COUNTS = {
    PieceType.LORD_MARSHAL: 1,
    PieceType.CHAMPION: 2,
    PieceType.KNIGHT: 4,
    PieceType.INFANTRY: 4,
    PieceType.HALBERDIER: 6,
    PieceType.MILITIA: 6,
    PieceType.SKIRMISHER: 6,
    PieceType.ARCHER: 3,
    PieceType.SAPPER: 8,
    PieceType.ASSASSIN: 1,
    PieceType.TOWER: 6,
    PieceType.FLAG: 1,
}


def test_army_sums_to_48():
    assert ARMY_SIZE == 48
    assert sum(ARMY_ROSTER.values()) == 48


def test_per_rank_counts_match_rules_table():
    assert ARMY_ROSTER == EXPECTED_COUNTS
    for piece, count in EXPECTED_COUNTS.items():
        assert piece.army_count == count


def test_numbered_pieces_have_strict_rank_order():
    ranks = sorted(piece.rank for piece in PieceType if piece.rank is not None)
    assert ranks == list(range(1, 10))


def test_assassin_tower_flag_have_no_rank():
    for piece in (PieceType.ASSASSIN, PieceType.TOWER, PieceType.FLAG):
        assert piece.rank is None


def test_mobility_categories():
    assert PieceType.TOWER.mobility is Mobility.IMMOBILE
    assert PieceType.FLAG.mobility is Mobility.IMMOBILE
    assert PieceType.KNIGHT.mobility is Mobility.KNIGHT_CHARGE
    assert PieceType.SKIRMISHER.mobility is Mobility.SKIRMISHER_RUSH

    others = set(PieceType) - {
        PieceType.TOWER,
        PieceType.FLAG,
        PieceType.KNIGHT,
        PieceType.SKIRMISHER,
    }
    assert all(piece.mobility is Mobility.BASELINE for piece in others)


def test_symbols_are_unique_and_match_notation_spec():
    symbols = {piece.symbol for piece in PieceType}
    assert len(symbols) == len(PieceType)
    assert symbols == set("123456789") | {"A", "T", "F"}

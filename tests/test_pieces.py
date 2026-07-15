"""Tests for static piece domain data: symbols, ranks, and the army roster."""

from capture_the_flag.pieces import ARMY_ROSTER, ARMY_SIZE, Mobility, PieceType

# Per-rank quantities from doc/ruleset/rules.md Section 2.2.
EXPECTED_COUNTS = {
    PieceType.MASTER_OF_ARMS: 3,
    PieceType.CHAMPION: 3,
    PieceType.KNIGHT: 3,
    PieceType.HALBERDIER: 3,
    PieceType.FOOT_SOLDIER: 3,
    PieceType.MILITIA: 3,
    PieceType.TOWER: 6,
    PieceType.FLAG: 1,
}


def test_army_sums_to_25():
    assert ARMY_SIZE == 25
    assert sum(ARMY_ROSTER.values()) == 25


def test_per_rank_counts_match_rules_table():
    assert ARMY_ROSTER == EXPECTED_COUNTS
    for piece, count in EXPECTED_COUNTS.items():
        assert piece.army_count == count


def test_numbered_pieces_have_strict_rank_order():
    ranks = sorted(piece.rank for piece in PieceType if piece.rank is not None)
    assert ranks == list(range(1, 7))


def test_tower_and_flag_have_no_rank():
    for piece in (PieceType.TOWER, PieceType.FLAG):
        assert piece.rank is None


def test_mobility_categories():
    assert PieceType.TOWER.mobility is Mobility.IMMOBILE
    assert PieceType.FLAG.mobility is Mobility.IMMOBILE

    others = set(PieceType) - {PieceType.TOWER, PieceType.FLAG}
    assert all(piece.mobility is Mobility.MOBILE for piece in others)


def test_symbols_are_unique_and_match_notation_spec():
    symbols = {piece.symbol for piece in PieceType}
    assert len(symbols) == len(PieceType)
    assert symbols == set("123456") | {"T", "F"}

"""Tests for static piece domain data: symbols, ranks, and army compositions."""

import pytest

from capture_the_flag.pieces import (
    STANDARD_BATTLE,
    ArmyComposition,
    Mobility,
    PieceType,
)

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


def test_standard_battle_sums_to_25():
    assert STANDARD_BATTLE.size == 25
    assert sum(STANDARD_BATTLE.counts.values()) == 25


def test_per_rank_counts_match_rules_table():
    assert STANDARD_BATTLE.counts == EXPECTED_COUNTS
    for piece, count in EXPECTED_COUNTS.items():
        assert STANDARD_BATTLE.count(piece) == count


def test_count_is_zero_for_a_piece_the_army_does_not_field():
    # A composition names what it fields; every other type has a count of 0
    # rather than being an error to ask about. `standard_skirmish` will field no
    # Foot Soldier, and code that asks how many there are wants 0.
    partial = ArmyComposition(
        composition_id="ranks_1_and_2_only",
        counts={
            PieceType.MASTER_OF_ARMS: 3,
            PieceType.CHAMPION: 3,
            PieceType.FLAG: 1,
        },
    )
    assert partial.count(PieceType.MILITIA) == 0
    assert partial.count(PieceType.TOWER) == 0
    assert partial.size == 7


def test_a_composition_rejects_an_explicit_zero():
    with pytest.raises(ValueError, match="omit it instead"):
        ArmyComposition(
            composition_id="broken",
            counts={PieceType.MILITIA: 0, PieceType.FLAG: 1},
        )


def test_a_composition_must_field_exactly_one_flag():
    with pytest.raises(ValueError, match="exactly one Flag"):
        ArmyComposition(composition_id="broken", counts={PieceType.MILITIA: 3})
    with pytest.raises(ValueError, match="exactly one Flag"):
        ArmyComposition(
            composition_id="broken",
            counts={PieceType.FLAG: 2, PieceType.MILITIA: 3},
        )


def test_army_count_no_longer_lives_on_the_piece():
    # How many of a piece an army fields is an ArmyComposition question since
    # major 2: a count on the enum would be a single global army by
    # construction, which two live rulesets cannot have.
    assert not hasattr(PieceType.MILITIA, "army_count")


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

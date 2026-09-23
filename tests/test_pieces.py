"""Tests for static piece domain data: symbols, ranks, and the army composition."""

import pytest

from capture_the_flag.pieces import (
    ARMY_COMPOSITIONS,
    STANDARD_ARMY,
    ArmyComposition,
    Mobility,
    PieceType,
)

# Per-rank quantities from doc/ruleset/rules.md Section 2.2.
EXPECTED_COUNTS = {
    PieceType.MASTER_OF_ARMS: 3,
    PieceType.CHAMPION: 3,
    PieceType.FOOT_SOLDIER: 3,
    PieceType.MILITIA: 3,
    PieceType.PEASANT: 3,
    PieceType.FLAG: 1,
}


def test_standard_army_sums_to_16():
    assert STANDARD_ARMY.size == 16
    assert sum(STANDARD_ARMY.counts.values()) == 16


def test_per_rank_counts_match_rules_table():
    assert STANDARD_ARMY.counts == EXPECTED_COUNTS
    for piece, count in EXPECTED_COUNTS.items():
        assert STANDARD_ARMY.count(piece) == count


def test_the_standard_army_is_the_only_registered_composition():
    # Major 3 publishes one army; nothing omits a rank, unlike major 2's several
    # compositions.
    assert ARMY_COMPOSITIONS == {"standard_army": STANDARD_ARMY}


def test_count_is_zero_for_a_piece_the_army_does_not_field():
    # A composition names what it fields; every other type has a count of 0
    # rather than being an error to ask about.
    partial = ArmyComposition(
        composition_id="ranks_1_and_2_only",
        counts={
            PieceType.MASTER_OF_ARMS: 3,
            PieceType.CHAMPION: 3,
            PieceType.FLAG: 1,
        },
    )
    assert partial.count(PieceType.MILITIA) == 0
    assert partial.count(PieceType.PEASANT) == 0
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
    # How many of a piece an army fields is an ArmyComposition question, not a
    # property of the enum: a count on the enum would be a single global army by
    # construction, which two live rulesets could not share.
    assert not hasattr(PieceType.MILITIA, "army_count")


def test_numbered_pieces_have_strict_rank_order():
    ranks = sorted(piece.rank for piece in PieceType if piece.rank is not None)
    assert ranks == list(range(1, 6))


def test_master_of_arms_is_the_strongest_rank():
    # Since major 3, rank 5 is the top rank -- the reverse of major 2's rank 1
    # (rules.md Section 2.2).
    assert PieceType.MASTER_OF_ARMS.rank == 5
    assert PieceType.PEASANT.rank == 1


def test_only_the_flag_has_no_rank():
    assert PieceType.FLAG.rank is None
    assert all(
        piece.rank is not None for piece in PieceType if piece is not PieceType.FLAG
    )


def test_mobility_categories():
    assert PieceType.FLAG.mobility is Mobility.IMMOBILE

    others = set(PieceType) - {PieceType.FLAG}
    assert all(piece.mobility is Mobility.MOBILE for piece in others)


def test_symbols_are_unique_and_match_notation_spec():
    symbols = {piece.symbol for piece in PieceType}
    assert len(symbols) == len(PieceType)
    assert symbols == set("12345") | {"F"}


def test_down_rank_is_one_rank_below_each_numbered_piece():
    # The rank-reduction relation (rules.md Section 4.3, formation loss): the
    # piece a surviving attacker or defender becomes after combat reduces it.
    for piece in PieceType:
        if piece.rank is None or piece.rank == 1:
            continue
        reduced = next(p for p in PieceType if p.rank == piece.rank - 1)
        assert piece.down_rank == reduced.rank


def test_the_weakest_numbered_piece_and_the_flag_have_no_down_rank():
    # A rank-1 piece never survives combat as a reduced piece (there is nothing
    # weaker to become), and the Flag never enters combat as a combatant at all.
    assert PieceType.PEASANT.down_rank is None
    assert PieceType.FLAG.down_rank is None


def test_reduced_returns_the_piece_one_rank_below():
    assert PieceType.MASTER_OF_ARMS.reduced() is PieceType.CHAMPION
    assert PieceType.CHAMPION.reduced() is PieceType.FOOT_SOLDIER
    assert PieceType.FOOT_SOLDIER.reduced() is PieceType.MILITIA
    assert PieceType.MILITIA.reduced() is PieceType.PEASANT


def test_reduced_asserts_on_a_piece_with_no_rank_below():
    with pytest.raises(AssertionError):
        PieceType.PEASANT.reduced()
    with pytest.raises(AssertionError):
        PieceType.FLAG.reduced()

"""Tests for `GameSetup`: the board and army pairing, and which pairings are
playable at all (rules.md Section 2)."""

import dataclasses

import pytest

from capture_the_flag.board import SIMPLE_64, BoardLayout
from capture_the_flag.game_setup import (
    PRE_RELEASE_SETUP,
    GameSetup,
    resolve_setup,
    setup_for_ruleset,
)
from capture_the_flag.pieces import STANDARD_ARMY, ArmyComposition, PieceType
from capture_the_flag.record import RulesetConfiguration, active_configuration

_SMALL_BOARD = BoardLayout(
    layout_id="small",
    columns=4,
    rows=8,
    home_rows=2,  # 8 home squares per side
)


def test_pre_release_setup_pairs_the_board_and_army():
    assert PRE_RELEASE_SETUP.layout is SIMPLE_64
    assert PRE_RELEASE_SETUP.composition is STANDARD_ARMY
    # 16 pieces into 16 home squares: the home zone is completely full, since
    # major 3's army must fill it exactly rather than merely fit (rules.md
    # Section 2).
    assert PRE_RELEASE_SETUP.composition.size == len(SIMPLE_64.white_home_squares)


def test_an_army_that_underfills_its_home_zone_is_rejected():
    too_few = ArmyComposition(
        composition_id="seven_pieces",
        counts={PieceType.MASTER_OF_ARMS: 6, PieceType.FLAG: 1},
    )
    with pytest.raises(ValueError, match="does not fill"):
        GameSetup(layout=_SMALL_BOARD, composition=too_few)


def test_an_army_that_overflows_its_home_zone_is_rejected():
    too_many = ArmyComposition(
        composition_id="nine_pieces",
        counts={PieceType.MASTER_OF_ARMS: 8, PieceType.FLAG: 1},
    )
    with pytest.raises(ValueError, match="does not fill"):
        GameSetup(layout=_SMALL_BOARD, composition=too_many)


def test_an_army_exactly_filling_its_home_zone_is_allowed():
    exact = ArmyComposition(
        composition_id="eight_pieces",
        counts={PieceType.MASTER_OF_ARMS: 7, PieceType.FLAG: 1},
    )
    setup = GameSetup(layout=_SMALL_BOARD, composition=exact)
    assert setup.composition.size == len(_SMALL_BOARD.white_home_squares)


def test_resolve_setup_builds_what_the_active_edition_names():
    setup = resolve_setup(active_configuration("3-0:PRE-RELEASE"))
    assert setup == PRE_RELEASE_SETUP
    assert setup.layout.layout_id == "simple_64"
    assert setup.composition.composition_id == "standard_army"


def test_resolve_setup_refuses_a_historical_edition():
    # Not because the id is unknown — `1-2:PRE-RELEASE` is in the table so a
    # stamped artifact still names something real — but because it is not Active:
    # the rules changed, so playing it now would not be playing what it meant.
    with pytest.raises(ValueError, match="historical edition"):
        resolve_setup(RulesetConfiguration("1-2:PRE-RELEASE"))


def test_resolve_setup_refuses_an_edition_it_has_never_heard_of():
    with pytest.raises(ValueError, match="not an edition this code knows"):
        resolve_setup(RulesetConfiguration("9-9:BERSERKER"))


def test_resolve_setup_refuses_any_flag_deviation():
    # Major 3 publishes no flags at all (`record.RULE_FLAGS`) -- the board and
    # army are each a single value named directly by the edition -- so a
    # configuration naming a flag, any flag, is beyond this build.
    configuration = RulesetConfiguration(
        "3-0:PRE-RELEASE", {"BOARD_LAYOUT": "standard_64"}
    )
    with pytest.raises(ValueError, match="no such flag"):
        resolve_setup(configuration)


def test_a_ruleset_name_resolves_to_its_current_edition():
    setup = setup_for_ruleset("PRE-RELEASE")
    assert setup.stamp.edition == "3-0:PRE-RELEASE"
    assert setup == PRE_RELEASE_SETUP


def test_a_ruleset_name_is_matched_case_insensitively():
    assert setup_for_ruleset("pre-release") == setup_for_ruleset("PRE-RELEASE")


def test_an_unknown_ruleset_name_names_the_live_ones():
    with pytest.raises(ValueError, match="unknown ruleset 'BERSERKER'"):
        setup_for_ruleset("BERSERKER")


def test_a_resolved_setup_carries_what_to_stamp_it_as():
    assert PRE_RELEASE_SETUP.stamp.render() == "3-0:PRE-RELEASE"


def test_a_hand_built_setup_has_nothing_to_stamp_itself_as():
    # Not every playable pairing is a published one: it plays, but it cannot be
    # recorded, because there is no honest thing to write in the Ruleset tag.
    ad_hoc = GameSetup(
        layout=_SMALL_BOARD,
        composition=ArmyComposition(
            composition_id="eight_pieces",
            counts={PieceType.MASTER_OF_ARMS: 7, PieceType.FLAG: 1},
        ),
    )
    assert ad_hoc.configuration is None
    with pytest.raises(ValueError, match="nothing to stamp it as"):
        _ = ad_hoc.stamp


def test_a_setup_cannot_carry_a_configuration_that_describes_another_game():
    # A setup whose configuration resolves to a different board or army must
    # not exist: `3-0:PRE-RELEASE` resolves to `simple_64` / `standard_army`, so
    # a setup naming some other pairing under that stamp would record every
    # game as having been played under rules it was not.
    other_army = ArmyComposition(
        composition_id="other_army",
        counts={PieceType.MASTER_OF_ARMS: 15, PieceType.FLAG: 1},
    )
    with pytest.raises(ValueError, match="cannot be stamped '3-0:PRE-RELEASE'"):
        dataclasses.replace(PRE_RELEASE_SETUP, composition=other_army)

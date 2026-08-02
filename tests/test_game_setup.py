"""Tests for `GameSetup`: the board and army pairing, and which pairings are
playable at all (rules.md Appendix A, "Combining these two")."""

import pytest

from capture_the_flag.board import STANDARD_144, BoardLayout
from capture_the_flag.game_setup import (
    BATTLE_SETUP,
    GameSetup,
    resolve_setup,
    setup_for_ruleset,
)
from capture_the_flag.pieces import STANDARD_BATTLE, ArmyComposition, PieceType
from capture_the_flag.record import (
    RulesetConfiguration,
    active_configuration,
    unsupported_aspects,
)

_SMALL_BOARD = BoardLayout(
    layout_id="small",
    columns=4,
    rows=8,
    home_rows=2,  # 8 home squares per side
    lake_rows=(4, 5),
    lake_pattern=(False, True, True, False),
)


def test_battle_setup_pairs_the_battle_board_and_army():
    assert BATTLE_SETUP.layout is STANDARD_144
    assert BATTLE_SETUP.composition is STANDARD_BATTLE
    # 25 pieces into 48 home squares, so the home zone is not full and a player
    # has a choice of which squares to occupy (rules.md Section 2.1).
    assert BATTLE_SETUP.composition.size < len(STANDARD_144.white_home_squares)


def test_an_army_that_does_not_fit_its_home_zone_is_rejected():
    # The shape of the invalid combination the rules name: an army must fit one
    # piece per home square. `standard_battle` on `standard_64` is this case
    # (25 pieces, 24 squares); here it is 9 into 8.
    too_big = ArmyComposition(
        composition_id="nine_pieces",
        counts={PieceType.MASTER_OF_ARMS: 8, PieceType.FLAG: 1},
    )
    with pytest.raises(ValueError, match="does not fit"):
        GameSetup(layout=_SMALL_BOARD, composition=too_big)


def test_an_army_exactly_filling_its_home_zone_is_allowed():
    # Exactly filling is playable, if joyless: every square is occupied, so
    # placement offers no choice. The rules bar an army that cannot fit, not one
    # that fits with nothing to spare.
    exact = ArmyComposition(
        composition_id="eight_pieces",
        counts={PieceType.MASTER_OF_ARMS: 7, PieceType.FLAG: 1},
    )
    setup = GameSetup(layout=_SMALL_BOARD, composition=exact)
    assert setup.composition.size == len(_SMALL_BOARD.white_home_squares)


def test_resolve_setup_builds_what_the_active_edition_names():
    setup = resolve_setup(active_configuration("2-0:BATTLE"))
    assert setup == BATTLE_SETUP
    assert setup.layout.layout_id == "standard_144"
    assert setup.composition.composition_id == "standard_battle"


def test_resolve_setup_refuses_a_historical_edition():
    # Not because the id is unknown — `1-2:PRE-RELEASE` is in the table so a
    # stamped artifact still names something real — but because it is not Active:
    # the rules changed, so playing it now would not be playing what it meant.
    with pytest.raises(ValueError, match="historical edition"):
        resolve_setup(RulesetConfiguration("1-2:PRE-RELEASE"))


def test_resolve_setup_refuses_an_edition_it_has_never_heard_of():
    with pytest.raises(ValueError, match="not an edition this code knows"):
        resolve_setup(RulesetConfiguration("9-9:BERSERKER"))


def test_resolve_setup_refuses_a_published_label_this_build_cannot_play():
    # `standard_64` is published in Appendix A and is a legitimate value of a
    # real flag — `unsupported_aspects` is right not to object to it. It is the
    # *build* that has no board for it yet, which is a different failure and gets
    # its own message.
    configuration = RulesetConfiguration(
        "2-0:BATTLE", {"BOARD_LAYOUT": "standard_64"}
    )
    assert unsupported_aspects(configuration) == []
    with pytest.raises(ValueError, match="implements no BOARD_LAYOUT 'standard_64'"):
        resolve_setup(configuration)


def test_a_deviating_flag_actually_changes_what_is_resolved():
    # The mechanism the flag model rests on: a configuration that deviates from
    # its edition resolves to something different. Exercised through the army,
    # since both published compositions are labels the flag knows.
    deviating = RulesetConfiguration(
        "2-0:BATTLE", {"ARMY_COMPOSITION": "standard_skirmish"}
    )
    with pytest.raises(ValueError, match="ARMY_COMPOSITION 'standard_skirmish'"):
        resolve_setup(deviating)


def test_a_ruleset_name_resolves_to_its_current_edition():
    # The pointer the vocabulary describes: a ruleset name is mutable, an edition
    # is not, so `BATTLE` means whichever `<major>-<minor>:BATTLE` is Active now.
    setup = setup_for_ruleset("BATTLE")
    assert setup.stamp.edition == "2-0:BATTLE"
    assert setup == BATTLE_SETUP


def test_a_ruleset_name_is_matched_case_insensitively():
    assert setup_for_ruleset("battle") == setup_for_ruleset("BATTLE")


def test_an_unknown_ruleset_name_names_the_live_ones():
    with pytest.raises(ValueError, match="unknown ruleset 'skirmish'"):
        setup_for_ruleset("skirmish")


def test_a_resolved_setup_carries_what_to_stamp_it_as():
    assert BATTLE_SETUP.stamp.render() == "2-0:BATTLE"


def test_a_hand_built_setup_has_nothing_to_stamp_itself_as():
    # A board and an army are independent flags, so a playable pairing can exist
    # that no published edition names. It plays; it cannot be recorded, because
    # there is no honest thing to write in the Ruleset tag.
    ad_hoc = GameSetup(
        layout=_SMALL_BOARD,
        composition=ArmyComposition(
            composition_id="two_pieces",
            counts={PieceType.MASTER_OF_ARMS: 1, PieceType.FLAG: 1},
        ),
    )
    assert ad_hoc.configuration is None
    with pytest.raises(ValueError, match="nothing to stamp it as"):
        _ = ad_hoc.stamp

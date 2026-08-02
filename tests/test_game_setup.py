"""Tests for `GameSetup`: the board and army pairing, and which pairings are
playable at all (rules.md Appendix A, "Combining these two")."""

import pytest

from capture_the_flag.board import STANDARD_144, BoardLayout
from capture_the_flag.game_setup import BATTLE_SETUP, GameSetup
from capture_the_flag.pieces import STANDARD_BATTLE, ArmyComposition, PieceType

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

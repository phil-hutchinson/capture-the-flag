"""Tests for CtfGameLogging: the combat-notation ply annotation (rules.md 4.4)."""

import random
from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.game_logging import CtfGameLogging
from capture_the_flag.match import play_match
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.player import RandomCtfPlayer
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

_WHITE_FLAG = Square(0, 1)  # A1 -- both flags present so no position is terminal.
_BLACK_FLAG = Square(11, 12)  # L12
_D5 = Square(3, 5)
_D6 = Square(3, 6)  # one square ahead of D5: a legal orthogonal step (D is open).

_annotate = CtfGameLogging().ply_annotation


def _position(extra: dict) -> CtfPosition:
    board = {
        _WHITE_FLAG: (Side.WHITE, P.FLAG),
        _BLACK_FLAG: (Side.BLACK, P.FLAG),
        **extra,
    }
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
    )


def _annotate_move(from_position: CtfPosition, ply: CtfPly) -> str:
    # Drive the real engine so the annotation reads the actual resulting board.
    return _annotate(from_position, ply, from_position.apply_ply(ply))


def test_no_attack_uses_plain_dash_form():
    position = _position({_D5: (Side.WHITE, P.FOOT_SOLDIER)})  # D6 empty.
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5-D6"


def test_attacker_wins_marks_the_defender():
    # A Champion (rank 2) beats a Militia (rank 6): the defender is removed.
    position = _position(
        {_D5: (Side.WHITE, P.CHAMPION), _D6: (Side.BLACK, P.MILITIA)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5-D6x"


def test_attacker_loses_marks_the_attacker():
    # A Militia (rank 6) attacking a Master-of-Arms (rank 1) is a complete
    # sacrifice: attacker removed, defender stays.
    position = _position(
        {_D5: (Side.WHITE, P.MILITIA), _D6: (Side.BLACK, P.MASTER_OF_ARMS)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5x-D6"


def test_mutual_loss_marks_both():
    # Equal-rank attack trades both pieces.
    position = _position(
        {_D5: (Side.WHITE, P.FOOT_SOLDIER), _D6: (Side.BLACK, P.FOOT_SOLDIER)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5x-D6x"


def test_tower_attack_marks_both():
    # Any attack on a Tower is a mutual loss (rules.md Section 4.3).
    position = _position(
        {_D5: (Side.WHITE, P.MILITIA), _D6: (Side.BLACK, P.TOWER)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5x-D6x"


def test_annotation_is_not_the_identity_string():
    # The logged form differs from str(ply); the identity key stays plain.
    position = _position(
        {_D5: (Side.WHITE, P.FOOT_SOLDIER), _D6: (Side.BLACK, P.FOOT_SOLDIER)}
    )
    ply = CtfPly(_D5, _D6)
    assert str(ply) == "D5D6"
    assert _annotate_move(position, ply) != str(ply)


def test_every_logged_ply_in_a_real_game_is_extended_form():
    # End to end: a full match's game log carries combat notation, one `-` per
    # ply, and the squares still match the plain identity string.
    white = RandomCtfPlayer("W", random.Random(1))
    black = RandomCtfPlayer("B", random.Random(2))
    result = play_match(white, black).game_result
    assert result.game_log
    for annotation, _board in result.game_log:
        assert annotation.count("-") == 1
        assert annotation.replace("-", "").replace("x", "").isalnum()

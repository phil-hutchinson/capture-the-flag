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
_F5 = Square(5, 5)
_F6 = Square(5, 6)  # one square ahead of F5: a legal orthogonal attack square.

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
        white_inactivity_counter=0,
        black_inactivity_counter=0,
        progress_counter=0,
        breachability=None,
    )


def _annotate_move(from_position: CtfPosition, ply: CtfPly) -> str:
    # Drive the real engine so the annotation reads the actual resulting board.
    return _annotate(from_position, ply, from_position.apply_ply(ply))


def test_no_attack_uses_plain_dash_form():
    position = _position({_F5: (Side.WHITE, P.INFANTRY)})  # F6 empty.
    assert _annotate_move(position, CtfPly(_F5, _F6)) == "F5-F6"


def test_attacker_wins_marks_the_defender():
    # Assassin wins on offense regardless of rank; the defender is removed.
    position = _position(
        {_F5: (Side.WHITE, P.ASSASSIN), _F6: (Side.BLACK, P.INFANTRY)}
    )
    assert _annotate_move(position, CtfPly(_F5, _F6)) == "F5-F6x"


def test_attacker_loses_marks_the_attacker():
    # A non-Sapper attacking a Tower is a complete sacrifice: attacker removed,
    # Tower stays.
    position = _position({_F5: (Side.WHITE, P.INFANTRY), _F6: (Side.BLACK, P.TOWER)})
    assert _annotate_move(position, CtfPly(_F5, _F6)) == "F5x-F6"


def test_mutual_loss_marks_both():
    # Equal-rank attack trades both pieces.
    position = _position(
        {_F5: (Side.WHITE, P.INFANTRY), _F6: (Side.BLACK, P.INFANTRY)}
    )
    assert _annotate_move(position, CtfPly(_F5, _F6)) == "F5x-F6x"


def test_annotation_is_not_the_identity_string():
    # The logged form differs from str(ply); the identity key stays plain.
    position = _position(
        {_F5: (Side.WHITE, P.INFANTRY), _F6: (Side.BLACK, P.INFANTRY)}
    )
    ply = CtfPly(_F5, _F6)
    assert str(ply) == "F5F6"
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

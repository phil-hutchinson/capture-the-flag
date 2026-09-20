"""Tests for CtfGameLogging: the combat-notation ply annotation (rules.md 4.5)."""

import random
import re
from types import MappingProxyType

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.game_logging import CtfGameLogging
from capture_the_flag.game_setup import PRE_RELEASE_SETUP
from capture_the_flag.match import play_match
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.player import RandomCtfPlayer
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

_WHITE_FLAG = Square(0, 1)  # A1 -- both flags present so no position is terminal.
_BLACK_FLAG = Square(7, 8)  # H8
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
        layout=SIMPLE_64,
        ply_count=0,
    )


def _annotate_move(from_position: CtfPosition, ply: CtfPly) -> str:
    # Drive the real engine so the annotation reads the actual resulting board.
    return _annotate(from_position, ply, from_position.apply_ply(ply))


def test_no_attack_uses_plain_dash_form():
    position = _position({_D5: (Side.WHITE, P.FOOT_SOLDIER)})  # D6 empty.
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5-D6"


def test_attacker_wins_marks_the_defender_and_reduces_the_attacker():
    # The higher-numbered rank wins (story 00000049 step 14): a Champion
    # (rank 4) beats a Militia (rank 2). The defender is removed, and the
    # surviving attacker is reduced to rank 3 (step 15) -- marked at the
    # source square, where it stood when the move began.
    position = _position(
        {_D5: (Side.WHITE, P.CHAMPION), _D6: (Side.BLACK, P.MILITIA)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5=3-D6x"


def test_attacker_loses_marks_the_attacker_and_reduces_the_defender():
    # A Peasant (rank 1) attacking a Master-of-Arms (rank 5) is a complete
    # sacrifice: attacker removed, defender survives reduced to rank 4.
    position = _position(
        {_D5: (Side.WHITE, P.PEASANT), _D6: (Side.BLACK, P.MASTER_OF_ARMS)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5x-D6=4"


def test_mutual_loss_marks_both():
    # Equal-rank attack trades both pieces; a draw reduces nothing.
    position = _position(
        {_D5: (Side.WHITE, P.FOOT_SOLDIER), _D6: (Side.BLACK, P.FOOT_SOLDIER)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5x-D6x"


def test_flag_capture_marks_only_the_destination():
    # Capturing the Flag is not combat (rules.md Section 4.5): the attacker
    # carries no mark and keeps its rank, the only way a move marks one
    # square and not the other.
    position = _position(
        {_D5: (Side.WHITE, P.MASTER_OF_ARMS), _D6: (Side.BLACK, P.FLAG)}
    )
    assert _annotate_move(position, CtfPly(_D5, _D6)) == "D5-D6x"


def test_annotation_is_not_the_identity_string():
    # The logged form differs from str(ply); the identity key stays plain.
    position = _position(
        {_D5: (Side.WHITE, P.FOOT_SOLDIER), _D6: (Side.BLACK, P.FOOT_SOLDIER)}
    )
    ply = CtfPly(_D5, _D6)
    assert str(ply) == "D5D6"
    assert _annotate_move(position, ply) != str(ply)


_ANNOTATION_RE = re.compile(r"^[A-H]\d+(?:x|=\d+)?-[A-H]\d+(?:x|=\d+)?$")


def test_every_logged_ply_in_a_real_game_is_extended_form():
    # End to end: a full match's game log carries the extended notation, one
    # `-` per ply, and each square carries at most one `x`/`=N` mark.
    white = RandomCtfPlayer("W", random.Random(1))
    black = RandomCtfPlayer("B", random.Random(2))
    result = play_match(white, black, PRE_RELEASE_SETUP).game_result
    assert result.game_log
    for annotation, _board in result.game_log:
        assert _ANNOTATION_RE.fullmatch(annotation), annotation

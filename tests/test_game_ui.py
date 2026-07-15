"""Tests for simple-notation ply parsing and the interactive move prompt."""

from types import MappingProxyType

import pytest

from capture_the_flag.board import Square
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly, parse_ply
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


def _position(board: dict, side_to_move: Side = Side.WHITE) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=0,
    )


class _ScriptedUI:
    """A `CtfGameUI` fed scripted input, recording prompts and messages."""

    def __init__(self, inputs: list[str]) -> None:
        self.prompts: list[str] = []
        self.messages: list[str] = []
        inputs_iter = iter(inputs)

        def input_fn(prompt: str) -> str:
            self.prompts.append(prompt)
            return next(inputs_iter)

        self.ui = CtfGameUI(input_fn=input_fn, print_fn=self.messages.append)


def test_parse_ply_is_the_inverse_of_str():
    for text in ["A2A3", "A10L12", "D2C2", "L1L2"]:
        assert str(parse_ply(text)) == text


def test_parse_ply_rejects_malformed_text():
    for text in ["", "A2", "A2A", "M2A3", "A2 A3", "A0A1", "A13A12"]:
        with pytest.raises(ValueError):
            parse_ply(text)


def test_legal_move_is_returned_and_prompt_names_the_side():
    scripted = _ScriptedUI(["d2d3"])  # lowercase is accepted
    position = _position({Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)})
    ply = scripted.ui.get_next_ply(position)
    assert ply == CtfPly(Square(3, 2), Square(3, 3))
    assert "White to move" in scripted.prompts[0]
    assert scripted.messages == []


def test_malformed_input_reprompts_with_a_message():
    scripted = _ScriptedUI(["banana", "D2D3"])
    position = _position({Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)})
    ply = scripted.ui.get_next_ply(position)
    assert ply == CtfPly(Square(3, 2), Square(3, 3))
    assert len(scripted.messages) == 1
    assert "Malformed move" in scripted.messages[0]


def test_illegal_moves_reprompt_naming_the_problem():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(0, 12): (Side.BLACK, P.MILITIA),
    }
    # D2D5 is three squares — too far even for an unencumbered piece.
    scripted = _ScriptedUI(["E5E6", "A12A11", "D2D5", "D2D3"])
    ply = scripted.ui.get_next_ply(_position(board))
    assert ply == CtfPly(Square(3, 2), Square(3, 3))
    assert scripted.messages == [
        "Illegal move: no piece on E5.",
        "Illegal move: the piece on A12 is not yours.",
        "Illegal move: your Foot Soldier on D2 cannot move to D5.",
    ]


def test_rejection_does_not_disturb_the_position():
    position = _position({Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)})
    before = (dict(position.board), position.side_to_move)
    scripted = _ScriptedUI(["nonsense", "E5E6", "D2D3"])
    scripted.ui.get_next_ply(position)
    assert (dict(position.board), position.side_to_move) == before

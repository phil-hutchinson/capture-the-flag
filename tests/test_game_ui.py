"""Tests for simple-notation ply parsing and the interactive move prompt."""

from types import MappingProxyType

import pytest

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.game_setup import PRE_RELEASE_SETUP
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly, parse_ply
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


def _position(
    board: dict, side_to_move: Side = Side.WHITE, ply_count: int = 0
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=0,
        layout=SIMPLE_64,
        ply_count=ply_count,
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

        self.ui = CtfGameUI(
            PRE_RELEASE_SETUP, input_fn=input_fn, print_fn=self.messages.append
        )


def test_parse_ply_is_the_inverse_of_str():
    for text in ["A2A3", "A10L12", "D2C2", "L1L2"]:
        assert str(parse_ply(text)) == text


def test_parse_ply_rejects_malformed_text():
    # Row 0 and a non-letter column are malformed notation; an off-board but
    # well-formed square (A13 on a 12-row board) is not the parser's business
    # and is rejected downstream as an illegal move.
    for text in ["", "A2", "A2A", "2A A3", "A2 A3", "A0A1"]:
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
        Square(0, 8): (Side.BLACK, P.MILITIA),
    }
    # D2D5 is three squares — too far even for an unencumbered piece.
    scripted = _ScriptedUI(["E5E6", "A8A7", "D2D5", "D2D3"])
    ply = scripted.ui.get_next_ply(_position(board))
    assert ply == CtfPly(Square(3, 2), Square(3, 3))
    assert scripted.messages == [
        "Illegal move: no piece on E5.",
        "Illegal move: the piece on A8 is not yours.",
        "Illegal move: your Foot Soldier on D2 cannot move to D5.",
    ]


def test_diagonal_onto_an_empty_square_names_the_attack_only_rule():
    board = {Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)}
    scripted = _ScriptedUI(["D2E3", "D2D3"])
    scripted.ui.get_next_ply(_position(board, ply_count=1))
    assert scripted.messages == [
        "Illegal move: your Foot Soldier on D2 can only move diagonally to "
        "attack, and E3 is empty (Section 4.4)."
    ]


def test_closed_diagonal_names_the_two_squares_that_close_it():
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 3): (Side.BLACK, P.MILITIA),  # E3, the target
        Square(4, 2): (Side.BLACK, P.PEASANT),  # E2, one flank
        Square(3, 3): (Side.WHITE, P.PEASANT),  # D3, the other — either side closes
    }
    scripted = _ScriptedUI(["D2E3", "D2C2"])
    scripted.ui.get_next_ply(_position(board, ply_count=1))
    assert scripted.messages == [
        "Illegal move: your Foot Soldier on D2 cannot attack E3 diagonally: "
        "the path is closed — a diagonal attack needs E2 or D3 empty, and both "
        "are occupied (Section 4.4)."
    ]


def test_encumbered_two_square_move_names_the_direction_it_applies_to():
    # The Militia on E3 is north-east of D2, which encumbers north only: D2D4
    # is refused while the path through D3 is empty and D2B2 is still legal.
    board = {
        Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
        Square(4, 3): (Side.BLACK, P.MILITIA),
    }
    scripted = _ScriptedUI(["D2D4", "D2B2"])
    ply = scripted.ui.get_next_ply(_position(board, ply_count=1))
    assert ply == CtfPly(Square(3, 2), Square(1, 2))
    assert len(scripted.messages) == 1
    assert "it is encumbered in that direction" in scripted.messages[0]
    assert "Its other directions are unaffected." in scripted.messages[0]


def test_first_ply_two_square_move_names_the_opening_restriction():
    # Unencumbered and with a clear path: only the first-move rule refuses it,
    # and the same ply is legal once the game is under way.
    board = {Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)}
    scripted = _ScriptedUI(["D2D4", "D2D3"])
    scripted.ui.get_next_ply(_position(board, ply_count=0))
    assert scripted.messages == [
        "Illegal move: your Foot Soldier on D2 cannot move two squares to D4: "
        "White's first move of the game is limited to one square (Section 4.1)."
    ]
    assert CtfPly(Square(3, 2), Square(3, 4)) in _position(
        board, ply_count=1
    ).legal_plies


def test_rejection_does_not_disturb_the_position():
    position = _position({Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER)})
    before = (dict(position.board), position.side_to_move)
    scripted = _ScriptedUI(["nonsense", "E5E6", "D2D3"])
    scripted.ui.get_next_ply(position)
    assert (dict(position.board), position.side_to_move) == before

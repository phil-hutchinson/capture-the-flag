"""Tests for the human player seat (scripted input)."""

from types import MappingProxyType

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.game_setup import PRE_RELEASE_SETUP
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.pieces import PieceType
from capture_the_flag.player import CtfPlayer, HumanCtfPlayer
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


class _ScriptedPlayer:
    """A `HumanCtfPlayer` fed scripted input, recording prompts and messages."""

    def __init__(self, ui_inputs: list[str]) -> None:
        self.prompts: list[str] = []
        self.messages: list[str] = []
        inputs_iter = iter(ui_inputs)

        def input_fn(prompt: str) -> str:
            self.prompts.append(prompt)
            return next(inputs_iter)

        ui = CtfGameUI(
            PRE_RELEASE_SETUP, input_fn=input_fn, print_fn=self.messages.append
        )
        self.player = HumanCtfPlayer(
            "Alice",
            ui,
            input_fn=input_fn,
            print_fn=self.messages.append,
        )


def test_human_player_satisfies_the_ctf_player_protocol():
    player: CtfPlayer = _ScriptedPlayer([]).player
    assert player.name == "Alice"
    assert player.render_before_ply is True


def test_select_ply_delegates_to_the_ui_prompt():
    position = CtfPosition(
        board=MappingProxyType({Square(3, 2): (Side.WHITE, PieceType.FOOT_SOLDIER)}),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=SIMPLE_64,
    )
    scripted = _ScriptedPlayer(["D2D3"])
    assert scripted.player.select_ply(position) == CtfPly(Square(3, 2), Square(3, 3))
    assert "White to move" in scripted.prompts[0]

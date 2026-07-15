"""Tests for the human player seat (scripted input)."""

from types import MappingProxyType

from capture_the_flag.board import BLACK_HOME_SQUARES, WHITE_HOME_SQUARES, Square
from capture_the_flag.game_ui import CtfGameUI
from capture_the_flag.pieces import ARMY_ROSTER, PieceType
from capture_the_flag.placement_file import parse_placement_file
from capture_the_flag.player import CtfPlayer, HumanCtfPlayer
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

# Same 4x12 fixture shape as test_placement_file: a valid 25-piece setup with
# `-` empty squares padding the grid to a full 4 rows of 12.
VALID_TEXT = "\n".join(
    [
        "123456123456",
        "123456------",
        "T-T-T-T-T-T-",
        "-----------F",
    ]
)


class _ScriptedPlayer:
    """A `HumanCtfPlayer` fed scripted input, recording prompts and messages."""

    def __init__(self, inputs: list[str], placement_dir, ui_inputs=()) -> None:
        self.prompts: list[str] = []
        self.messages: list[str] = []
        inputs_iter = iter(list(inputs) + list(ui_inputs))

        def input_fn(prompt: str) -> str:
            self.prompts.append(prompt)
            return next(inputs_iter)

        ui = CtfGameUI(input_fn=input_fn, print_fn=self.messages.append)
        self.player = HumanCtfPlayer(
            "Alice",
            ui,
            placement_dir=placement_dir,
            input_fn=input_fn,
            print_fn=self.messages.append,
        )


def test_human_player_satisfies_the_ctf_player_protocol(tmp_path):
    player: CtfPlayer = _ScriptedPlayer([], tmp_path).player
    assert player.name == "Alice"
    assert player.render_before_ply is True


def test_bad_file_names_reprompt_until_a_valid_file(tmp_path):
    (tmp_path / "good.txt").write_text(VALID_TEXT, encoding="utf-8")
    (tmp_path / "bad.txt").write_text("not a placement", encoding="utf-8")
    scripted = _ScriptedPlayer(["missing.txt", "bad.txt", "good.txt"], tmp_path)

    placement = scripted.player.get_placement(Side.WHITE)

    assert placement == parse_placement_file(VALID_TEXT, Side.WHITE)
    assert "No placement file named 'missing.txt'" in scripted.messages[0]
    assert "Expected 4 rows" in scripted.messages[1]
    assert "Alice (White)" in scripted.prompts[0]


def test_accepted_placement_clears_the_screen(tmp_path):
    scripted = _ScriptedPlayer(["random"], tmp_path)
    scripted.player.get_placement(Side.WHITE)
    # The typed dialogue is wiped so the opponent never sees the file name.
    assert scripted.messages[-1].startswith("\033[2J\033[H")
    assert "Alice's placement is locked in." in scripted.messages[-1]


def test_random_request_yields_a_legal_placement(tmp_path):
    for text, side, home in [
        ("random", Side.WHITE, WHITE_HOME_SQUARES),
        ("RANDOM", Side.BLACK, BLACK_HOME_SQUARES),
    ]:
        placement = _ScriptedPlayer([text], tmp_path).player.get_placement(side)
        assert placement.keys() <= home  # 25 of the 48 home squares filled
        assert len(placement) == 25
        counts: dict[PieceType, int] = {}
        for piece in placement.values():
            counts[piece] = counts.get(piece, 0) + 1
        assert counts == ARMY_ROSTER


def test_select_ply_delegates_to_the_ui_prompt(tmp_path):
    position = CtfPosition(
        board=MappingProxyType({Square(3, 2): (Side.WHITE, PieceType.FOOT_SOLDIER)}),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
    )
    scripted = _ScriptedPlayer([], tmp_path, ui_inputs=["D2D3"])
    assert scripted.player.select_ply(position) == CtfPly(Square(3, 2), Square(3, 3))
    assert "White to move" in scripted.prompts[0]

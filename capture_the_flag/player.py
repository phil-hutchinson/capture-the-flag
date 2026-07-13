"""The `CtfPlayer` seam (phase-1 placement + phase-2 play) and the random
and human player implementations."""

import random
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from game_engine_core.engines.random_engine import RandomEngine
from game_engine_core.protocols.player import Player

from .game_ui import CtfGameUI
from .placement import Placement, random_placement
from .placement_file import (
    DEFAULT_PLACEMENT_DIR,
    PlacementFileError,
    load_placement_file,
)
from .ply import CtfPly
from .position import CtfPosition
from .side import Side

CLEAR_SCREEN = "\033[2J\033[H"
"""ANSI clear-screen-and-home, printed to wipe the placement dialogue."""


class CtfPlayer(Player[CtfPly, CtfPosition], Protocol):
    """A `Player` that can also produce a phase-1 placement.

    A match wrapper calls `get_placement` for each side before phase 2
    begins, then hands the resulting `CtfPosition` to the library's
    `StandardGame`, which drives `select_ply` as usual.
    """

    def get_placement(self, side: Side) -> Placement:
        """This player's phase-1 home-zone placement for `side`."""
        ...


class RandomCtfPlayer:
    """A `CtfPlayer` that places uniformly at random and moves uniformly at
    random."""

    def __init__(
        self,
        name: str,
        rng: random.Random | None = None,
        render_before_ply: bool = False,
    ) -> None:
        self._name = name
        self._rng = rng if rng is not None else random.Random()
        self._render_before_ply = render_before_ply
        self._engine: RandomEngine[CtfPly, CtfPosition] = RandomEngine()

    @property
    def name(self) -> str:
        return self._name

    @property
    def render_before_ply(self) -> bool:
        return self._render_before_ply

    def get_placement(self, side: Side) -> Placement:
        return random_placement(side, self._rng)

    def select_ply(self, position: CtfPosition) -> CtfPly:
        return self._engine.select_ply(position)


class HumanCtfPlayer:
    """A `CtfPlayer` seat driven by a person at the terminal.

    Placement comes from a placement file named at the prompt — any
    `PlacementFileError` (missing file, malformed file, wrong piece mix) is
    printed and re-prompted — or from typing `random` for a random legal
    placement. Once accepted, the screen is cleared so the typed file name
    (the only secret in the placement dialogue) is not left visible to the
    opponent. Plies are delegated to the shared `CtfGameUI` prompt, and the
    board is rendered before every human turn.

    `input_fn`/`print_fn` default to the builtins; tests inject scripted
    replacements.
    """

    def __init__(
        self,
        name: str,
        game_ui: CtfGameUI,
        placement_dir: Path = DEFAULT_PLACEMENT_DIR,
        rng: random.Random | None = None,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self._name = name
        self._game_ui = game_ui
        self._placement_dir = placement_dir
        self._rng = rng if rng is not None else random.Random()
        self._input = input_fn
        self._print = print_fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def render_before_ply(self) -> bool:
        return True

    def get_placement(self, side: Side) -> Placement:
        prompt = (
            f"{self._name} ({side.name.title()}) — placement file name in "
            f"{self._placement_dir}/, or 'random': "
        )
        while True:
            text = self._input(prompt).strip()
            if text.lower() == "random":
                placement = random_placement(side, self._rng)
                break
            try:
                placement = load_placement_file(text, side, self._placement_dir)
                break
            except PlacementFileError as error:
                self._print(str(error))
        self._print(f"{CLEAR_SCREEN}{self._name}'s placement is locked in.")
        return placement

    def select_ply(self, position: CtfPosition) -> CtfPly:
        return self._game_ui.get_next_ply(position)

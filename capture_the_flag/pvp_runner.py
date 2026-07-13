"""Human-vs-human terminal runner: one complete game, placement to outcome.

Runnable as a module: `python -m capture_the_flag.pvp_runner [options]`.
Wires two `HumanCtfPlayer`s and a shared `CtfGameUI` into `play_match` — the
single-game entry point retained for exactly this purpose (see story
00000005's note on story 00000015) — and announces how the game ended.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path

from game_engine_core.models.game_result import GameResult

from .game_ui import CtfGameUI
from .match import play_match
from .placement_file import DEFAULT_PLACEMENT_DIR
from .player import HumanCtfPlayer


def announce_result(result: GameResult, white_name: str, black_name: str) -> str:
    """The end-of-game announcement: who won (or a draw) and why.

    `result.outcome` is absolute (1 = White won), `result_reason` the ending
    vocabulary from `outcome.py`.
    """
    if result.outcome == 1:
        headline = f"{white_name} (White) wins"
    elif result.outcome == -1:
        headline = f"{black_name} (Black) wins"
    else:
        headline = "Draw"
    return f"{headline} — {result.result_reason}, after {len(result.game_log)} plies."


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play a human-vs-human game of Capture the Flag in the terminal.",
    )
    parser.add_argument(
        "--white",
        default="White",
        help="name of the first-moving player (default: White)",
    )
    parser.add_argument(
        "--black",
        default="Black",
        help="name of the second-moving player (default: Black)",
    )
    parser.add_argument(
        "-p",
        "--placements-dir",
        type=Path,
        default=DEFAULT_PLACEMENT_DIR,
        help="folder placement files are read from (default: ./placements)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    game_ui = CtfGameUI()
    white = HumanCtfPlayer(args.white, game_ui, placement_dir=args.placements_dir)
    black = HumanCtfPlayer(args.black, game_ui, placement_dir=args.placements_dir)
    match_result = play_match(white, black, game_ui=game_ui)
    print()
    print(announce_result(match_result.game_result, args.white, args.black))


if __name__ == "__main__":
    main()

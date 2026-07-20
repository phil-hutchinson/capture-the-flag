"""Single-game terminal runner: any kind of player vs any kind, placement to
outcome.

Runnable as a module: `python -m capture_the_flag.game_runner [options]`. Each
seat's kind (`human`, `random`, or `neural`) is chosen on the command line, so
one runner covers human-vs-human, human-vs-machine, and machine-vs-machine play.

Rendering follows the seats: a human always sees the board before their own ply,
a machine-vs-machine game is rendered throughout so it can be watched, but in a
human-vs-machine game only the human's turns are rendered (the machine's are not,
to avoid drawing the board twice around a move the human didn't make).
"""

import argparse
import random
from collections.abc import Sequence
from pathlib import Path

from game_engine_core.models.game_result import GameResult

from .game_ui import CtfGameUI
from .match import play_match
from .placement_file import DEFAULT_PLACEMENT_DIR
from .player import PLAYER_KINDS, PlayerContext, make_player


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
        description="Play one game of Capture the Flag between any two player kinds.",
    )
    parser.add_argument(
        "--white",
        choices=PLAYER_KINDS,
        default="human",
        help="kind of the first-moving player (default: human)",
    )
    parser.add_argument(
        "--black",
        choices=PLAYER_KINDS,
        default="human",
        help="kind of the second-moving player (default: human)",
    )
    parser.add_argument(
        "--white-name",
        default="White",
        help="display name of the first-moving player (default: White)",
    )
    parser.add_argument(
        "--black-name",
        default="Black",
        help="display name of the second-moving player (default: Black)",
    )
    parser.add_argument(
        "-p",
        "--placements-dir",
        type=Path,
        default=DEFAULT_PLACEMENT_DIR,
        help="folder placement files are read from (default: ./placements)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed placement, random play, and neural network init for reproducibility",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="MCTS iterations per ply for neural players (default: engine default)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="ply-selection temperature for neural players (default: engine default)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)

    rng = None
    if args.seed is not None:
        # Seed the process-global `random` (RandomEngine draws from it) and,
        # when a neural player is seated, torch — so an untrained net's weights
        # are reproducible too.
        random.seed(args.seed)
        rng = random.Random(args.seed)
        if "neural" in (args.white, args.black):
            import torch

            torch.manual_seed(args.seed)

    game_ui = CtfGameUI()
    context = PlayerContext(
        game_ui=game_ui, placements_dir=args.placements_dir, rng=rng
    )
    # Machine seats render only when there is no human in the game (so a
    # machine-vs-machine game is watchable, but a human-vs-machine game renders
    # around the human's turns alone). Human seats always render regardless.
    machine_render = "human" not in (args.white, args.black)

    white = make_player(
        args.white,
        args.white_name,
        context=context,
        render_before_ply=machine_render,
        iterations=args.iterations,
        temperature=args.temperature,
    )
    black = make_player(
        args.black,
        args.black_name,
        context=context,
        render_before_ply=machine_render,
        iterations=args.iterations,
        temperature=args.temperature,
    )

    match_result = play_match(white, black, game_ui=game_ui)
    print()
    print(announce_result(match_result.game_result, args.white_name, args.black_name))


if __name__ == "__main__":
    main()

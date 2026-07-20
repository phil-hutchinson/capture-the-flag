"""Headless batch runner: play many machine-vs-machine matches, write one
game-record file per match, and report a batch summary.

Runnable as a module: `python -m capture_the_flag.batch_runner [options]`. Each
seat's kind is chosen on the command line, restricted to the non-interactive
machine kinds (`random`, `neural`) — there is no UI in a headless batch.
"""

import argparse
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from game_engine_core.tournament.tournament import Tournament

from .game_logging import CtfGameLogging
from .match import build_initial_position
from .player import MACHINE_PLAYER_KINDS, PlayerContext, make_player
from .record import write_record


@dataclass(frozen=True)
class BatchSummary:
    """Outcome tallies, ending-reason breakdown, and game-length statistics."""

    games_played: int
    white_wins: int
    black_wins: int
    draws: int
    min_plies: int
    max_plies: int
    mean_plies: float
    reason_counts: Mapping[str, int]
    """How many games ended for each reason (e.g. `Flag Captured`), the
    game-specific vocabulary from `outcome.py`. Sums to `games_played`."""

    def format(self) -> str:
        # Reasons ordered by frequency, then name, for a stable, readable line.
        reason_breakdown = ", ".join(
            f"{reason}: {count}"
            for reason, count in sorted(
                self.reason_counts.items(), key=lambda item: (-item[1], item[0])
            )
        )
        return (
            f"Games played: {self.games_played}\n"
            f"White wins:   {self.white_wins}\n"
            f"Black wins:   {self.black_wins}\n"
            f"Draws:        {self.draws}\n"
            f"Endings:      {reason_breakdown}\n"
            f"Plies per game — min: {self.min_plies}, "
            f"max: {self.max_plies}, mean: {self.mean_plies:.1f}"
        )


def run_batch(
    num_games: int,
    output_dir: Path,
    seed: int | None = None,
    white_kind: str = "random",
    black_kind: str = "random",
    iterations: int | None = None,
    temperature: float | None = None,
) -> BatchSummary:
    """Play `num_games` matches between the two chosen machine kinds, writing one
    game-record file per match into `output_dir` (created if needed), and return
    the batch summary.

    The batch is a two-player round robin over the shared `Tournament`: the two
    players meet `num_games` times, and `Tournament` alternates which of them
    moves first (holds White) from game to game, so `white_wins` / `black_wins`
    below count first-mover / second-mover wins rather than a fixed player.
    Phase-1 placement is supplied through the widened position factory
    (`build_initial_position`); scheduling, side alternation, and the game loop
    all come from `Tournament`.

    `white_kind`/`black_kind` must be machine kinds (`MACHINE_PLAYER_KINDS`);
    `iterations`/`temperature` tune neural players only. Passing `seed` makes the
    whole batch reproducible: it seeds phase-1 placement, the process-global
    `random` module that `RandomCtfPlayer.select_ply`'s `RandomEngine` draws
    from, and (for a neural seat) `torch` for the network's initial weights — the
    three independent randomness sources a batch pulls from.
    """
    if num_games < 1:
        raise ValueError("num_games must be at least 1")
    for kind in (white_kind, black_kind):
        if kind not in MACHINE_PLAYER_KINDS:
            raise ValueError(
                f"batch play requires a machine kind {MACHINE_PLAYER_KINDS}, got {kind!r}"
            )

    if seed is not None:
        random.seed(seed)
        rng = random.Random(seed)
        if "neural" in (white_kind, black_kind):
            import torch

            torch.manual_seed(seed)
    else:
        rng = random.Random()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tournament rejects duplicate player names, so disambiguate matching kinds
    # with an A/B suffix (a neural-vs-random batch reads as "Neural"/"Random").
    if white_kind == black_kind:
        white_name, black_name = f"{white_kind.title()} A", f"{black_kind.title()} B"
    else:
        white_name, black_name = white_kind.title(), black_kind.title()

    context = PlayerContext(rng=rng)
    white_player = make_player(
        white_kind, white_name, context=context,
        iterations=iterations, temperature=temperature,
    )
    black_player = make_player(
        black_kind, black_name, context=context,
        iterations=iterations, temperature=temperature,
    )
    tournament = Tournament(
        players=[white_player, black_player],
        position_factory=build_initial_position,
        game_logging=CtfGameLogging(),
        games_per_pairing=num_games,
    )
    result = tournament.run()

    white_wins = 0
    black_wins = 0
    draws = 0
    ply_counts: list[int] = []
    reason_counts: Counter[str] = Counter()

    width = len(str(num_games))
    for game_number, record in enumerate(result.records, start=1):
        game_result = record.result
        # Absolute outcome: 1 => side 1 (the first mover, White) won, -1 => Black.
        if game_result.outcome == 1:
            white_wins += 1
        elif game_result.outcome == -1:
            black_wins += 1
        else:
            draws += 1
        ply_counts.append(len(game_result.game_log))
        reason_counts[game_result.result_reason] += 1

        text = write_record(
            game_result,
            white_name=record.players[1],
            black_name=record.players[-1],
            round_number=str(game_number),
        )
        record_path = output_dir / f"game_{game_number:0{width}d}.ctfgame"
        record_path.write_text(text, encoding="utf-8")

    return BatchSummary(
        games_played=num_games,
        white_wins=white_wins,
        black_wins=black_wins,
        draws=draws,
        min_plies=min(ply_counts),
        max_plies=max(ply_counts),
        mean_plies=sum(ply_counts) / len(ply_counts),
        reason_counts=dict(reason_counts),
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play a batch of machine-vs-machine Capture the Flag games.",
    )
    parser.add_argument(
        "-n",
        "--games",
        type=int,
        default=100,
        help="number of games to play (default: 100)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("games"),
        help="directory to write game-record files to (default: ./games)",
    )
    parser.add_argument(
        "--white",
        choices=MACHINE_PLAYER_KINDS,
        default="random",
        help="kind of the first-moving player (default: random)",
    )
    parser.add_argument(
        "--black",
        choices=MACHINE_PLAYER_KINDS,
        default="random",
        help="kind of the second-moving player (default: random)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed the batch's random number generator for reproducibility",
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
    summary = run_batch(
        args.games,
        args.output_dir,
        seed=args.seed,
        white_kind=args.white,
        black_kind=args.black,
        iterations=args.iterations,
        temperature=args.temperature,
    )
    print(summary.format())


if __name__ == "__main__":
    main()

"""Headless batch runner: play many random-vs-random matches, write one
game-record file per match, and report a batch summary.

Runnable as a module: `python -m capture_the_flag.batch_runner [options]`.
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
from .player import RandomCtfPlayer
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
    rng: random.Random | None = None,
) -> BatchSummary:
    """Play `num_games` random-vs-random matches, writing one game-record
    file per match into `output_dir` (created if needed), and return the
    batch summary.

    The batch is a two-player round robin over the shared `Tournament`: two
    `RandomCtfPlayer`s meet `num_games` times, and `Tournament` alternates which
    of them moves first (holds White) from game to game, so `white_wins` /
    `black_wins` below count first-mover / second-mover wins rather than a fixed
    player. Phase-1 placement is supplied through the widened position factory
    (`build_initial_position`); scheduling, side alternation, and the game loop
    all come from `Tournament`.

    `rng` seeds phase-1 placement only. `RandomCtfPlayer.select_ply` is
    backed by `game-engine-core`'s `RandomEngine`, which draws from the
    process-global `random` module rather than an injectable generator;
    callers wanting a fully reproducible batch (placement *and* play) should
    also call `random.seed(...)` before invoking this function.
    """
    if num_games < 1:
        raise ValueError("num_games must be at least 1")

    rng = rng if rng is not None else random.Random()
    output_dir.mkdir(parents=True, exist_ok=True)

    tournament = Tournament(
        players=[RandomCtfPlayer("Random A", rng), RandomCtfPlayer("Random B", rng)],
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
        description="Play a batch of random-vs-random Capture the Flag games.",
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
        "--seed",
        type=int,
        default=None,
        help="seed the batch's random number generator for reproducibility",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    rng = None
    if args.seed is not None:
        # Seed the process-global `random` module too, since select_ply's
        # `RandomEngine` draws from it rather than an injectable generator.
        random.seed(args.seed)
        rng = random.Random(args.seed)
    summary = run_batch(args.games, args.output_dir, rng=rng)
    print(summary.format())


if __name__ == "__main__":
    main()

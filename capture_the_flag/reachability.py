"""Structural reachability and the Unbreachable Flag cache (rules.md
Sections 5 and 6.2).

Structural reachability treats lakes and any intact Tower or Flag (either
side) as impassable walls, and ignores all mobile pieces. A piece's own
*legal* movement is blocked by those same lakes and Towers, so the connected
region a piece occupies can never change as a result of ordinary movement --
only destroying a Tower (removing a wall) or capturing the piece itself can
change it. This is why the breachability cache only needs recomputing on a
Tower- or Sapper-removing ply (see `transitions.py`), not on every ply.
"""

from collections import deque
from collections.abc import Mapping

from .board import (
    BLACK_HOME_SQUARES,
    LAKE_SQUARES,
    WHITE_HOME_SQUARES,
    Square,
    orthogonal_neighbors,
)
from .breachability import BreachabilityCache
from .pieces import PieceType
from .side import Side

Board = Mapping[Square, tuple[Side, PieceType]]


def _blocked_squares(board: Board) -> frozenset[Square]:
    blocked = set(LAKE_SQUARES)
    for square, (_side, piece) in board.items():
        if piece is PieceType.TOWER or piece is PieceType.FLAG:
            blocked.add(square)
    return frozenset(blocked)


def _connected_component(blocked: frozenset[Square], start: Square) -> set[Square]:
    """Every square reachable from `start` without crossing `blocked`."""
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in orthogonal_neighbors(current):
            if neighbor in visited or neighbor in blocked:
                continue
            visited.add(neighbor)
            queue.append(neighbor)
    return visited


def _reachable(blocked: frozenset[Square], start: Square, target: Square) -> bool:
    """Whether `target` is reachable from `start`, treating `target` itself
    as always a valid landing square even if it is in `blocked` (a Tower is
    a wall to move *through*, not to arrive *at*)."""
    if start == target:
        return True
    visited = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in orthogonal_neighbors(current):
            if neighbor == target:
                return True
            if neighbor in visited or neighbor in blocked:
                continue
            visited.add(neighbor)
            queue.append(neighbor)
    return False


def _flag_enclosed(board: Board, side: Side, blocked: frozenset[Square]) -> bool:
    flag_square = next(
        square
        for square, (piece_side, piece) in board.items()
        if piece_side is side and piece is PieceType.FLAG
    )
    opponent_home = BLACK_HOME_SQUARES if side is Side.WHITE else WHITE_HOME_SQUARES
    component = _connected_component(blocked, flag_square)
    return component.isdisjoint(opponent_home)


def _sappers_available(board: Board, side: Side, blocked: frozenset[Square]) -> bool:
    enemy = side.opponent
    enemy_towers = [
        square
        for square, (piece_side, piece) in board.items()
        if piece_side is enemy and piece is PieceType.TOWER
    ]
    sappers = [
        square
        for square, (piece_side, piece) in board.items()
        if piece_side is side and piece is PieceType.SAPPER
    ]
    return any(
        _reachable(blocked, sapper_square, tower_square)
        for sapper_square in sappers
        for tower_square in enemy_towers
    )


def compute_breachability(board: Board) -> BreachabilityCache:
    """Compute the four Unbreachable Flag inputs (rules.md Section 6.2)
    fresh from `board`."""
    blocked = _blocked_squares(board)
    return BreachabilityCache(
        white_flag_enclosed=_flag_enclosed(board, Side.WHITE, blocked),
        black_flag_enclosed=_flag_enclosed(board, Side.BLACK, blocked),
        white_sappers_available=_sappers_available(board, Side.WHITE, blocked),
        black_sappers_available=_sappers_available(board, Side.BLACK, blocked),
    )

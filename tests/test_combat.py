"""Tests for combat resolution (rules.md Section 4.3)."""

import itertools
from types import MappingProxyType

import pytest

from capture_the_flag.board import Square
from capture_the_flag.combat import CombatResult, resolve_combat
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

ATTACKER = Square(3, 2)  # D2
DEFENDER = Square(3, 3)  # D3, adjacent north of the attacker

NUMBERED_PIECES = [piece for piece in P if piece.rank is not None]


def _position(board: dict) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
    )


def _resolve(
    attacker_piece: P,
    defender_piece: P,
    *,
    attacker: Square = ATTACKER,
    defender: Square = DEFENDER,
    extra: dict | None = None,
) -> CombatResult:
    board = {
        attacker: (Side.WHITE, attacker_piece),
        defender: (Side.BLACK, defender_piece),
    }
    if extra:
        board.update(extra)
    return resolve_combat(_position(board), attacker, defender)


@pytest.mark.parametrize(
    ("attacker_piece", "defender_piece"),
    list(itertools.product(NUMBERED_PIECES, NUMBERED_PIECES)),
)
def test_rank_order_table(attacker_piece, defender_piece):
    # No friendly neighbours on the board, so no formation bonus is in play.
    assert attacker_piece.rank is not None
    assert defender_piece.rank is not None
    result = _resolve(attacker_piece, defender_piece)
    if attacker_piece.rank < defender_piece.rank:
        assert result is CombatResult.ATTACKER_WINS
    elif attacker_piece.rank > defender_piece.rank:
        assert result is CombatResult.ATTACKER_LOSES
    else:
        assert result is CombatResult.MUTUAL_LOSS


@pytest.mark.parametrize("attacker_piece", NUMBERED_PIECES)
def test_any_attack_on_a_tower_is_a_mutual_loss(attacker_piece):
    assert _resolve(attacker_piece, P.TOWER) is CombatResult.MUTUAL_LOSS


@pytest.mark.parametrize("attacker_piece", NUMBERED_PIECES)
def test_flag_is_always_captured(attacker_piece):
    assert _resolve(attacker_piece, P.FLAG) is CombatResult.ATTACKER_WINS


def test_flag_capture_ignores_formation_bonus():
    # A friendly piece beside the Flag never saves it: capture is immediate.
    board = {
        ATTACKER: (Side.WHITE, P.MILITIA),
        DEFENDER: (Side.BLACK, P.FLAG),
        Square(4, 3): (Side.BLACK, P.MILITIA),  # beside the Flag (E3)
    }
    assert resolve_combat(_position(board), ATTACKER, DEFENDER) is (
        CombatResult.ATTACKER_WINS
    )


def test_defender_formation_bonus_draws_against_one_rank_higher():
    # Champion (2) beats Knight (3) cleanly, but a friendly Knight beside the
    # defending Knight turns the loss into a draw (both removed).
    friend = {Square(4, 3): (Side.BLACK, P.KNIGHT)}  # E3, adjacent to D3
    assert _resolve(P.CHAMPION, P.KNIGHT) is CombatResult.ATTACKER_WINS
    assert _resolve(P.CHAMPION, P.KNIGHT, extra=friend) is CombatResult.MUTUAL_LOSS


def test_attacker_formation_bonus_draws_against_one_rank_higher():
    # A Knight (3) attacking a Champion (2) normally loses; a friendly Knight
    # beside the attacker (checked at its pre-move square) makes it a draw.
    friend = {Square(4, 2): (Side.WHITE, P.KNIGHT)}  # E2, adjacent to D2
    assert _resolve(P.KNIGHT, P.CHAMPION) is CombatResult.ATTACKER_LOSES
    assert _resolve(P.KNIGHT, P.CHAMPION, extra=friend) is CombatResult.MUTUAL_LOSS


def test_formation_bonus_counts_diagonal_neighbours():
    friend = {Square(4, 4): (Side.BLACK, P.KNIGHT)}  # E4, diagonal to D3
    assert _resolve(P.CHAMPION, P.KNIGHT, extra=friend) is CombatResult.MUTUAL_LOSS


def test_no_formation_bonus_when_rank_gap_exceeds_one():
    # Master-of-Arms (1) vs Knight (3): a two-rank gap, so a friendly Knight
    # beside the defender provides no rescue.
    friend = {Square(4, 3): (Side.BLACK, P.KNIGHT)}
    assert _resolve(P.MASTER_OF_ARMS, P.KNIGHT, extra=friend) is (
        CombatResult.ATTACKER_WINS
    )


def test_no_formation_bonus_from_a_different_rank_neighbour():
    # A friendly neighbour of a *different* rank does not form a formation.
    friend = {Square(4, 3): (Side.BLACK, P.MILITIA)}  # rank 6, not 3
    assert _resolve(P.CHAMPION, P.KNIGHT, extra=friend) is CombatResult.ATTACKER_WINS


def test_no_formation_bonus_from_an_enemy_neighbour():
    # An equal-rank neighbour on the *attacker's* side does not help the
    # defending Knight.
    enemy = {Square(4, 3): (Side.WHITE, P.KNIGHT)}
    assert _resolve(P.CHAMPION, P.KNIGHT, extra=enemy) is CombatResult.ATTACKER_WINS

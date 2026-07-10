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
TRIGGER = Square(3, 4)  # D4, one square beyond the defender on the same line

NUMBERED_PIECES = [piece for piece in P if piece.rank is not None]


def _position(board: dict) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        white_inactivity_counter=0,
        black_inactivity_counter=0,
        progress_counter=0,
    )


def _resolve(
    attacker_piece: P,
    defender_piece: P,
    *,
    attacker: Square = ATTACKER,
    defender: Square = DEFENDER,
    extra: dict | None = None,
) -> CombatResult:
    board = {attacker: (Side.WHITE, attacker_piece), defender: (Side.BLACK, defender_piece)}
    if extra:
        board.update(extra)
    return resolve_combat(_position(board), attacker, defender)


@pytest.mark.parametrize(
    ("attacker_piece", "defender_piece"),
    list(itertools.product(NUMBERED_PIECES, NUMBERED_PIECES)),
)
def test_rank_order_table(attacker_piece, defender_piece):
    assert attacker_piece.rank is not None
    assert defender_piece.rank is not None
    result = _resolve(attacker_piece, defender_piece)
    if attacker_piece.rank < defender_piece.rank:
        assert result is CombatResult.ATTACKER_WINS
    elif attacker_piece.rank > defender_piece.rank:
        assert result is CombatResult.ATTACKER_LOSES
    else:
        assert result is CombatResult.MUTUAL_LOSS


def test_knight_charge_beats_knight():
    # Distance 3 (D2 -> D5): a genuine charge.
    result = _resolve(P.KNIGHT, P.KNIGHT, defender=Square(3, 5))
    assert result is CombatResult.ATTACKER_WINS


def test_adjacent_knight_vs_knight_is_still_mutual_loss():
    result = _resolve(P.KNIGHT, P.KNIGHT)  # distance 1, not a charge
    assert result is CombatResult.MUTUAL_LOSS


def test_assassin_wins_against_any_rank():
    for defender_piece in NUMBERED_PIECES:
        assert _resolve(P.ASSASSIN, defender_piece) is CombatResult.ATTACKER_WINS


def test_assassin_always_loses_when_attacked():
    # The attacker wins regardless of its own rank -- even the weakest piece.
    for attacker_piece in NUMBERED_PIECES:
        assert _resolve(attacker_piece, P.ASSASSIN) is CombatResult.ATTACKER_WINS


def test_assassin_vs_assassin_attacker_wins():
    assert _resolve(P.ASSASSIN, P.ASSASSIN) is CombatResult.ATTACKER_WINS


def test_assassin_attacking_tower_is_a_complete_sacrifice():
    assert _resolve(P.ASSASSIN, P.TOWER) is CombatResult.ATTACKER_LOSES


def test_sapper_destroys_tower():
    assert _resolve(P.SAPPER, P.TOWER) is CombatResult.ATTACKER_WINS


@pytest.mark.parametrize("attacker_piece", [p for p in NUMBERED_PIECES if p is not P.SAPPER])
def test_non_sapper_attacking_tower_is_a_complete_sacrifice(attacker_piece):
    assert _resolve(attacker_piece, P.TOWER) is CombatResult.ATTACKER_LOSES


@pytest.mark.parametrize("attacker_piece", [*NUMBERED_PIECES, P.ASSASSIN])
def test_flag_is_always_captured(attacker_piece):
    assert _resolve(attacker_piece, P.FLAG) is CombatResult.ATTACKER_WINS


def test_archer_support_converts_clean_loss_to_mutual_loss():
    # Infantry (attacker) beats Militia (defender) cleanly by rank...
    board = {
        ATTACKER: (Side.WHITE, P.INFANTRY),
        DEFENDER: (Side.BLACK, P.MILITIA),
        TRIGGER: (Side.BLACK, P.ARCHER),  # friendly to the defender
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.MUTUAL_LOSS


def test_no_support_when_trigger_square_is_empty():
    board = {ATTACKER: (Side.WHITE, P.INFANTRY), DEFENDER: (Side.BLACK, P.MILITIA)}
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.ATTACKER_WINS


def test_no_support_when_trigger_piece_is_not_an_archer():
    board = {
        ATTACKER: (Side.WHITE, P.INFANTRY),
        DEFENDER: (Side.BLACK, P.MILITIA),
        TRIGGER: (Side.BLACK, P.HALBERDIER),  # friendly, but not an Archer
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.ATTACKER_WINS


def test_no_support_when_trigger_archer_is_the_wrong_side():
    board = {
        ATTACKER: (Side.WHITE, P.INFANTRY),
        DEFENDER: (Side.BLACK, P.MILITIA),
        TRIGGER: (Side.WHITE, P.ARCHER),  # an Archer, but friendly to the attacker
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.ATTACKER_WINS


def test_no_support_when_trigger_square_is_off_board():
    # Row 12 is the board edge; one square beyond it does not exist.
    attacker = Square(3, 11)  # D11
    defender = Square(3, 12)  # D12
    board = {attacker: (Side.WHITE, P.INFANTRY), defender: (Side.BLACK, P.MILITIA)}
    position = _position(board)
    assert resolve_combat(position, attacker, defender) is CombatResult.ATTACKER_WINS


def test_no_support_when_trigger_square_is_a_lake():
    # Column F (index 5) is a lake column; F4 -> F5 -> F6 puts the trigger
    # square on a lake, which can never hold a piece.
    attacker = Square(5, 4)  # F4
    defender = Square(5, 5)  # F5
    board = {attacker: (Side.WHITE, P.INFANTRY), defender: (Side.BLACK, P.MILITIA)}
    position = _position(board)
    assert resolve_combat(position, attacker, defender) is CombatResult.ATTACKER_WINS


def test_archer_covered_tower_becomes_a_trade_with_the_sapper():
    board = {
        ATTACKER: (Side.WHITE, P.SAPPER),
        DEFENDER: (Side.BLACK, P.TOWER),
        TRIGGER: (Side.BLACK, P.ARCHER),
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.MUTUAL_LOSS


@pytest.mark.parametrize("attacker_piece", [*NUMBERED_PIECES, P.ASSASSIN])
def test_archer_never_supports_the_flag(attacker_piece):
    # An Archer directly behind the Flag provides no support: capturing the
    # Flag is always an immediate win for the attacker (rules.md 6.1), even for
    # a Sapper or the Assassin.
    board = {
        ATTACKER: (Side.WHITE, attacker_piece),
        DEFENDER: (Side.BLACK, P.FLAG),
        TRIGGER: (Side.BLACK, P.ARCHER),
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.ATTACKER_WINS


def test_archer_support_converts_assassin_attack_to_mutual_loss():
    # The Assassin wins against the target by its special rule, but is not
    # immune to Archer support: the result is a trade (rules.md 4.3).
    board = {
        ATTACKER: (Side.WHITE, P.ASSASSIN),
        DEFENDER: (Side.BLACK, P.MILITIA),
        TRIGGER: (Side.BLACK, P.ARCHER),
    }
    position = _position(board)
    assert resolve_combat(position, ATTACKER, DEFENDER) is CombatResult.MUTUAL_LOSS

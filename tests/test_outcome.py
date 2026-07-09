"""Tests for outcome and endings (rules.md Section 6)."""

from types import MappingProxyType

from capture_the_flag.board import Square
from capture_the_flag.breachability import BreachabilityCache
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.placement import assemble_position, random_placement
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side

# A cache that never triggers the Unbreachable Flag win on its own, so tests
# for the other endings can be isolated from it.
_INERT_BREACHABILITY = BreachabilityCache(
    white_flag_enclosed=False,
    black_flag_enclosed=False,
    white_sappers_available=False,
    black_sappers_available=False,
)

# Neutral squares to park each side's Flag in tests that aren't about flag
# capture -- the outcome check for Section 6.1 requires both to be present.
_WHITE_FLAG_SQUARE = Square(11, 1)  # L1
_BLACK_FLAG_SQUARE = Square(11, 12)  # L12


def _position(
    board: dict,
    side_to_move: Side = Side.WHITE,
    white_inactivity_counter: int = 0,
    black_inactivity_counter: int = 0,
    progress_counter: int = 0,
    breachability: BreachabilityCache | None = _INERT_BREACHABILITY,
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        white_inactivity_counter=white_inactivity_counter,
        black_inactivity_counter=black_inactivity_counter,
        progress_counter=progress_counter,
        breachability=breachability,
    )


def test_fresh_position_is_ongoing():
    white = random_placement(Side.WHITE)
    black = random_placement(Side.BLACK)
    position = assemble_position(white, black)
    assert position.outcome is None


def test_active_players_own_flag_missing_is_a_loss():
    board = {
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.FLAG),
    }
    position = _position(board, side_to_move=Side.WHITE)
    assert position.outcome == -1


def test_opponents_flag_missing_is_a_win():
    board = {
        Square(3, 2): (Side.WHITE, P.FLAG),
        Square(5, 5): (Side.WHITE, P.INFANTRY),
    }
    position = _position(board, side_to_move=Side.WHITE)
    assert position.outcome == 1


def test_no_legal_move_is_a_loss():
    # Only immobile pieces for the side to move.
    board = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(0, 2): (Side.WHITE, P.TOWER),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, side_to_move=Side.WHITE)
    assert position.legal_plies == ()
    assert position.outcome == -1


def test_inactivity_loss_for_active_player():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, side_to_move=Side.WHITE, white_inactivity_counter=50)
    assert position.outcome == -1


def test_inactivity_loss_for_opponent_is_a_win():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, side_to_move=Side.WHITE, black_inactivity_counter=50)
    assert position.outcome == 1


def test_below_inactivity_limit_is_still_ongoing():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, side_to_move=Side.WHITE, white_inactivity_counter=49)
    assert position.outcome is None


def test_no_progress_draw():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, progress_counter=80)
    assert position.outcome == 0


def test_below_progress_limit_is_still_ongoing():
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(board, progress_counter=79)
    assert position.outcome is None


def test_unbreachable_flag_white_wins():
    cache = BreachabilityCache(
        white_flag_enclosed=True,
        black_flag_enclosed=False,
        white_sappers_available=True,
        black_sappers_available=False,  # Black can't breach White's wall.
    )
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    white_active = _position(board, side_to_move=Side.WHITE, breachability=cache)
    black_active = _position(board, side_to_move=Side.BLACK, breachability=cache)
    assert white_active.outcome == 1
    assert black_active.outcome == -1


def test_unbreachable_flag_black_wins():
    cache = BreachabilityCache(
        white_flag_enclosed=False,
        black_flag_enclosed=True,
        white_sappers_available=False,  # White can't breach Black's wall.
        black_sappers_available=True,
    )
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    white_active = _position(board, side_to_move=Side.WHITE, breachability=cache)
    black_active = _position(board, side_to_move=Side.BLACK, breachability=cache)
    assert white_active.outcome == -1
    assert black_active.outcome == 1


def test_unbreachable_flag_both_at_once_is_a_draw():
    cache = BreachabilityCache(
        white_flag_enclosed=True,
        black_flag_enclosed=True,
        white_sappers_available=False,
        black_sappers_available=False,
    )
    board = {
        _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(3, 2): (Side.WHITE, P.INFANTRY),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    white_active = _position(board, side_to_move=Side.WHITE, breachability=cache)
    black_active = _position(board, side_to_move=Side.BLACK, breachability=cache)
    assert white_active.outcome == 0
    assert black_active.outcome == 0


def test_unbreachable_flag_takes_priority_over_no_legal_move_and_clocks():
    # A win/draw condition (Section 6.2) is checked ahead of the "softer"
    # endings, even when those would also independently apply.
    cache = BreachabilityCache(
        white_flag_enclosed=True,
        black_flag_enclosed=False,
        white_sappers_available=False,
        black_sappers_available=False,
    )
    board = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(0, 2): (Side.WHITE, P.TOWER),
        _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
        Square(5, 5): (Side.BLACK, P.INFANTRY),
    }
    position = _position(
        board,
        side_to_move=Side.WHITE,
        white_inactivity_counter=50,
        progress_counter=80,
        breachability=cache,
    )
    assert position.legal_plies == ()  # no-legal-move and inactivity would
    # otherwise both say "White (active) loses" -- Unbreachable says White wins.
    assert position.outcome == 1


def test_mutual_last_sapper_trade_both_enclosed_is_a_draw():
    # Both sides' last Sapper trades in one mutual-loss combat; both flags
    # are enclosed by their own intact Towers, so both conditions fire at
    # once (rules.md Section 6.2 mutual last-Sapper trade edge case).
    position = _mutual_sapper_trade_setup(black_flag_enclosed=True)
    after_trade = position.apply_ply(CtfPly(Square(3, 5), Square(3, 6)))
    assert after_trade.breachability is not None
    assert after_trade.breachability.white_flag_enclosed is True
    assert after_trade.breachability.black_flag_enclosed is True
    assert after_trade.outcome == 0


def test_mutual_last_sapper_trade_only_one_enclosed_is_a_win():
    position = _mutual_sapper_trade_setup(black_flag_enclosed=False)
    after_trade = position.apply_ply(CtfPly(Square(3, 5), Square(3, 6)))
    assert after_trade.breachability is not None
    assert after_trade.breachability.white_flag_enclosed is True
    assert after_trade.breachability.black_flag_enclosed is False
    # White made the trade, so Black is now the active player; White won.
    assert after_trade.side_to_move is Side.BLACK
    assert after_trade.outcome == -1


def _mutual_sapper_trade_setup(*, black_flag_enclosed: bool) -> CtfPosition:
    white_flag = Square(0, 1)  # A1, sealed by the two Towers below.
    white_tower_a2 = Square(0, 2)
    white_tower_b1 = Square(1, 1)
    black_flag = Square(11, 12)  # L12, sealed the same way iff requested.
    board = {
        white_flag: (Side.WHITE, P.FLAG),
        white_tower_a2: (Side.WHITE, P.TOWER),
        white_tower_b1: (Side.WHITE, P.TOWER),
        black_flag: (Side.BLACK, P.FLAG),
        Square(3, 5): (Side.WHITE, P.SAPPER),
        Square(3, 6): (Side.BLACK, P.SAPPER),
    }
    if black_flag_enclosed:
        board[Square(11, 11)] = (Side.BLACK, P.TOWER)
        board[Square(10, 12)] = (Side.BLACK, P.TOWER)
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=Side.WHITE,
        white_inactivity_counter=0,
        black_inactivity_counter=0,
        progress_counter=0,
        breachability=_INERT_BREACHABILITY,
    )

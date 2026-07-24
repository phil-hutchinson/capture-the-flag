from types import MappingProxyType

import pytest
import torch
import torch.nn as nn
from game_engine_core.engines.mcts_engine import MCTSEngine
from torch import Tensor

from capture_the_flag.board import BOARD_COLUMNS, BOARD_ROWS, Square
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import (
    CtfNNEvaluator,
    policy_logit_location_for_ply,
    rotate_ply,
    rotate_square,
)
from capture_the_flag.engines.neural_network.tensor_layout import (
    ACTION_SPACE_SHAPE,
    FP_INACTIVITY_COUNT,
    FP_OUR_FLAG,
    FP_OUR_FLAG_RELATIVE_COLUMN,
    FP_OUR_FLAG_RELATIVE_ROW,
    FP_OUR_RANK_1,
    FP_OUR_RANK_1_QUANTITY,
    # FP_OUR_RANK_2,
    FP_OUR_RANK_2_QUANTITY,
    # FP_OUR_RANK_3,
    FP_OUR_RANK_3_QUANTITY,
    # FP_OUR_RANK_4,
    FP_OUR_RANK_4_QUANTITY,
    # FP_OUR_RANK_5,
    FP_OUR_RANK_5_QUANTITY,
    # FP_OUR_RANK_6,
    FP_OUR_RANK_6_QUANTITY,
    FP_OUR_TOWER,
    FP_PASSABLE,
    FP_THEIR_FLAG,
    FP_THEIR_FLAG_RELATIVE_COLUMN,
    FP_THEIR_FLAG_RELATIVE_ROW,
    # FP_THEIR_RANK_1,
    FP_THEIR_RANK_1_QUANTITY,
    FP_THEIR_RANK_2,
    FP_THEIR_RANK_2_QUANTITY,
    # FP_THEIR_RANK_3,
    FP_THEIR_RANK_3_QUANTITY,
    # FP_THEIR_RANK_4,
    FP_THEIR_RANK_4_QUANTITY,
    # FP_THEIR_RANK_5,
    FP_THEIR_RANK_5_QUANTITY,
    # FP_THEIR_RANK_6,
    FP_THEIR_RANK_6_QUANTITY,
    # FP_THEIR_TOWER,
    # INPUT_SHAPE,
    MOVEMENT_INDEX,
)
from capture_the_flag.outcome import INACTIVITY_LIMIT
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side
from tests.engines.neural_network.small_networks import small_network


def _dummy_model():
    # Simple dummy model for testing—CtfNNEvaluator only uses encode_position, not the model itself
    return nn.Linear(1, 1)

def _position(board: dict, side_to_move: Side = Side.WHITE, inactivity_counter: int = 0) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=inactivity_counter,
    )

def _matching_white_position(inactivity_counter: int = 0) -> CtfPosition:
    board = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(3, 4): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(4, 3): (Side.WHITE, P.TOWER),
        Square(4, 11): (Side.BLACK, P.CHAMPION),
        Square(4, 12): (Side.BLACK, P.FLAG),
    }

    return _position(board,side_to_move=Side.WHITE,inactivity_counter=inactivity_counter)

def _matching_black_position(inactivity_counter: int = 0) -> CtfPosition:
    board = {
        Square(11, 12): (Side.BLACK, P.FLAG),
        Square(8, 9): (Side.BLACK, P.MASTER_OF_ARMS),
        Square(7, 10): (Side.BLACK, P.TOWER),
        Square(7, 2): (Side.WHITE, P.CHAMPION),
        Square(7, 1): (Side.WHITE, P.FLAG),
    }

    return _position(board,side_to_move=Side.BLACK,inactivity_counter=inactivity_counter)

def _base_position(side_to_move: Side, inactivity_counter: int = 0) -> CtfPosition:
    board = {
        Square(4, 1): (Side.WHITE, P.FLAG),
        Square(11, 3): (Side.WHITE, P.TOWER),
        Square(4, 2): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(3, 1): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(4, 12): (Side.BLACK, P.FLAG),
        Square(0, 9): (Side.BLACK, P.TOWER),
        Square(2, 9): (Side.BLACK, P.TOWER),
        Square(4, 9): (Side.BLACK, P.TOWER),
        Square(6, 9): (Side.BLACK, P.TOWER),
        Square(8, 9): (Side.BLACK, P.TOWER),
        Square(10, 9): (Side.BLACK, P.TOWER),
        Square(1, 9): (Side.BLACK, P.CHAMPION),
        Square(3, 9): (Side.BLACK, P.CHAMPION),
        Square(5, 9): (Side.BLACK, P.CHAMPION),
        Square(7, 9): (Side.BLACK, P.CHAMPION),
        Square(9, 9): (Side.BLACK, P.CHAMPION),
        Square(11, 9): (Side.BLACK, P.CHAMPION),
    }

    return _position(board,side_to_move=side_to_move,inactivity_counter=inactivity_counter)


_MOBILE_RANKS: tuple[P, ...] = (
    P.MASTER_OF_ARMS,
    P.CHAMPION,
    P.KNIGHT,
    P.HALBERDIER,
    P.FOOT_SOLDIER,
    P.MILITIA,
)

_OUR_RANK_QUANTITY_FP: tuple[int, ...] = (
    FP_OUR_RANK_1_QUANTITY,
    FP_OUR_RANK_2_QUANTITY,
    FP_OUR_RANK_3_QUANTITY,
    FP_OUR_RANK_4_QUANTITY,
    FP_OUR_RANK_5_QUANTITY,
    FP_OUR_RANK_6_QUANTITY,
)

_THEIR_RANK_QUANTITY_FP: tuple[int, ...] = (
    FP_THEIR_RANK_1_QUANTITY,
    FP_THEIR_RANK_2_QUANTITY,
    FP_THEIR_RANK_3_QUANTITY,
    FP_THEIR_RANK_4_QUANTITY,
    FP_THEIR_RANK_5_QUANTITY,
    FP_THEIR_RANK_6_QUANTITY,
)

# Deliberately asymmetric and distinct per side, so a bug that swaps "our" and
# "their" (e.g. under rotation) produces a detectably wrong ratio rather than
# an accidental match.
_ATTRITION_COUNTS: dict[Side, dict[P, int]] = {
    Side.WHITE: {
        P.MASTER_OF_ARMS: 3,
        P.CHAMPION: 2,
        P.KNIGHT: 1,
        P.HALBERDIER: 0,
        P.FOOT_SOLDIER: 3,
        P.MILITIA: 3,
    },
    Side.BLACK: {
        P.MASTER_OF_ARMS: 0,
        P.CHAMPION: 1,
        P.KNIGHT: 2,
        P.HALBERDIER: 3,
        P.FOOT_SOLDIER: 0,
        P.MILITIA: 1,
    },
}

def _ranked_pieces(side: Side, counts: dict[P, int], start_row: int) -> dict[Square, tuple[Side, P]]:
    # Up to 18 pieces (6 ranks x roster of 3) can't fit in one 12-column row,
    # so spread across two consecutive rows. Callers must pick a `start_row` whose
    # pair avoids the lake rows (6-7), so the fixture stays a position the rules
    # could actually produce.
    squares = (
        Square(column, row)
        for row in (start_row, start_row + 1)
        for column in range(BOARD_COLUMNS)
    )
    board: dict[Square, tuple[Side, P]] = {}
    for rank in _MOBILE_RANKS:
        for _ in range(counts[rank]):
            board[next(squares)] = (side, rank)
    return board

def _full_army_position(side_to_move: Side = Side.WHITE) -> CtfPosition:
    full_counts = {rank: 3 for rank in _MOBILE_RANKS}
    board: dict[Square, tuple[Side, P]] = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(11, 12): (Side.BLACK, P.FLAG),
    }
    board.update(_ranked_pieces(Side.WHITE, full_counts, start_row=4))
    board.update(_ranked_pieces(Side.BLACK, full_counts, start_row=8))
    return _position(board, side_to_move=side_to_move)

def _attrition_position(side_to_move: Side = Side.WHITE) -> CtfPosition:
    board: dict[Square, tuple[Side, P]] = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(11, 12): (Side.BLACK, P.FLAG),
    }
    board.update(_ranked_pieces(Side.WHITE, _ATTRITION_COUNTS[Side.WHITE], start_row=4))
    board.update(_ranked_pieces(Side.BLACK, _ATTRITION_COUNTS[Side.BLACK], start_row=8))
    return _position(board, side_to_move=side_to_move)

def _check_uniform_plane_value(encoded: Tensor, feature_plane: int, expected_value: float) -> None:
    for row in range(BOARD_ROWS):
        for column in range(BOARD_COLUMNS):
            assert encoded[feature_plane, row, column] == pytest.approx(expected_value)

def _check_tensor_piece_fill(encoded: Tensor, expected_piece_placements: set[tuple[int, int, int]]) -> None:
    # Expected tuples are (plane, column, row) — board-natural order, 0-based —
    # transposed to the tensor's (plane, row, column) at the point of indexing.
    for fp in range(16):
        for column in range(12):
            for row in range(12):
                expected_value = 1 if (fp, column, row) in expected_piece_placements else 0
                assert encoded[fp, row, column] == expected_value

def _check_flag_relative_planes(
    encoded: Tensor,
    our_flag_position: tuple[int, int],
    their_flag_position: tuple[int, int],
) -> None:
    # Positions are (tensor row, tensor column) of each flag, in the frame
    # `encoded` was built in. Checked at every square, since the offset is
    # defined board-wide, not just at sampled points.
    our_flag_row, our_flag_column = our_flag_position
    their_flag_row, their_flag_column = their_flag_position
    for row in range(BOARD_ROWS):
        for column in range(BOARD_COLUMNS):
            assert encoded[FP_OUR_FLAG_RELATIVE_ROW, row, column] == pytest.approx(
                (our_flag_row - row) / BOARD_ROWS
            )
            assert encoded[FP_OUR_FLAG_RELATIVE_COLUMN, row, column] == pytest.approx(
                (our_flag_column - column) / BOARD_COLUMNS
            )
            assert encoded[FP_THEIR_FLAG_RELATIVE_ROW, row, column] == pytest.approx(
                (their_flag_row - row) / BOARD_ROWS
            )
            assert encoded[FP_THEIR_FLAG_RELATIVE_COLUMN, row, column] == pytest.approx(
                (their_flag_column - column) / BOARD_COLUMNS
            )

def _check_tensor_lake_fill(encoded: Tensor) -> None:
    expected_lake_placements = {
        (1, 5),
        (1, 6),
        (2, 5),
        (2, 6),
        (5, 5),
        (5, 6),
        (6, 5),
        (6, 6),
        (9, 5),
        (9, 6),
        (10, 5),
        (10, 6),
    }
    for column in range(12):
        for row in range(12):
            expected_value = 0 if (column, row) in expected_lake_placements else 1
            assert encoded[FP_PASSABLE, row, column] == expected_value

_A2A4_L11L9:tuple[int,int,int] = MOVEMENT_INDEX[(2, 0)], 1, 0
_D4D5_I9I8:tuple[int,int,int] = MOVEMENT_INDEX[(1, 0)], 3, 3
_H9G9_E4F4:tuple[int,int,int] = MOVEMENT_INDEX[(0, -1)], 8, 7

def _setup_policy_logits(seed = 987) -> Tensor:
    torch.manual_seed(seed)

    policy_logits = torch.empty(ACTION_SPACE_SHAPE)
    policy_logits.uniform_(-10, 10)
    policy_logits[_A2A4_L11L9] = 3.0
    policy_logits[_D4D5_I9I8] = 10.0
    policy_logits[_H9G9_E4F4] = 25.0
    return policy_logits

def _setup_position_legal_plies(side: Side, monkeypatch) -> CtfPosition:
    board = {}
    position = CtfPosition(board, side, 0)
    square_1_from = Square(0, 2) if side == Side.WHITE else Square(11, 11)
    square_1_to = Square(0, 4) if side == Side.WHITE else Square(11, 9)
    square_2_from = Square(3, 4) if side == Side.WHITE else Square(8, 9)
    square_2_to = Square(3, 5) if side == Side.WHITE else Square(8, 8)
    square_3_from = Square(7, 9) if side == Side.WHITE else Square(4, 4)
    square_3_to = Square(6, 9) if side == Side.WHITE else Square(5, 4)

    legal_plies = (
        CtfPly(square_1_from, square_1_to),
        CtfPly(square_2_from, square_2_to),
        CtfPly(square_3_from, square_3_to),
    )
    monkeypatch.setattr(CtfPosition, "legal_plies", property(lambda self: legal_plies))

    return position


@pytest.mark.parametrize(
    "position", 
    [_matching_white_position(), _matching_black_position()],
    ids=["white_board", "black_board"]
)
def test_encode_processes_matching_boards_correctly(position):
    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)
    expected_piece_placements = {
        (FP_OUR_FLAG, 0, 0),
        (FP_OUR_RANK_1, 3, 3),
        (FP_OUR_TOWER, 4, 2),
        (FP_THEIR_RANK_2, 4, 10),
        (FP_THEIR_FLAG, 4, 11),
    }
    _check_tensor_piece_fill(encoded, expected_piece_placements)
    _check_tensor_lake_fill(encoded)

@pytest.mark.parametrize(
    "inactivity_counter", 
    [0, 10, 49]
)
def test_matching_positions_equivalent(inactivity_counter):
    white_position = _matching_white_position(inactivity_counter)
    black_position = _matching_black_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model())
    white_encoded = evaluator.encode_position(white_position)
    black_encoded = evaluator.encode_position(black_position)

    assert torch.equal(white_encoded, black_encoded)

@pytest.mark.parametrize(
    "inactivity_counter", 
    [0, 10, 49]
)
def test_inactivity_counter_consistent(inactivity_counter):
    position = _matching_white_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)

    ref_value = encoded[FP_INACTIVITY_COUNT, 0, 0]
    # TODO use constants here
    for row in range(12):
        for column in range(12):
            # we should be able to test for exact equality even with floats (should be exactly the same float)
            assert encoded[FP_INACTIVITY_COUNT, row, column] == ref_value

@pytest.mark.parametrize(
    "inactivity_counter", 
    [0, 10, 49]
)
def test_inactivity_counter_populated(inactivity_counter):
    position = _matching_white_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)

    expected_value = inactivity_counter / INACTIVITY_LIMIT
    # TODO use constants here
    for row in range(12):
        for column in range(12):
            assert encoded[FP_INACTIVITY_COUNT, row, column] == pytest.approx(expected_value)

@pytest.mark.parametrize(
    "position, our_flag_position, their_flag_position",
    [
        (_matching_white_position(), (0, 0), (11, 4)),
        (_matching_black_position(), (0, 0), (11, 4)),
    ],
    ids=["white_board", "black_board"],
)
def test_flag_relative_planes_normalized_correctly(position, our_flag_position, their_flag_position):
    # Both fixtures are the same position, one from each side's perspective, so
    # both flags land at the same tensor coordinates once re-based into the
    # mover's frame -- (0, 0) for the mover's own flag, (11, 4) for the enemy's.
    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)
    _check_flag_relative_planes(encoded, our_flag_position, their_flag_position)

@pytest.mark.parametrize(
    "inactivity_counter",
    [0, 10, 49]
)
def test_flag_relative_planes_equivalent_under_rotation(inactivity_counter):
    white_position = _matching_white_position(inactivity_counter)
    black_position = _matching_black_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model())
    white_encoded = evaluator.encode_position(white_position)
    black_encoded = evaluator.encode_position(black_position)

    for fp in (
        FP_OUR_FLAG_RELATIVE_ROW,
        FP_OUR_FLAG_RELATIVE_COLUMN,
        FP_THEIR_FLAG_RELATIVE_ROW,
        FP_THEIR_FLAG_RELATIVE_COLUMN,
    ):
        assert torch.equal(white_encoded[fp], black_encoded[fp])

def test_army_strength_planes_full_army_is_one():
    position = _full_army_position(Side.WHITE)

    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)

    for fp in _OUR_RANK_QUANTITY_FP + _THEIR_RANK_QUANTITY_FP:
        _check_uniform_plane_value(encoded, fp, 1.0)

@pytest.mark.parametrize(
    "side_to_move",
    [Side.WHITE, Side.BLACK],
    ids=["White", "Black"],
)
def test_army_strength_planes_reflect_attrition(side_to_move):
    position = _attrition_position(side_to_move)
    our_counts = _ATTRITION_COUNTS[side_to_move]
    their_counts = _ATTRITION_COUNTS[side_to_move.opponent]

    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)

    for rank, our_fp, their_fp in zip(_MOBILE_RANKS, _OUR_RANK_QUANTITY_FP, _THEIR_RANK_QUANTITY_FP, strict=True):
        _check_uniform_plane_value(encoded, our_fp, our_counts[rank] / 3)
        _check_uniform_plane_value(encoded, their_fp, their_counts[rank] / 3)

@pytest.mark.parametrize(
    "inactivity_counter",
    [0, 10, 49]
)
def test_army_strength_planes_equivalent_under_rotation(inactivity_counter):
    white_position = _matching_white_position(inactivity_counter)
    black_position = _matching_black_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model())
    white_encoded = evaluator.encode_position(white_position)
    black_encoded = evaluator.encode_position(black_position)

    for fp in _OUR_RANK_QUANTITY_FP + _THEIR_RANK_QUANTITY_FP:
        assert torch.equal(white_encoded[fp], black_encoded[fp])

@pytest.mark.parametrize(
    "missing_side, expected",
    [(Side.WHITE, "own"), (Side.BLACK, "enemy")],
    ids=["own_flag", "enemy_flag"],
)
def test_encode_rejects_a_position_with_a_flag_missing(missing_side, expected):
    # A flag leaves the board only by being captured, which ends the game, so this
    # is a terminal position. Nothing in the engine's wiring encodes one (MCTS and
    # the self-play collector both short-circuit on `outcome`), but `encode_position`
    # is public, and the offset planes have no defined value here — so it names the
    # problem rather than raising a bare StopIteration from the flag lookup.
    board = {
        square: piece
        for square, piece in _matching_white_position().board.items()
        if piece != (missing_side, P.FLAG)
    }
    position = _position(board, side_to_move=Side.WHITE, inactivity_counter=0)

    evaluator = CtfNNEvaluator(_dummy_model())

    with pytest.raises(ValueError, match=expected):
        evaluator.encode_position(position)

def test_rotate_square_involution():
    for column in range(BOARD_COLUMNS):
        for row in range(1, BOARD_ROWS + 1):
            original_square = Square(column, row)
            rotated_once = rotate_square(original_square)
            rotated_twice = rotate_square(rotated_once)
            assert original_square.column == rotated_twice.column
            assert original_square.row == rotated_twice.row

@pytest.mark.parametrize(
    "rotation",
    [
        (0, 1, 11, 12), # A1 => L12
        (11, 1, 0, 12), # L1 => A12
        (3, 6, 8, 7) # D6 => I7
    ]
)
def test_rotate_square_rotates_180_degrees(rotation):
    column_original, row_original, column_expected, row_expected = rotation

    original_square = Square(column_original, row_original)
    rotated_square = rotate_square(original_square)

    assert rotated_square.column == column_expected
    assert rotated_square.row == row_expected

def test_rotate_ply_rotates_180_degrees():
    original = CtfPly(Square(2, 3), Square(2, 4))
    rotated = rotate_ply(original)

    assert str(rotated) == "J10J9"

@pytest.mark.parametrize(
    "active_player_id",
    [1, -1],
    ids=["White", "Black"],
)
def test_policy_logit_location_for_ply_is_bijective(active_player_id):
    # note: this does include illegal moves (from/to lakes, to off the board locations) that exist in the policy_logit
    filled: set[tuple[int,int,int]] = set()
    for column in range(BOARD_COLUMNS):
        for row in range(1, BOARD_ROWS + 1):
            for row_delta, column_delta in MOVEMENT_INDEX.keys():
                from_square = Square(column, row)
                to_square = Square(column + column_delta, row + row_delta)
                ply = CtfPly(from_square, to_square)
                location = policy_logit_location_for_ply(ply, active_player_id)
                assert 0 <= location[0] < ACTION_SPACE_SHAPE[0]
                assert 0 <= location[1] < ACTION_SPACE_SHAPE[1]
                assert 0 <= location[2] < ACTION_SPACE_SHAPE[2]
                assert location not in filled
                filled.add(location)

@pytest.mark.parametrize(
    "side_values", 
    [(Side.WHITE, "A2A4", "D4D5", "H9G9"), (Side.BLACK, "L11L9", "I9I8", "E4F4")],
    ids=["White", "Black"],
)
def test_decode_policy_returns_valid_policy_dict(side_values, monkeypatch):
    side, pos1, pos2, pos3, = side_values

    evaluator = CtfNNEvaluator(_dummy_model())

    policy_logits = _setup_policy_logits()
    position = _setup_position_legal_plies(side, monkeypatch)
    
    policy_dict = evaluator.decode_policy(policy_logits, position)

    assert len(policy_dict) == 3

    assert pos1 in policy_dict
    assert pos2 in policy_dict
    assert pos3 in policy_dict

    assert policy_dict[pos3] > policy_dict[pos2] > policy_dict[pos1]

    assert sum(policy_dict.values()) == pytest.approx(1.0)

@pytest.mark.parametrize(
    "side_values", 
    [(Side.WHITE, "A2A4", "D4D5", "H9G9"), (Side.BLACK, "L11L9", "I9I8", "E4F4")],
    ids=["White", "Black"],
)
def test_decode_policy_ignores_masked_indices(side_values, monkeypatch):
    side, pos1, pos2, pos3, = side_values

    evaluator = CtfNNEvaluator(_dummy_model())

    policy_logits_a = _setup_policy_logits(1234)
    policy_logits_b = _setup_policy_logits(2345)
    position = _setup_position_legal_plies(side, monkeypatch)
    
    policy_dict_a = evaluator.decode_policy(policy_logits_a, position)
    policy_dict_b = evaluator.decode_policy(policy_logits_b, position)

    assert len(policy_dict_a) == len(policy_dict_b)

    for ply, value in policy_dict_a.items():
        assert ply in policy_dict_b
        assert value == pytest.approx(policy_dict_b[ply])

@pytest.mark.parametrize(
    "side_to_move", 
    [Side.WHITE, Side.BLACK,],
)
def test_evaluator_with_actual_nn_returns_valid_evaluation(side_to_move):
    
    nn = small_network()
    evaluator = CtfNNEvaluator(nn)

    position = _base_position(side_to_move, 0)
    evaluation = evaluator.evaluate_position(position)

    assert -1 <= evaluation.value <= 1
    assert evaluation.policy is not None
    assert set(evaluation.policy.keys()) == {str(ply) for ply in position.legal_plies}
    assert all(value >= 0 for value in evaluation.policy.values())
    assert sum(evaluation.policy.values()) == pytest.approx(1.0)

@pytest.mark.parametrize(
    "side_to_move", 
    [Side.WHITE, Side.BLACK,],
)
def test_evaluator_in_engine_with_actual_nn_returns_valid_ply(side_to_move):
    
    nn = small_network()
    engine: MCTSEngine[CtfPly, CtfPosition, CtfNNEvaluator] = MCTSEngine(
        evaluator = CtfNNEvaluator(nn),
        iterations = 100,
        temperature = 0.0
    )

    position = _base_position(side_to_move, 0)
    selected_ply = engine.select_ply(position)

    assert selected_ply.source in position.board.keys()
    selected_side, _ = position.board[selected_ply.source]
    assert selected_side == side_to_move

    # no pieces are in range to attack each other, so assert that it lands on a blank square
    assert selected_ply.destination not in position.board.keys() 
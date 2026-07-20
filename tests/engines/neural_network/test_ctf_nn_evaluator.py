from types import MappingProxyType

import pytest
import torch
import torch.nn as nn
from game_engine_core.engines.mcts_engine import MCTSEngine
from torch import Tensor

from capture_the_flag.board import BOARD_COLUMNS, BOARD_ROWS, Square
from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.tensor_layout import (
    ACTION_SPACE_SHAPE,
    FP_INACTIVITY_COUNT,
    FP_OUR_FLAG,
    FP_OUR_RANK_1,
    # FP_OUR_RANK_2,
    # FP_OUR_RANK_3,
    # FP_OUR_RANK_4,
    # FP_OUR_RANK_5,
    # FP_OUR_RANK_6,
    FP_OUR_TOWER,
    FP_PASSABLE,
    FP_THEIR_FLAG,
    # FP_THEIR_RANK_1,
    FP_THEIR_RANK_2,
    # FP_THEIR_RANK_3,
    # FP_THEIR_RANK_4,
    # FP_THEIR_RANK_5,
    # FP_THEIR_RANK_6,
    # FP_THEIR_TOWER,
    # INPUT_SHAPE,
    MOVEMENT_INDEX,
)
from capture_the_flag.outcome import INACTIVITY_LIMIT
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side


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


def _check_tensor_piece_fill(encoded: Tensor, expected_piece_placements: set[tuple[int, int, int]]) -> None:
    # Expected tuples are (plane, column, row) — board-natural order, 0-based —
    # transposed to the tensor's (plane, row, column) at the point of indexing.
    for fp in range(16):
        for column in range(12):
            for row in range(12):
                expected_value = 1 if (fp, column, row) in expected_piece_placements else 0
                assert encoded[fp, row, column] == expected_value

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

def test_rotate_square_involution():
    evaluator = CtfNNEvaluator(_dummy_model())
    for column in range(BOARD_COLUMNS):
        for row in range(1, BOARD_ROWS + 1):
            original_square = Square(column, row)
            rotated_once = evaluator._rotate_square(original_square)
            rotated_twice = evaluator._rotate_square(rotated_once)
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
    evaluator = CtfNNEvaluator(_dummy_model())

    original_square = Square(column_original, row_original)
    rotated_square = evaluator._rotate_square(original_square)

    assert rotated_square.column == column_expected
    assert rotated_square.row == row_expected

@pytest.mark.parametrize(
    "active_player_id", 
    [1, -1],
    ids=["White", "Black"],
)
def test_get_policy_logit_location_for_ply_is_bijective(active_player_id):
    # note: this does include illegal moves (from/to lakes, to off the board locations) that exist in the policy_logit
    filled: set[tuple[int,int,int]] = set()
    evaluator = CtfNNEvaluator(_dummy_model())
    for column in range(BOARD_COLUMNS):
        for row in range(1, BOARD_ROWS + 1):
            for row_delta, column_delta in MOVEMENT_INDEX.keys():
                from_square = Square(column, row)
                to_square = Square(column + column_delta, row + row_delta)
                ply = CtfPly(from_square, to_square)
                location = evaluator._get_policy_logit_location_for_ply(ply, active_player_id)
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
    
    nn = CtfCrn()
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
    
    nn = CtfCrn()
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
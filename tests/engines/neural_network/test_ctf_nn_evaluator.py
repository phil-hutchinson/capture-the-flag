from types import MappingProxyType

import pytest
import torch
import torch.nn as nn
from torch import Tensor

from capture_the_flag.board import Square
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.outcome import INACTIVITY_LIMIT
from capture_the_flag.pieces import PieceType as P
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
            expected_value = 1 if (column, row) in expected_lake_placements else 0
            assert encoded[CtfNNEvaluator._FP_LAKE, row, column] == expected_value


@pytest.mark.parametrize(
    "position", 
    [_matching_white_position(), _matching_black_position()],
    ids=["white_board", "black_board"]
)
def test_encode_processes_matching_boards_correctly(position):
    evaluator = CtfNNEvaluator(_dummy_model())
    encoded = evaluator.encode_position(position)
    expected_piece_placements = {
        (CtfNNEvaluator._FP_OUR_FLAG, 0, 0),
        (CtfNNEvaluator._FP_OUR_RANK_1, 3, 3),
        (CtfNNEvaluator._FP_OUR_TOWER, 4, 2),
        (CtfNNEvaluator._FP_THEIR_RANK_2, 4, 10),
        (CtfNNEvaluator._FP_THEIR_FLAG, 4, 11),
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

    ref_value = encoded[CtfNNEvaluator._FP_INACTIVITY_COUNT, 0, 0]
    # TODO use constants here
    for row in range(12):
        for column in range(12):
            # we should be able to test for exact equality even with floats (should be exactly the same float)
            assert encoded[CtfNNEvaluator._FP_INACTIVITY_COUNT, row, column] == ref_value

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
            assert encoded[CtfNNEvaluator._FP_INACTIVITY_COUNT, row, column] == pytest.approx(expected_value)
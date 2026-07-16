"""The learned play engine's evaluator: position encoding and policy decoding.

`encode_position` presents a `CtfPosition` to the network as a 17-plane one-hot
12x12 image, always from the side-to-move's perspective: when Black is to move,
the board is rotated 180 degrees and ownership relabelled, so the network always
sees "own side moving up the board" and never knows which colour it is playing.

Two coordinate conventions meet here and nowhere else: `Square` is
column-first and 1-indexed on rows (matching the rules' "A3" notation), while
tensors are row-major and 0-indexed — `(channel, row, column)`, the
height-before-width order torch's convolutions expect. `_get_tensor_position`
is the single point of conversion between the two frames.
"""

from collections.abc import Sequence
from typing import Literal

import torch
from game_engine_learning.neural_network_evaluator import NeuralNetworkEvaluator
from torch import Tensor

from ...board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from ...outcome import INACTIVITY_LIMIT
from ...pieces import PieceType
from ...ply import CtfPly
from ...position import CtfPosition


class CtfNNEvaluator(NeuralNetworkEvaluator[CtfPly, CtfPosition]):
    # Feature Planes:
    _FP_OUR_FLAG = 0
    _FP_OUR_TOWER = 1
    _FP_OUR_RANK_1 = 2
    _FP_OUR_RANK_2 = 3
    _FP_OUR_RANK_3 = 4
    _FP_OUR_RANK_4 = 5
    _FP_OUR_RANK_5 = 6
    _FP_OUR_RANK_6 = 7
    _FP_THEIR_FLAG = 8
    _FP_THEIR_TOWER = 9 
    _FP_THEIR_RANK_1 = 10
    _FP_THEIR_RANK_2 = 11
    _FP_THEIR_RANK_3 = 12
    _FP_THEIR_RANK_4 = 13
    _FP_THEIR_RANK_5 = 14
    _FP_THEIR_RANK_6 = 15
    _FP_LAKE = 16
    _FP_INACTIVITY_COUNT = 17

    _OUR_FP = {
        PieceType.FLAG: _FP_OUR_FLAG,
        PieceType.TOWER: _FP_OUR_TOWER,
        PieceType.MASTER_OF_ARMS: _FP_OUR_RANK_1,
        PieceType.CHAMPION: _FP_OUR_RANK_2,
        PieceType.KNIGHT: _FP_OUR_RANK_3,
        PieceType.HALBERDIER: _FP_OUR_RANK_4,
        PieceType.FOOT_SOLDIER: _FP_OUR_RANK_5,
        PieceType.MILITIA: _FP_OUR_RANK_6,
    }

    _THEIR_FP = {
        PieceType.FLAG: _FP_THEIR_FLAG,
        PieceType.TOWER: _FP_THEIR_TOWER,
        PieceType.MASTER_OF_ARMS: _FP_THEIR_RANK_1,
        PieceType.CHAMPION: _FP_THEIR_RANK_2,
        PieceType.KNIGHT: _FP_THEIR_RANK_3,
        PieceType.HALBERDIER: _FP_THEIR_RANK_4,
        PieceType.FOOT_SOLDIER: _FP_THEIR_RANK_5,
        PieceType.MILITIA: _FP_THEIR_RANK_6,
    }


    def encode_position(self, position: CtfPosition) -> Tensor:
        # tensor expected to be (batch, channels, height, width)
        # batch will be handled later - we just need to do the last three here

        def _get_tensor_position(square: Square, active_player_id: Literal[1, -1]) -> tuple[int, int]:
            """`square` as 0-based tensor indices, in `(row, column)` order.

            Identity re-basing when White is to move; the 180-degree rotation
            when Black is to move, so the mover's back rank is always row 0.
            """
            if active_player_id == 1:
                return square.row - 1, square.column
            else:
                return 12 - square.row, 11 - square.column
        
        encoded = torch.zeros((18, BOARD_ROWS, BOARD_COLUMNS), dtype=torch.float32)

        # current pieces on board
        for square, (side, piece_type) in position.board.items():
            tensor_row, tensor_column  = _get_tensor_position(square, position.active_player_id)
            ours = (side.value * position.active_player_id) == 1
            fp = CtfNNEvaluator._OUR_FP[piece_type] if ours else CtfNNEvaluator._THEIR_FP[piece_type]
            encoded[fp, tensor_row, tensor_column] = 1
        # lake squares
        for lake_square in LAKE_SQUARES:
            tensor_row, tensor_column = _get_tensor_position(lake_square, position.active_player_id)
            encoded[CtfNNEvaluator._FP_LAKE, tensor_row, tensor_column] = 1
        # Draw-by-inactivity counter
        move_limit_ratio = position.inactivity_counter / INACTIVITY_LIMIT
        encoded[CtfNNEvaluator._FP_INACTIVITY_COUNT, :, :].fill_(move_limit_ratio)

        return encoded
    
    def decode_policy(self, policy_logits: Tensor, legal_plies: Sequence[CtfPly]) -> dict[str, float]:
        # not implemented yet
        return {}




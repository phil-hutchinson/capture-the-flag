"""The learned play engine's evaluator: position encoding and policy decoding.

`encode_position` presents a `CtfPosition` to the network as a 18-plane one-hot
12x12 image, always from the side-to-move's perspective: when Black is to move,
the board is rotated 180 degrees and ownership relabelled, so the network always
sees "own side moving up the board" and never knows which colour it is playing.

Two coordinate conventions meet here and nowhere else: `Square` is
column-first and 1-indexed on rows (matching the rules' "A3" notation), while
tensors are row-major and 0-indexed — `(channel, row, column)`, the
height-before-width order torch's convolutions expect. `_get_tensor_position`
is the single point of conversion between the two frames.
"""

from typing import Literal

import torch
import torch.nn.functional as F
from game_engine_learning.neural_network_evaluator import NeuralNetworkEvaluator
from torch import Tensor

from ...board import LAKE_SQUARES, Square
from ...outcome import INACTIVITY_LIMIT
from ...pieces import PieceType
from ...ply import CtfPly
from ...position import CtfPosition
from .tensor_layout import (
    ACTION_SPACE_SHAPE,
    FP_INACTIVITY_COUNT,
    FP_OUR_FLAG,
    FP_OUR_RANK_1,
    FP_OUR_RANK_2,
    FP_OUR_RANK_3,
    FP_OUR_RANK_4,
    FP_OUR_RANK_5,
    FP_OUR_RANK_6,
    FP_OUR_TOWER,
    FP_PASSABLE,
    FP_THEIR_FLAG,
    FP_THEIR_RANK_1,
    FP_THEIR_RANK_2,
    FP_THEIR_RANK_3,
    FP_THEIR_RANK_4,
    FP_THEIR_RANK_5,
    FP_THEIR_RANK_6,
    FP_THEIR_TOWER,
    INPUT_SHAPE,
    MOVEMENT_INDEX,
)


class CtfNNEvaluator(NeuralNetworkEvaluator[CtfPosition]):

    _OUR_FP = {
        PieceType.FLAG: FP_OUR_FLAG,
        PieceType.TOWER: FP_OUR_TOWER,
        PieceType.MASTER_OF_ARMS: FP_OUR_RANK_1,
        PieceType.CHAMPION: FP_OUR_RANK_2,
        PieceType.KNIGHT: FP_OUR_RANK_3,
        PieceType.HALBERDIER: FP_OUR_RANK_4,
        PieceType.FOOT_SOLDIER: FP_OUR_RANK_5,
        PieceType.MILITIA: FP_OUR_RANK_6,
    }

    _THEIR_FP = {
        PieceType.FLAG: FP_THEIR_FLAG,
        PieceType.TOWER: FP_THEIR_TOWER,
        PieceType.MASTER_OF_ARMS: FP_THEIR_RANK_1,
        PieceType.CHAMPION: FP_THEIR_RANK_2,
        PieceType.KNIGHT: FP_THEIR_RANK_3,
        PieceType.HALBERDIER: FP_THEIR_RANK_4,
        PieceType.FOOT_SOLDIER: FP_THEIR_RANK_5,
        PieceType.MILITIA: FP_THEIR_RANK_6,
    }

    def encode_position(self, position: CtfPosition) -> Tensor:
        # tensor expected to be (batch, channels, height, width)
        # batch will be handled later - we just need to do the last three here

        encoded = torch.zeros(INPUT_SHAPE, dtype=torch.float32)

        # Current pieces on board
        for square, (side, piece_type) in position.board.items():
            tensor_row, tensor_column  = self._get_tensor_position(square, position.active_player_id)
            ours = (side.value * position.active_player_id) == 1
            fp = CtfNNEvaluator._OUR_FP[piece_type] if ours else CtfNNEvaluator._THEIR_FP[piece_type]
            encoded[fp, tensor_row, tensor_column] = 1
        # Passable squares / Lake squares
        encoded[FP_PASSABLE, :, :].fill_(1)
        for lake_square in LAKE_SQUARES:
            tensor_row, tensor_column = self._get_tensor_position(lake_square, position.active_player_id)
            encoded[FP_PASSABLE, tensor_row, tensor_column] = 0
        # Draw-by-inactivity counter
        move_limit_ratio = position.inactivity_counter / INACTIVITY_LIMIT
        encoded[FP_INACTIVITY_COUNT, :, :].fill_(move_limit_ratio)

        return encoded
    
    def decode_policy(self, policy_logits: Tensor, position: CtfPosition) -> dict[str, float]:
        # identify location in policy_logits tensor for all legal plies
        legal_ply_mapping: dict[tuple[int, int, int], CtfPly] = {}
        for ply in position.legal_plies:
            logit_location = self._get_policy_logit_location_for_ply(ply, position.active_player_id)
            legal_ply_mapping[logit_location] = ply

        # create filter, starting with all positions masked, and unmasking legal plies
        mask = torch.full(ACTION_SPACE_SHAPE, float('-inf'))
        for policy_logit_location in legal_ply_mapping:
            mask[policy_logit_location] = 0.0
        
        # create a probability for all legal plies, summing to one
        # masked locations in policy_logits will receive a probability of 0
        masked = policy_logits + mask
        probabilities = F.softmax(masked.flatten(), dim = -1).reshape(ACTION_SPACE_SHAPE)
        
        # map the probabilities back to valid plies
        return {str(ply): probabilities[policy_logit_location].item() for (policy_logit_location, ply) in legal_ply_mapping.items()}        

    def _rotate_square(self, square: Square) -> Square:
        rotated_row = 13 - square.row
        rotated_column = 11 - square.column
        return Square(rotated_column, rotated_row)

    def _get_tensor_position(self, square: Square, active_player_id: Literal[1, -1]) -> tuple[int, int]:
        """`square` as 0-based tensor indices, in `(row, column)` order.

        Identity re-basing when White is to move; the 180-degree rotation
        when Black is to move, so the mover's back rank is always row 0.
        """
        if active_player_id == -1:
            square = self._rotate_square(square)

        return square.row - 1, square.column

    def _get_policy_logit_location_for_ply(self, ply: CtfPly, active_player_id: Literal[1, -1]) -> tuple[int, int, int]:
        # returns (movemement index, row, column)
        tensor_from_row, tensor_from_column = self._get_tensor_position(ply.source, active_player_id)
        tensor_to_row, tensor_to_column = self._get_tensor_position(ply.destination, active_player_id)
        row_delta = tensor_to_row - tensor_from_row
        column_delta = tensor_to_column - tensor_from_column
        movement_index = MOVEMENT_INDEX[(row_delta, column_delta)]
        return movement_index, tensor_from_row, tensor_from_column


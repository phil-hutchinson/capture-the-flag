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

from ...board import BOARD_COLUMNS, BOARD_ROWS, LAKE_SQUARES, Square
from ...outcome import INACTIVITY_LIMIT
from ...pieces import PieceType
from ...ply import CtfPly
from ...position import CtfPosition
from .tensor_layout import (
    ACTION_SPACE_SHAPE,
    FP_INACTIVITY_COUNT,
    FP_OUR_FLAG,
    FP_OUR_FLAG_RELATIVE_COLUMN,
    FP_OUR_FLAG_RELATIVE_ROW,
    FP_OUR_RANK_1,
    FP_OUR_RANK_1_QUANTITY,
    FP_OUR_RANK_2,
    FP_OUR_RANK_2_QUANTITY,
    FP_OUR_RANK_3,
    FP_OUR_RANK_3_QUANTITY,
    FP_OUR_RANK_4,
    FP_OUR_RANK_4_QUANTITY,
    FP_OUR_RANK_5,
    FP_OUR_RANK_5_QUANTITY,
    FP_OUR_RANK_6,
    FP_OUR_RANK_6_QUANTITY,
    FP_OUR_TOWER,
    FP_PASSABLE,
    FP_THEIR_FLAG,
    FP_THEIR_FLAG_RELATIVE_COLUMN,
    FP_THEIR_FLAG_RELATIVE_ROW,
    FP_THEIR_RANK_1,
    FP_THEIR_RANK_1_QUANTITY,
    FP_THEIR_RANK_2,
    FP_THEIR_RANK_2_QUANTITY,
    FP_THEIR_RANK_3,
    FP_THEIR_RANK_3_QUANTITY,
    FP_THEIR_RANK_4,
    FP_THEIR_RANK_4_QUANTITY,
    FP_THEIR_RANK_5,
    FP_THEIR_RANK_5_QUANTITY,
    FP_THEIR_RANK_6,
    FP_THEIR_RANK_6_QUANTITY,
    FP_THEIR_TOWER,
    INPUT_SHAPE,
    MOVEMENT_INDEX,
)


def rotate_square(square: Square) -> Square:
    """The 180-degree board rotation: the shared side-to-move orientation
    transform. It is its own inverse, so encoder (orienting the input) and
    decoder (mapping preferences back to global-frame plies) stay consistent by
    applying the same function."""
    return Square(11 - square.column, 13 - square.row)

def rotate_ply(ply: CtfPly) -> CtfPly:
    return CtfPly(
        rotate_square(ply.source),
        rotate_square(ply.destination),
    )

def tensor_position(square: Square, active_player_id: Literal[1, -1]) -> tuple[int, int]:
    """`square` as 0-based tensor indices, in `(row, column)` order.

    Identity re-basing when White is to move; the 180-degree rotation when Black
    is to move, so the mover's back rank is always row 0.
    """
    if active_player_id == -1:
        square = rotate_square(square)
    return square.row - 1, square.column


def policy_logit_location_for_ply(
    ply: CtfPly, active_player_id: Literal[1, -1]
) -> tuple[int, int, int]:
    """The `(movement index, row, column)` slot in the action space a ply maps
    to, in the side-to-move frame."""
    tensor_from_row, tensor_from_column = tensor_position(ply.source, active_player_id)
    tensor_to_row, tensor_to_column = tensor_position(ply.destination, active_player_id)
    row_delta = tensor_to_row - tensor_from_row
    column_delta = tensor_to_column - tensor_from_column
    movement_index = MOVEMENT_INDEX[(row_delta, column_delta)]
    return movement_index, tensor_from_row, tensor_from_column


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

    _FP_PIECE_QUANTITY = {
        #key: our piece, rank
        (True, PieceType.MASTER_OF_ARMS): FP_OUR_RANK_1_QUANTITY,
        (True, PieceType.CHAMPION): FP_OUR_RANK_2_QUANTITY,
        (True, PieceType.KNIGHT): FP_OUR_RANK_3_QUANTITY,
        (True, PieceType.HALBERDIER): FP_OUR_RANK_4_QUANTITY,
        (True, PieceType.FOOT_SOLDIER): FP_OUR_RANK_5_QUANTITY,
        (True, PieceType.MILITIA): FP_OUR_RANK_6_QUANTITY,
        (False, PieceType.MASTER_OF_ARMS): FP_THEIR_RANK_1_QUANTITY,
        (False, PieceType.CHAMPION): FP_THEIR_RANK_2_QUANTITY,
        (False, PieceType.KNIGHT): FP_THEIR_RANK_3_QUANTITY,
        (False, PieceType.HALBERDIER): FP_THEIR_RANK_4_QUANTITY,
        (False, PieceType.FOOT_SOLDIER): FP_THEIR_RANK_5_QUANTITY,
        (False, PieceType.MILITIA): FP_THEIR_RANK_6_QUANTITY,
    }

    _FP_PIECE_TOTAL_QUANTITY = {
        FP_OUR_RANK_1_QUANTITY: PieceType.MASTER_OF_ARMS.army_count,
        FP_OUR_RANK_2_QUANTITY: PieceType.CHAMPION.army_count,
        FP_OUR_RANK_3_QUANTITY: PieceType.KNIGHT.army_count,
        FP_OUR_RANK_4_QUANTITY: PieceType.HALBERDIER.army_count,
        FP_OUR_RANK_5_QUANTITY: PieceType.FOOT_SOLDIER.army_count,
        FP_OUR_RANK_6_QUANTITY: PieceType.MILITIA.army_count,
        FP_THEIR_RANK_1_QUANTITY: PieceType.MASTER_OF_ARMS.army_count,
        FP_THEIR_RANK_2_QUANTITY: PieceType.CHAMPION.army_count,
        FP_THEIR_RANK_3_QUANTITY: PieceType.KNIGHT.army_count,
        FP_THEIR_RANK_4_QUANTITY: PieceType.HALBERDIER.army_count,
        FP_THEIR_RANK_5_QUANTITY: PieceType.FOOT_SOLDIER.army_count,
        FP_THEIR_RANK_6_QUANTITY: PieceType.MILITIA.army_count,
    }

    def encode_position(self, position: CtfPosition) -> Tensor:
        # tensor expected to be (batch, channels, height, width)
        # batch will be handled later - we just need to do the last three here
        encoded = torch.zeros(INPUT_SHAPE, dtype=torch.float32)

        # Current pieces on board
        for square, (side, piece_type) in position.board.items():
            tensor_row, tensor_column = tensor_position(square, position.active_player_id)
            ours = (side.value * position.active_player_id) == 1
            fp = CtfNNEvaluator._OUR_FP[piece_type] if ours else CtfNNEvaluator._THEIR_FP[piece_type]
            encoded[fp, tensor_row, tensor_column] = 1
        # Passable squares / Lake squares
        encoded[FP_PASSABLE, :, :].fill_(1)
        for lake_square in LAKE_SQUARES:
            tensor_row, tensor_column = tensor_position(lake_square, position.active_player_id)
            encoded[FP_PASSABLE, tensor_row, tensor_column] = 0
        # Draw-by-inactivity counter
        move_limit_ratio = position.inactivity_counter / INACTIVITY_LIMIT
        encoded[FP_INACTIVITY_COUNT, :, :].fill_(move_limit_ratio)
        # Flags relative position
        our_flag_square = next(k for k, (side, piece_type) in position.board.items()
              if side == position.side_to_move and piece_type == PieceType.FLAG)
        our_flag_row, our_flag_column = tensor_position(our_flag_square, position.active_player_id)
        for row in range(BOARD_ROWS):
            encoded[FP_OUR_FLAG_RELATIVE_ROW, row, :].fill_((our_flag_row - row)/BOARD_ROWS)
        for column in range(BOARD_COLUMNS):
            encoded[FP_OUR_FLAG_RELATIVE_COLUMN, :, column].fill_((our_flag_column - column)/BOARD_COLUMNS)
        their_flag_square = next(k for k, (side, piece_type) in position.board.items()
              if side != position.side_to_move and piece_type == PieceType.FLAG)
        their_flag_row, their_flag_column = tensor_position(their_flag_square, position.active_player_id)
        for row in range(BOARD_ROWS):
            encoded[FP_THEIR_FLAG_RELATIVE_ROW, row, :].fill_((their_flag_row - row)/BOARD_ROWS)
        for column in range(BOARD_COLUMNS):
            encoded[FP_THEIR_FLAG_RELATIVE_COLUMN, :, column].fill_((their_flag_column - column)/BOARD_COLUMNS)
        # Army strength
        piece_strength: dict[int, int] = {}
        for fp_entry in CtfNNEvaluator._FP_PIECE_QUANTITY.values():
            piece_strength[fp_entry] = 0
        for _, (piece_side, piece_type) in position.board.items():
            ours = (piece_side == position.side_to_move)
            if (ours, piece_type) in CtfNNEvaluator._FP_PIECE_QUANTITY:
                fp_to_increment = CtfNNEvaluator._FP_PIECE_QUANTITY[(ours, piece_type)]
                piece_strength[fp_to_increment] += 1
        for feature_plane, quantity in piece_strength.items():
            encoded[feature_plane, :, :].fill_(quantity / CtfNNEvaluator._FP_PIECE_TOTAL_QUANTITY[feature_plane])

        return encoded
    
    def decode_policy(self, policy_logits: Tensor, position: CtfPosition) -> dict[str, float]:
        # identify location in policy_logits tensor for all legal plies
        legal_ply_mapping: dict[tuple[int, int, int], CtfPly] = {}
        for ply in position.legal_plies:
            logit_location = policy_logit_location_for_ply(ply, position.active_player_id)
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


"""The learned play engine's evaluator: position encoding and policy decoding.

`encode_position` presents a `CtfPosition` to the network as a `TOTAL_FP_COUNT`-
plane image the size of the configured board, always from the side-to-move's
perspective: when Black is to move, the board is rotated 180 degrees and
ownership relabelled, so the network always sees "own side moving up the board"
and never knows which colour it is playing. Most planes are one-hot piece/lake
indicators, but the engineered planes (flag-relative offsets, army-strength
ratios) are continuous-valued broadcasts — see `tensor_layout.py` for the full
plane layout.

An evaluator is built for one `TensorLayout` and encodes only that board and
army: the extent of every plane and the divisor of every army-strength plane come
from it. The board-shaped helpers below therefore take the layout they are
rotating or indexing within rather than reading a module constant, which is what
lets a Skirmish position and a Battle position be encoded in the same process.

Two coordinate conventions meet here and nowhere else: `Square` is
column-first and 1-indexed on rows (matching the rules' "A3" notation), while
tensors are row-major and 0-indexed — `(channel, row, column)`, the
height-before-width order torch's convolutions expect. `tensor_position`
is the single point of conversion between the two frames.
"""

from typing import Literal

import torch
import torch.nn as nn
import torch.nn.functional as F
from game_engine_core.models.position_evaluation import PositionEvaluation
from game_engine_learning.neural_network_evaluator import NeuralNetworkEvaluator
from torch import Tensor

from ...board import BoardLayout, Square
from ...instrumentation.timing import region, timed
from ...outcome import INACTIVITY_LIMIT
from ...pieces import PieceType
from ...ply import CtfPly
from ...position import CtfPosition
from ...timing_regions import (
    BUILD_POLICY_MASK,
    DECODE_POLICY,
    ENCODE_POSITION,
    EVALUATE_POSITION,
    MAP_PLY_SLOTS,
    POLICY_SOFTMAX,
    READ_PLY_PROBABILITIES,
)
from .tensor_layout import (
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
    MOVEMENT_INDEX,
    TensorLayout,
)


def rotate_square(square: Square, layout: BoardLayout) -> Square:
    """The 180-degree board rotation: the shared side-to-move orientation
    transform. It is its own inverse, so encoder (orienting the input) and
    decoder (mapping preferences back to global-frame plies) stay consistent by
    applying the same function.

    Rotation is about the board's extent, so `layout` is the board being rotated
    within — the one the position is played on."""
    return Square(
        layout.columns - 1 - square.column,
        layout.rows + 1 - square.row,
    )

def rotate_ply(ply: CtfPly, layout: BoardLayout) -> CtfPly:
    return CtfPly(
        rotate_square(ply.source, layout),
        rotate_square(ply.destination, layout),
    )

def tensor_position(
    square: Square, active_player_id: Literal[1, -1], layout: BoardLayout
) -> tuple[int, int]:
    """`square` as 0-based tensor indices, in `(row, column)` order.

    Identity re-basing when White is to move; the 180-degree rotation when Black
    is to move, so the mover's back rank is always row 0.
    """
    if active_player_id == -1:
        square = rotate_square(square, layout)
    return square.row - 1, square.column


def policy_logit_location_for_ply(
    ply: CtfPly, active_player_id: Literal[1, -1], layout: BoardLayout
) -> tuple[int, int, int]:
    """The `(movement index, row, column)` slot in the action space a ply maps
    to, in the side-to-move frame."""
    tensor_from_row, tensor_from_column = tensor_position(
        ply.source, active_player_id, layout
    )
    tensor_to_row, tensor_to_column = tensor_position(
        ply.destination, active_player_id, layout
    )
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

    def __init__(self, model: nn.Module, tensor_layout: TensorLayout) -> None:
        """`tensor_layout` is the board and army this evaluator encodes — the
        run's, not a build default, so the same code encodes either ruleset."""
        super().__init__(model)
        self._tensor_layout = tensor_layout
        self._layout = tensor_layout.layout

        # What each per-rank quantity plane is normalised by: the army's full
        # count of that rank, so a plane reads 1.0 at full strength and falls as
        # the rank is attrited.
        #
        # A rank the composition does not field has a divisor of 0, and its plane
        # reads a constant 0.0 rather than a ratio — the rank is present in the
        # contract (see `TOTAL_FP_COUNT`) but absent from the army, so "none of
        # it remains" is both the true statement and the only finite one.
        self._rank_totals = {
            quantity_plane: tensor_layout.composition.count(piece)
            for (_ours, piece), quantity_plane in self._FP_PIECE_QUANTITY.items()
        }

        # Precomputed once per evaluator rather than per encoding: each is a
        # single row/column vector the flag-offset planes broadcast against, and
        # encoding is the hot path in self-play.
        self._row_indices = torch.arange(
            self._layout.rows, dtype=torch.float32
        ).unsqueeze(1)
        self._column_indices = torch.arange(
            self._layout.columns, dtype=torch.float32
        ).unsqueeze(0)

    @property
    def tensor_layout(self) -> TensorLayout:
        """The tensor contract this evaluator encodes to."""
        return self._tensor_layout

    def _fill_flag_offset_planes(
        self, encoded: Tensor, flag: tuple[int, int], row_plane: int, column_plane: int
    ) -> None:
        """Fill one flag's pair of signed offset planes, `flag` being its `(row,
        column)` in the mover's frame.

        Each square carries `(flag coordinate - own coordinate) / board extent`
        along one axis, so the sign tells the network which side of the flag it
        sits on -- in front of vs. behind, left vs. right -- which an absolute
        distance discards. Each plane varies along one axis only, so a single
        row/column vector broadcasts across it.
        """
        flag_row, flag_column = flag
        encoded[row_plane] = (flag_row - self._row_indices) / self._layout.rows
        encoded[column_plane] = (
            flag_column - self._column_indices
        ) / self._layout.columns

    @timed(EVALUATE_POSITION)
    def evaluate_position(self, position: CtfPosition) -> PositionEvaluation:
        """Time the whole evaluation, then defer to the shared implementation.

        Search spends most of a self-play game inside this call, and its three
        instrumented children (encoding, forward pass, policy decoding) do not
        add up to it — the difference is the base class's own per-call overhead,
        which is worth seeing rather than hiding. The override exists only to
        name the region; the evaluation itself stays where it was.
        """
        return super().evaluate_position(position)

    @timed(ENCODE_POSITION)
    def encode_position(self, position: CtfPosition) -> Tensor:
        # A position from another board would index cleanly into this one's
        # tensor -- an 8x8 board's squares are all valid 12x12 indices -- so
        # without this the wrong board encodes silently rather than failing. The
        # shapes now follow the run's configuration, so this is no longer a
        # stand-in for that; it is the standing invariant that an evaluator
        # encodes the board it was built for.
        if position.layout != self._layout:
            raise ValueError(
                f"this evaluator encodes {self._layout.layout_id} positions; "
                f"got a {position.layout.layout_id} position"
            )
        # tensor expected to be (batch, channels, height, width)
        # batch will be handled later - we just need to do the last three here
        encoded = torch.zeros(self._tensor_layout.input_shape, dtype=torch.float32)

        # Current pieces on board. This single pass also collects what the two
        # engineered plane families need — where each flag stands, and how many
        # of each mobile rank survive — since both are functions of the same
        # board traversal, and encoding is the hot path in self-play.
        our_flag: tuple[int, int] | None = None
        their_flag: tuple[int, int] | None = None
        piece_strength = dict.fromkeys(CtfNNEvaluator._FP_PIECE_QUANTITY.values(), 0)
        for square, (side, piece_type) in position.board.items():
            tensor_row, tensor_column = tensor_position(
                square, position.active_player_id, self._layout
            )
            ours = side == position.side_to_move
            fp = CtfNNEvaluator._OUR_FP[piece_type] if ours else CtfNNEvaluator._THEIR_FP[piece_type]
            encoded[fp, tensor_row, tensor_column] = 1
            if piece_type is PieceType.FLAG:
                if ours:
                    our_flag = (tensor_row, tensor_column)
                else:
                    their_flag = (tensor_row, tensor_column)
            quantity_fp = CtfNNEvaluator._FP_PIECE_QUANTITY.get((ours, piece_type))
            if quantity_fp is not None:
                piece_strength[quantity_fp] += 1
        # Passable squares / Lake squares
        encoded[FP_PASSABLE, :, :].fill_(1)
        for lake_square in self._layout.lake_squares:
            tensor_row, tensor_column = tensor_position(
                lake_square, position.active_player_id, self._layout
            )
            encoded[FP_PASSABLE, tensor_row, tensor_column] = 0
        # Draw-by-inactivity counter
        move_limit_ratio = position.inactivity_counter / INACTIVITY_LIMIT
        encoded[FP_INACTIVITY_COUNT, :, :].fill_(move_limit_ratio)
        # Flags relative position. Both flags stand on the board throughout play —
        # a flag leaves it only by being captured, which ends the game — so a
        # missing one means a terminal position reached the encoder. Nothing in
        # the engine's own wiring does that (MCTS and the self-play collector both
        # short-circuit on `outcome`), so this is a caller error worth naming
        # rather than a state to encode some default for.
        if our_flag is None or their_flag is None:
            missing = "own" if our_flag is None else "enemy"
            raise ValueError(
                f"cannot encode a position with no {missing} flag on the board: "
                "the flag-relative offset planes are undefined for it. A flag is "
                "only ever removed by capture, which ends the game, so this is a "
                "terminal position."
            )
        self._fill_flag_offset_planes(
            encoded, our_flag, FP_OUR_FLAG_RELATIVE_ROW, FP_OUR_FLAG_RELATIVE_COLUMN
        )
        self._fill_flag_offset_planes(
            encoded, their_flag, FP_THEIR_FLAG_RELATIVE_ROW, FP_THEIR_FLAG_RELATIVE_COLUMN
        )
        # Army strength
        for feature_plane, quantity in piece_strength.items():
            roster = self._rank_totals[feature_plane]
            encoded[feature_plane, :, :].fill_(quantity / roster if roster else 0.0)

        return encoded

    @timed(DECODE_POLICY)
    def decode_policy(self, policy_logits: Tensor, position: CtfPosition) -> dict[str, float]:
        # Each of the four phases below is timed separately: decoding is entered
        # once per position evaluation — over a million times in a training run —
        # and the phases have very different characters (two walk the legal plies
        # a tensor element at a time, one is a single fused tensor op), so a
        # single figure for the whole call says nothing about which to attack.
        #
        # The legal plies are read *before* the first region opens: `legal_plies`
        # is itself timed, and reading it inside `map-ply-slots` would bury its
        # cost under that phase instead of leaving it the sibling of these four it
        # has always been.
        legal_plies = position.legal_plies
        action_space_shape = self._tensor_layout.action_space_shape

        # identify location in policy_logits tensor for all legal plies
        with region(MAP_PLY_SLOTS):
            legal_ply_mapping: dict[tuple[int, int, int], CtfPly] = {}
            for ply in legal_plies:
                logit_location = policy_logit_location_for_ply(
                    ply, position.active_player_id, self._layout
                )
                legal_ply_mapping[logit_location] = ply

        # create filter, starting with all positions masked, and unmasking legal plies
        with region(BUILD_POLICY_MASK):
            mask = torch.full(action_space_shape, float('-inf'))
            for policy_logit_location in legal_ply_mapping:
                mask[policy_logit_location] = 0.0

        # create a probability for all legal plies, summing to one
        # masked locations in policy_logits will receive a probability of 0
        with region(POLICY_SOFTMAX):
            masked = policy_logits + mask
            probabilities = F.softmax(masked.flatten(), dim = -1).reshape(action_space_shape)

        # map the probabilities back to valid plies
        with region(READ_PLY_PROBABILITIES):
            return {str(ply): probabilities[policy_logit_location].item() for (policy_logit_location, ply) in legal_ply_mapping.items()}

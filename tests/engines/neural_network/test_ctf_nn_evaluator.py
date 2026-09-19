from types import MappingProxyType

import pytest
import torch
import torch.nn as nn
from game_engine_core.engines.mcts_engine import MCTSEngine
from torch import Tensor

from capture_the_flag.board import SIMPLE_64, Square
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import (
    CtfNNEvaluator,
    policy_logit_location_for_ply,
    rotate_ply,
    rotate_square,
)
from capture_the_flag.engines.neural_network.tensor_layout import (
    FP_INACTIVITY_COUNT,
    FP_OUR_FLAG,
    FP_OUR_RANK_5,
    FP_PASSABLE,
    FP_THEIR_FLAG,
    FP_THEIR_RANK_4,
    MOVEMENT_INDEX,
    TOTAL_FP_COUNT,
)
from capture_the_flag.outcome import INACTIVITY_LIMIT
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.ply import CtfPly
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side
from tests.engines.neural_network.small_networks import (
    OTHER_SETUP,
    OTHER_TENSOR_LAYOUT,
    PRE_RELEASE_TENSOR_LAYOUT,
    small_network,
)

_ACTION_SPACE_SHAPE = PRE_RELEASE_TENSOR_LAYOUT.action_space_shape


def _dummy_model():
    # Simple dummy model for testing—CtfNNEvaluator only uses encode_positions, not the model itself
    return nn.Linear(1, 1)

def _position(board: dict, side_to_move: Side = Side.WHITE, inactivity_counter: int = 0) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=inactivity_counter,
        layout=SIMPLE_64,
    )

def _matching_white_position(inactivity_counter: int = 0) -> CtfPosition:
    board = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(3, 3): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(4, 6): (Side.BLACK, P.CHAMPION),
        Square(7, 8): (Side.BLACK, P.FLAG),
    }

    return _position(board,side_to_move=Side.WHITE,inactivity_counter=inactivity_counter)

def _matching_black_position(inactivity_counter: int = 0) -> CtfPosition:
    # The same physical position as `_matching_white_position`, every square
    # rotated 180 degrees on SIMPLE_64 and every side swapped -- so it is the
    # position White's fixture describes, seen from Black's side of the board.
    board = {
        Square(7, 8): (Side.BLACK, P.FLAG),
        Square(4, 6): (Side.BLACK, P.MASTER_OF_ARMS),
        Square(3, 3): (Side.WHITE, P.CHAMPION),
        Square(0, 1): (Side.WHITE, P.FLAG),
    }

    return _position(board,side_to_move=Side.BLACK,inactivity_counter=inactivity_counter)

def _base_position(side_to_move: Side, inactivity_counter: int = 0) -> CtfPosition:
    board = {
        Square(3, 1): (Side.WHITE, P.FLAG),
        Square(2, 1): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(3, 2): (Side.WHITE, P.MASTER_OF_ARMS),
        Square(3, 8): (Side.BLACK, P.FLAG),
        Square(0, 7): (Side.BLACK, P.CHAMPION),
        Square(1, 7): (Side.BLACK, P.CHAMPION),
        Square(2, 7): (Side.BLACK, P.CHAMPION),
        Square(3, 7): (Side.BLACK, P.CHAMPION),
        Square(4, 7): (Side.BLACK, P.CHAMPION),
        Square(5, 7): (Side.BLACK, P.CHAMPION),
    }

    return _position(board,side_to_move=side_to_move,inactivity_counter=inactivity_counter)


def _check_tensor_piece_fill(encoded: Tensor, expected_piece_placements: set[tuple[int, int, int]]) -> None:
    # Expected tuples are (plane, column, row) — board-natural order, 0-based —
    # transposed to the tensor's (plane, row, column) at the point of indexing.
    # Bounded at FP_PASSABLE, the first non-piece plane: passability and
    # inactivity are constant broadcasts, not piece placements, so they are out
    # of scope for a checker that asserts everything else reads zero.
    for fp in range(FP_PASSABLE):
        for column in range(8):
            for row in range(8):
                expected_value = 1 if (fp, column, row) in expected_piece_placements else 0
                assert encoded[fp, row, column] == expected_value

def _check_tensor_all_passable(encoded: Tensor) -> None:
    # SIMPLE_64 has no impassable squares at all (`doc/ruleset/CLAUDE.md`), so
    # the passability plane is uniformly open here.
    for column in range(SIMPLE_64.columns):
        for row in range(SIMPLE_64.rows):
            assert encoded[FP_PASSABLE, row, column] == 1

_A2A4_H7H5:tuple[int,int,int] = MOVEMENT_INDEX[(2, 0)], 1, 0
_D4D5_E5E4:tuple[int,int,int] = MOVEMENT_INDEX[(1, 0)], 3, 3
_H7G7_A2B2:tuple[int,int,int] = MOVEMENT_INDEX[(0, -1)], 6, 7

def _setup_policy_logits(seed = 987) -> Tensor:
    torch.manual_seed(seed)

    policy_logits = torch.empty(_ACTION_SPACE_SHAPE)
    policy_logits.uniform_(-10, 10)
    policy_logits[_A2A4_H7H5] = 3.0
    policy_logits[_D4D5_E5E4] = 10.0
    policy_logits[_H7G7_A2B2] = 25.0
    return policy_logits

def _setup_position_legal_plies(side: Side, monkeypatch) -> CtfPosition:
    board = {}
    position = CtfPosition(board, side, 0, SIMPLE_64)
    square_1_from = Square(0, 2) if side == Side.WHITE else Square(7, 7)
    square_1_to = Square(0, 4) if side == Side.WHITE else Square(7, 5)
    square_2_from = Square(3, 4) if side == Side.WHITE else Square(4, 5)
    square_2_to = Square(3, 5) if side == Side.WHITE else Square(4, 4)
    square_3_from = Square(7, 7) if side == Side.WHITE else Square(0, 2)
    square_3_to = Square(6, 7) if side == Side.WHITE else Square(1, 2)

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
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    encoded = evaluator.encode_positions([position])[0]
    expected_piece_placements = {
        (FP_OUR_FLAG, 0, 0),
        (FP_OUR_RANK_5, 3, 2),
        (FP_THEIR_RANK_4, 4, 5),
        (FP_THEIR_FLAG, 7, 7),
    }
    _check_tensor_piece_fill(encoded, expected_piece_placements)
    _check_tensor_all_passable(encoded)

@pytest.mark.parametrize(
    "inactivity_counter",
    [0, 10, 39]
)
def test_matching_positions_equivalent(inactivity_counter):
    white_position = _matching_white_position(inactivity_counter)
    black_position = _matching_black_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    white_encoded = evaluator.encode_positions([white_position])[0]
    black_encoded = evaluator.encode_positions([black_position])[0]

    assert torch.equal(white_encoded, black_encoded)

@pytest.mark.parametrize(
    "inactivity_counter",
    [0, 10, 39]
)
def test_inactivity_counter_consistent(inactivity_counter):
    position = _matching_white_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    encoded = evaluator.encode_positions([position])[0]

    ref_value = encoded[FP_INACTIVITY_COUNT, 0, 0]
    # TODO use constants here
    for row in range(8):
        for column in range(8):
            # we should be able to test for exact equality even with floats (should be exactly the same float)
            assert encoded[FP_INACTIVITY_COUNT, row, column] == ref_value

@pytest.mark.parametrize(
    "inactivity_counter",
    [0, 10, 39]
)
def test_inactivity_counter_populated(inactivity_counter):
    position = _matching_white_position(inactivity_counter)

    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    encoded = evaluator.encode_positions([position])[0]

    expected_value = inactivity_counter / INACTIVITY_LIMIT
    # TODO use constants here
    for row in range(8):
        for column in range(8):
            assert encoded[FP_INACTIVITY_COUNT, row, column] == pytest.approx(expected_value)

@pytest.mark.parametrize(
    "layout",
    [SIMPLE_64, OTHER_SETUP.layout],
    ids=["simple_64", "other"],
)
def test_rotate_square_involution(layout):
    for column in range(layout.columns):
        for row in range(1, layout.rows + 1):
            original_square = Square(column, row)
            rotated_once = rotate_square(original_square, layout)
            rotated_twice = rotate_square(rotated_once, layout)
            assert original_square.column == rotated_twice.column
            assert original_square.row == rotated_twice.row

@pytest.mark.parametrize(
    "rotation",
    [
        (0, 1, 7, 8), # A1 => H8
        (7, 1, 0, 8), # H1 => A8
        (3, 6, 4, 3), # D6 => E3
    ]
)
def test_rotate_square_rotates_180_degrees(rotation):
    column_original, row_original, column_expected, row_expected = rotation

    original_square = Square(column_original, row_original)
    rotated_square = rotate_square(original_square, SIMPLE_64)

    assert rotated_square.column == column_expected
    assert rotated_square.row == row_expected

def test_rotate_square_rotates_about_its_own_board():
    # The same square rotates to two different places on two different boards --
    # which is the whole reason the layout is a parameter rather than a constant.
    assert str(rotate_square(Square(0, 1), SIMPLE_64)) == "H8"
    assert str(rotate_square(Square(0, 1), OTHER_SETUP.layout)) == "D6"

def test_rotate_ply_rotates_180_degrees():
    original = CtfPly(Square(2, 3), Square(2, 4))
    rotated = rotate_ply(original, SIMPLE_64)

    assert str(rotated) == "F6F5"

@pytest.mark.parametrize(
    "active_player_id",
    [1, -1],
    ids=["White", "Black"],
)
@pytest.mark.parametrize(
    "tensor_layout",
    [PRE_RELEASE_TENSOR_LAYOUT, OTHER_TENSOR_LAYOUT],
    ids=["pre_release", "other"],
)
def test_policy_logit_location_for_ply_is_bijective(tensor_layout, active_player_id):
    # note: this does include illegal moves (to off-board locations) that exist in the policy_logit
    layout = tensor_layout.layout
    action_space_shape = tensor_layout.action_space_shape
    filled: set[tuple[int,int,int]] = set()
    for column in range(layout.columns):
        for row in range(1, layout.rows + 1):
            for row_delta, column_delta in MOVEMENT_INDEX.keys():
                from_square = Square(column, row)
                to_square = Square(column + column_delta, row + row_delta)
                ply = CtfPly(from_square, to_square)
                location = policy_logit_location_for_ply(ply, active_player_id, layout)
                assert 0 <= location[0] < action_space_shape[0]
                assert 0 <= location[1] < action_space_shape[1]
                assert 0 <= location[2] < action_space_shape[2]
                assert location not in filled
                filled.add(location)

@pytest.mark.parametrize(
    "side_values",
    [(Side.WHITE, "A2A4", "D4D5", "H7G7"), (Side.BLACK, "H7H5", "E5E4", "A2B2")],
    ids=["White", "Black"],
)
def test_decode_policy_returns_valid_policy_dict(side_values, monkeypatch):
    side, pos1, pos2, pos3, = side_values

    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)

    policy_logits = _setup_policy_logits()
    position = _setup_position_legal_plies(side, monkeypatch)

    policy_dict = evaluator.decode_policies(policy_logits.unsqueeze(0), [position])[0]

    assert len(policy_dict) == 3

    assert pos1 in policy_dict
    assert pos2 in policy_dict
    assert pos3 in policy_dict

    assert policy_dict[pos3] > policy_dict[pos2] > policy_dict[pos1]

    assert sum(policy_dict.values()) == pytest.approx(1.0)

@pytest.mark.parametrize(
    "side_values",
    [(Side.WHITE, "A2A4", "D4D5", "H7G7"), (Side.BLACK, "H7H5", "E5E4", "A2B2")],
    ids=["White", "Black"],
)
def test_decode_policy_ignores_masked_indices(side_values, monkeypatch):
    side, pos1, pos2, pos3, = side_values

    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)

    policy_logits_a = _setup_policy_logits(1234)
    policy_logits_b = _setup_policy_logits(2345)
    position = _setup_position_legal_plies(side, monkeypatch)

    policy_dict_a = evaluator.decode_policies(policy_logits_a.unsqueeze(0), [position])[0]
    policy_dict_b = evaluator.decode_policies(policy_logits_b.unsqueeze(0), [position])[0]

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
    evaluator = CtfNNEvaluator(nn, PRE_RELEASE_TENSOR_LAYOUT)

    position = _base_position(side_to_move, 0)
    evaluation = evaluator.evaluate_positions([position])[0]

    assert -1 <= evaluation.value <= 1
    assert evaluation.policy is not None
    assert set(evaluation.policy.keys()) == {str(ply) for ply in position.legal_plies}
    assert all(value >= 0 for value in evaluation.policy.values())
    assert sum(evaluation.policy.values()) == pytest.approx(1.0)

# The batch contract. Everything above passes one position at a time, which an
# implementation that ignored every position after the first would still satisfy —
# so these four are the ones that actually pin index alignment. Each uses two
# positions that differ in what they produce, because a batch of identical
# positions cannot tell alignment from luck.

def test_encode_stacks_the_batch_in_position_order():
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    positions = [_matching_white_position(), _base_position(Side.WHITE, 0)]

    encoded = evaluator.encode_positions(positions)

    assert tuple(encoded.shape) == (2, *PRE_RELEASE_TENSOR_LAYOUT.input_shape)
    for row, position in enumerate(positions):
        assert torch.equal(encoded[row], evaluator.encode_positions([position])[0])
    assert not torch.equal(encoded[0], encoded[1])

def test_decode_aligns_each_policy_with_its_own_position():
    # Side to move decides which plies are legal, so the two positions produce
    # disjoint key sets: decoding both rows against positions[0] would fail here
    # rather than merely return the wrong probabilities.
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    positions = [_base_position(Side.WHITE, 0), _base_position(Side.BLACK, 0)]
    policy_logits = torch.stack([_setup_policy_logits(1234), _setup_policy_logits(2345)])

    policies = evaluator.decode_policies(policy_logits, positions)

    assert len(policies) == 2
    for policy, position in zip(policies, positions, strict=True):
        assert set(policy) == {str(ply) for ply in position.legal_plies}
        assert sum(policy.values()) == pytest.approx(1.0)

def test_decode_rejects_a_logit_batch_that_does_not_match_the_positions():
    # A model returning the wrong batch size would otherwise decode the shorter of
    # the two and return a result silently missing its tail.
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)
    positions = [_base_position(Side.WHITE, 0), _base_position(Side.BLACK, 0)]

    with pytest.raises(ValueError):
        evaluator.decode_policies(_setup_policy_logits().unsqueeze(0), positions)

def test_evaluate_returns_one_evaluation_per_position_in_order():
    evaluator = CtfNNEvaluator(small_network(), PRE_RELEASE_TENSOR_LAYOUT)
    positions = [_base_position(Side.WHITE, 0), _base_position(Side.BLACK, 0)]

    evaluations = evaluator.evaluate_positions(positions)

    assert len(evaluations) == 2
    for evaluation, position in zip(evaluations, positions, strict=True):
        assert -1 <= evaluation.value <= 1
        assert set(evaluation.policy) == {str(ply) for ply in position.legal_plies}

def test_evaluate_of_an_empty_batch_evaluates_nothing():
    # Routine rather than a misuse: a fleet wave whose every selected leaf is
    # terminal reaches the evaluator with nothing to evaluate.
    evaluator = CtfNNEvaluator(small_network(), PRE_RELEASE_TENSOR_LAYOUT)

    assert evaluator.evaluate_positions([]) == []

def test_encode_of_an_empty_batch_is_an_empty_batch():
    # The same empty wave one level down, where torch.stack would raise rather
    # than produce the zero-row batch the shape contract implies.
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)

    encoded = evaluator.encode_positions([])

    assert tuple(encoded.shape) == (0, *PRE_RELEASE_TENSOR_LAYOUT.input_shape)

@pytest.mark.parametrize(
    "side_to_move",
    [Side.WHITE, Side.BLACK,],
)
def test_evaluator_in_engine_with_actual_nn_returns_valid_ply(side_to_move):

    nn = small_network()
    engine: MCTSEngine[CtfPly, CtfPosition, CtfNNEvaluator] = MCTSEngine(
        evaluator = CtfNNEvaluator(nn, PRE_RELEASE_TENSOR_LAYOUT),
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

# --- Configuration-driven encoding (story 37, step 8) ------------------------
#
# Everything above is the one published board and army. Major 2's Skirmish
# played this role before major 3 collapsed the board and army to one of each
# (`doc/ruleset/CLAUDE.md`); `OTHER_SETUP` (a hand-built setup naming no
# published edition, see `small_networks.py`) plays it now. These assert the
# part that is no longer a build constant: the tensor's extent comes from the
# configured layout.

def _other_position(
    board: dict, side_to_move: Side = Side.WHITE, inactivity_counter: int = 0
) -> CtfPosition:
    return CtfPosition(
        board=MappingProxyType(board),
        side_to_move=side_to_move,
        inactivity_counter=inactivity_counter,
        layout=OTHER_SETUP.layout,
    )

def _other_full_army_position() -> CtfPosition:
    # `OTHER_SETUP` fields 3 Peasants and a Flag per side, laid out along each
    # home row. The exact squares do not matter to these assertions; that they
    # are on a small board and field a small army does.
    board: dict[Square, tuple[Side, P]] = {
        Square(0, 1): (Side.WHITE, P.FLAG),
        Square(1, 1): (Side.WHITE, P.PEASANT),
        Square(2, 1): (Side.WHITE, P.PEASANT),
        Square(3, 1): (Side.WHITE, P.PEASANT),
        Square(0, 6): (Side.BLACK, P.FLAG),
        Square(1, 6): (Side.BLACK, P.PEASANT),
        Square(2, 6): (Side.BLACK, P.PEASANT),
        Square(3, 6): (Side.BLACK, P.PEASANT),
    }
    return _other_position(board)

def test_encode_is_shaped_by_the_configured_board():
    evaluator = CtfNNEvaluator(_dummy_model(), OTHER_TENSOR_LAYOUT)

    encoded = evaluator.encode_positions([_other_full_army_position()])[0]

    assert tuple(encoded.shape) == OTHER_TENSOR_LAYOUT.input_shape
    assert tuple(encoded.shape) == (TOTAL_FP_COUNT, 6, 4)

def test_encode_leaves_the_passable_plane_uniformly_open_on_any_board():
    # `BoardLayout` carries no impassable squares since major 3 deleted lakes
    # (story 00000049 step 4), on `OTHER_SETUP`'s board as much as the
    # published one -- so this plane reads 1.0 everywhere regardless of which
    # board is configured. It is retained rather than dropped: it is what lets
    # the network tell a real edge square from the zero-padding a convolution
    # adds at the border (`eng-nn-4.md`).
    evaluator = CtfNNEvaluator(_dummy_model(), OTHER_TENSOR_LAYOUT)

    encoded = evaluator.encode_positions([_other_full_army_position()])[0]

    assert torch.all(encoded[FP_PASSABLE] == 1)

def test_encode_rejects_a_position_from_another_board():
    # A 4x6 board's squares are all valid 8x8 indices, so a position from the
    # smaller board would encode silently into this tensor rather than failing.
    evaluator = CtfNNEvaluator(_dummy_model(), PRE_RELEASE_TENSOR_LAYOUT)

    with pytest.raises(ValueError, match="simple_64"):
        evaluator.encode_positions([_other_full_army_position()])

def test_evaluator_with_actual_other_nn_returns_valid_evaluation():
    evaluator = CtfNNEvaluator(
        small_network(OTHER_TENSOR_LAYOUT), OTHER_TENSOR_LAYOUT
    )

    position = _other_full_army_position()
    evaluation = evaluator.evaluate_positions([position])[0]

    assert -1 <= evaluation.value <= 1
    assert evaluation.policy is not None
    assert set(evaluation.policy.keys()) == {str(ply) for ply in position.legal_plies}
    assert sum(evaluation.policy.values()) == pytest.approx(1.0)

"""Tests for the self-play collection wiring (story 00000009, Step 3).

Exercises `build_self_play_collector` end to end at a tiny search budget: the
collected `TrainingSample`s must be structurally valid, their value targets must
alternate down a game, and the capture-time transform must reframe Black-to-move
visit distributions into the network's white-normalized frame.
"""

import pytest
from game_engine_learning.self_play_collector import SelfPlayCollector

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.ctf_engine_factory import CtfEngineFactory
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.engines.neural_network.ctf_self_play import (
    build_self_play_collector,
)
from capture_the_flag.engines.neural_network.tensor_layout import INPUT_SHAPE
from capture_the_flag.engines.neural_network.ctf_policy_target import (
    transform_policy_to_white_perspective,
)


def _evaluator() -> CtfNNEvaluator:
    return CtfNNEvaluator(CtfCrn())


def _fast_engine_factory(evaluator: CtfNNEvaluator) -> CtfEngineFactory:
    # A tiny search budget with non-zero temperature: cheap enough for a test,
    # exploratory enough to visit both movers and spread the visit distribution.
    return CtfEngineFactory(evaluator, iterations=8, temperature=1.0)


def test_build_self_play_collector_wires_the_game_specific_pieces():
    evaluator = _evaluator()
    collector = build_self_play_collector(evaluator)

    assert isinstance(collector, SelfPlayCollector)
    assert collector._evaluator is evaluator
    assert isinstance(collector._position_factory, CtfPositionFactory)
    # Forgetting the transform is the plan's silent-failure mode (the policy head
    # trained against mis-framed targets), so pin that it is actually wired in.
    assert collector._policy_transform is transform_policy_to_white_perspective


def test_collect_produces_structurally_valid_samples():
    evaluator = _evaluator()
    collector = build_self_play_collector(evaluator, _fast_engine_factory(evaluator))

    samples = collector.collect(2)

    assert samples
    for sample in samples:
        assert tuple(sample.encoded_position.shape) == INPUT_SHAPE
        assert sample.target_value in (-1.0, 0.0, 1.0)
        probs = list(sample.target_policy.values())
        assert probs  # a distribution over at least one ply
        assert all(p >= 0.0 for p in probs)
        assert sum(probs) == pytest.approx(1.0)


def test_target_values_alternate_within_a_game():
    evaluator = _evaluator()
    collector = build_self_play_collector(evaluator, _fast_engine_factory(evaluator))

    values = [sample.target_value for sample in collector.collect(1)]

    assert values
    # The outcome propagates backward with the sign flipping every ply, so
    # consecutive targets are negatives of each other. A draw degenerates this
    # to an all-zero sequence, which still satisfies the relation.
    assert all(nxt == -prev for prev, nxt in zip(values, values[1:], strict=False))


def test_capture_time_transform_reframes_black_to_move_distributions():
    evaluator = _evaluator()
    captures: list[tuple[object, dict[str, float], dict[str, float]]] = []

    def spy_transform(position, policy):
        transformed = transform_policy_to_white_perspective(position, policy)
        captures.append((position, policy, transformed))
        return transformed

    collector = SelfPlayCollector(
        evaluator=evaluator,
        engine_factory=_fast_engine_factory(evaluator),
        position_factory=CtfPositionFactory(),
        policy_transform=spy_transform,
    )
    collector.collect(1)

    assert captures
    white = [c for c in captures if c[0].active_player_id == 1]
    black = [c for c in captures if c[0].active_player_id == -1]
    assert white and black  # a real game alternates movers, so both appear

    # White to move: the network frame already matches the global frame, so the
    # transform is the identity and the raw visit distribution is stored as-is.
    for _position, raw, transformed in white:
        assert transformed == raw

    # Black to move: the distribution is re-keyed into the white-normalized frame
    # (keys change) while its mass is merely permuted (values preserved, still a
    # distribution) — reframing without corrupting the target.
    for position, raw, transformed in black:
        legal = {str(ply) for ply in position.legal_plies}
        assert set(raw) <= legal
        assert set(transformed) != set(raw)
        assert sorted(transformed.values()) == pytest.approx(sorted(raw.values()))
        assert sum(transformed.values()) == pytest.approx(1.0)

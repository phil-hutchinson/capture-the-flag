"""What the learned-evaluator path records, and how it nests.

Names, counts, and nesting only — never durations (real wall clock here).
"""

from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.instrumentation.timing import timing_session
from capture_the_flag.timing_regions import (
    DECODE_POLICY,
    ENCODE_POSITION,
    EVALUATE_POSITION,
    LEGAL_PLIES,
    NETWORK_FORWARD,
)
from tests.engines.neural_network.small_networks import small_network

from .test_mechanics_regions import child, ongoing_position


def test_evaluation_children_nest_under_the_evaluation() -> None:
    evaluator = CtfNNEvaluator(small_network())
    position = ongoing_position()

    with timing_session("test") as session:
        for _ in range(3):
            evaluator.evaluate_position(position)

    evaluate = child(session.root, EVALUATE_POSITION)
    assert evaluate.calls == 3
    assert child(evaluate, ENCODE_POSITION).calls == 3
    assert child(evaluate, NETWORK_FORWARD).calls == 3
    assert child(evaluate, DECODE_POLICY).calls == 3
    # Nothing escaped to the root: the three are children, not siblings.
    assert set(session.root.children) == {EVALUATE_POSITION}


def test_evaluation_keeps_an_unattributed_remainder_of_its_own() -> None:
    """The shared base class's per-call wrapping — eval-mode switching, batching
    a single sample, unwrapping the value tensor — is real time inside
    `evaluate-position` that none of its children explain."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.evaluate_position(ongoing_position())

    assert child(session.root, EVALUATE_POSITION).unattributed_ns > 0


def test_policy_decoding_pays_for_a_ply_generation() -> None:
    """Decoding masks illegal plies, so it regenerates the legal plies — cost
    attributed to the decode rather than pooled with the caller's own."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.evaluate_position(ongoing_position())

    decode = child(session.root, EVALUATE_POSITION, DECODE_POLICY)
    assert child(decode, LEGAL_PLIES).calls == 1


def test_encoding_alone_records_without_an_evaluation() -> None:
    """`encode_position` is also called directly (the self-play collector encodes
    each step), so it records at whatever depth the caller sits."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.encode_position(ongoing_position())

    assert child(session.root, ENCODE_POSITION).calls == 1
    assert EVALUATE_POSITION not in session.root.children


def test_batched_forward_passes_record_at_the_callers_depth() -> None:
    """Training pushes minibatches through the same region; the call path — not
    the name — is what separates it from search's single-position passes."""
    import torch

    from capture_the_flag.engines.neural_network.tensor_layout import INPUT_SHAPE

    network = small_network()
    batch = torch.zeros((4, *INPUT_SHAPE), dtype=torch.float32)

    with timing_session("test") as session:
        network(batch)

    assert child(session.root, NETWORK_FORWARD).calls == 1

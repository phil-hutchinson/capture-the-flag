"""What the learned-evaluator path records, and how it nests.

Names, counts, and nesting only — never a duration, since this runs on real wall
clock. The one exception is a *share* of a parent region, asserted with a bound
coarse enough that no machine's noise can reach it: whether a region's children
account for it is the question this path's instrumentation exists to answer, so
it is worth an assertion despite the timings underneath being unreproducible.
"""

from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.instrumentation.timing import timing_session
from capture_the_flag.timing_regions import (
    BUILD_POLICY_MASK,
    DECODE_POLICY,
    ENCODE_POSITION,
    EVALUATE_POSITION,
    LEGAL_PLIES,
    MAP_PLY_SLOTS,
    NETWORK_FORWARD,
    NETWORK_MODE_SWITCH,
    POLICY_SOFTMAX,
    READ_PLY_PROBABILITIES,
)
from tests.engines.neural_network.small_networks import small_network

from .test_mechanics_regions import child, ongoing_position

DECODE_PHASES = (
    MAP_PLY_SLOTS,
    BUILD_POLICY_MASK,
    POLICY_SOFTMAX,
    READ_PLY_PROBABILITIES,
)
"""The four phases of a decode, in the order `decode_policy` performs them."""


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
    assert child(evaluate, NETWORK_MODE_SWITCH).calls == 3
    # Nothing escaped to the root: the four are children, not siblings.
    assert set(session.root.children) == {EVALUATE_POSITION}


def test_evaluation_keeps_an_unattributed_remainder_of_its_own() -> None:
    """The shared base class's per-call tensor plumbing — batching a single
    sample, unwrapping the value tensor, entering the no-grad context — is real
    time inside `evaluate-position` that none of its children explain. It is left
    unnamed deliberately: naming it would mean copying that class's body here."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.evaluate_position(ongoing_position())

    assert child(session.root, EVALUATE_POSITION).unattributed_ns > 0


def test_the_mode_switch_is_charged_to_the_evaluation_that_triggers_it() -> None:
    """The shared evaluator switches the model to eval mode on every call, and
    torch implements that as a recursive walk over every submodule — the largest
    single item in what `evaluate-position` used to leave unattributed. The region
    lives on the network, so the call path is what charges it to the evaluation."""
    evaluator = CtfNNEvaluator(small_network())
    position = ongoing_position()

    with timing_session("test") as session:
        for _ in range(3):
            evaluator.evaluate_position(position)

    evaluate = child(session.root, EVALUATE_POSITION)
    assert child(evaluate, NETWORK_MODE_SWITCH).calls == 3
    assert NETWORK_MODE_SWITCH not in session.root.children


def test_mode_switches_outside_an_evaluation_record_at_the_callers_depth() -> None:
    """Training flips the shared model to train mode and back, so the same region
    appears on the training branch too — one name, separated by call path. `eval()`
    routes through `train(False)`, which is why both are counted here."""
    network = small_network()

    with timing_session("test") as session:
        network.train()
        network.eval()

    assert child(session.root, NETWORK_MODE_SWITCH).calls == 2


def test_policy_decoding_pays_for_a_ply_generation() -> None:
    """Decoding masks illegal plies, so it regenerates the legal plies — cost
    attributed to the decode rather than pooled with the caller's own."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.evaluate_position(ongoing_position())

    decode = child(session.root, EVALUATE_POSITION, DECODE_POLICY)
    assert child(decode, LEGAL_PLIES).calls == 1


def test_decoding_records_each_of_its_phases() -> None:
    """Decoding is entered once per evaluation — over a million times in a
    training run — and its phases differ in kind: two walk the legal plies a
    tensor element at a time, one is a single fused tensor op. A single figure for
    the call would not say which to attack."""
    evaluator = CtfNNEvaluator(small_network())
    position = ongoing_position()

    with timing_session("test") as session:
        for _ in range(3):
            evaluator.evaluate_position(position)

    decode = child(session.root, EVALUATE_POSITION, DECODE_POLICY)
    for phase in DECODE_PHASES:
        assert child(decode, phase).calls == 3
    # One region per decode, never one per ply — a phase's own loop over the
    # legal plies stays uninstrumented, so the counts follow decodes, not plies.
    assert decode.calls == 3


def test_ply_generation_stays_a_sibling_of_the_decode_phases() -> None:
    """Decoding reads the legal plies before opening its first phase, so the
    already-timed `legal-plies` region stays where it has always been: beside the
    phases, not buried inside the one that consumes them. Records taken before the
    phases existed therefore remain comparable line for line."""
    evaluator = CtfNNEvaluator(small_network())

    with timing_session("test") as session:
        evaluator.evaluate_position(ongoing_position())

    decode = child(session.root, EVALUATE_POSITION, DECODE_POLICY)
    assert child(decode, LEGAL_PLIES).calls == 1
    assert LEGAL_PLIES not in child(decode, MAP_PLY_SLOTS).children


def test_the_phases_account_for_the_decode() -> None:
    """The gap this subdivision exists to close: three quarters of `decode-policy`
    used to have no name, which put a ceiling on what any optimization of it could
    claim. What is left over now is region-entry overhead — bounded loosely here,
    since the underlying durations are real wall clock."""
    evaluator = CtfNNEvaluator(small_network())
    position = ongoing_position()

    with timing_session("test") as session:
        for _ in range(10):
            evaluator.evaluate_position(position)

    decode = child(session.root, EVALUATE_POSITION, DECODE_POLICY)
    assert decode.unattributed_ns * 3 < decode.elapsed_ns


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

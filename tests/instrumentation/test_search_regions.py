"""The search boundary: what a call into the shared engine records, and what its
unattributed remainder means.

This is the story's headline measurement, so the assertions are about *shape*:
our instrumented work must appear beneath the search region rather than beside
it, and what is left over must be the engine's own internals.
"""

from capture_the_flag.engines.neural_network.ctf_engine_factory import CtfEngineFactory
from capture_the_flag.engines.neural_network.ctf_nn_evaluator import CtfNNEvaluator
from capture_the_flag.engines.neural_network.neural_ctf_player import (
    build_neural_player,
)
from capture_the_flag.instrumentation.timed_search import (
    SEARCH,
    SEARCH_RESET,
    SEARCH_WITH_POLICY,
    TimedMCTSEngine,
)
from capture_the_flag.instrumentation.timing import timing_session
from capture_the_flag.timing_regions import (
    APPLY_PLY,
    EVALUATE_POSITION,
    LEGAL_PLIES,
)
from tests.engines.neural_network.small_networks import small_network

from .test_mechanics_regions import child, ongoing_position

SEARCH_ITERATIONS = 8
"""Enough iterations for the engine to expand and evaluate more than once,
few enough to keep the test fast."""


def timed_engine(iterations: int = SEARCH_ITERATIONS) -> TimedMCTSEngine:
    return TimedMCTSEngine(
        CtfNNEvaluator(small_network()), iterations=iterations, temperature=0.0
    )


def test_our_work_nests_under_the_search_call() -> None:
    engine = timed_engine()
    position = ongoing_position()

    with timing_session("test") as session:
        engine.select_ply(position)

    search = child(session.root, SEARCH)
    assert search.calls == 1
    # Evaluation and ply generation happened *inside* the search, not beside it.
    assert child(search, EVALUATE_POSITION).calls > 0
    assert child(search, LEGAL_PLIES).calls > 0
    assert child(search, APPLY_PLY).calls > 0
    assert EVALUATE_POSITION not in session.root.children


def test_remainder_is_the_engines_own_internals() -> None:
    """Selection, expansion and backpropagation live in the pinned dependency
    and cannot be instrumented; what the search call cost beyond our own
    recorded work is exactly that, and nothing else in the process can leak
    into it."""
    engine = timed_engine()

    with timing_session("test") as session:
        engine.select_ply(ongoing_position())

    search = child(session.root, SEARCH)
    children_total = sum(node.elapsed_ns for node in search.children.values())
    assert search.unattributed_ns == search.elapsed_ns - children_total
    assert search.unattributed_ns > 0


def test_work_outside_search_cannot_inflate_the_remainder() -> None:
    """The same operations run outside a search are recorded on their own branch,
    so they neither shrink nor pad what search is charged for."""
    engine = timed_engine()
    position = ongoing_position()

    with timing_session("test") as session:
        engine.select_ply(position)
        for _ in range(20):
            _ = position.legal_plies  # plenty of work, entirely outside search

    search = child(session.root, SEARCH)
    assert child(session.root, LEGAL_PLIES).calls == 20
    assert child(search, LEGAL_PLIES).calls < 20
    assert search.elapsed_ns == sum(
        node.elapsed_ns for node in search.children.values()
    ) + search.unattributed_ns


def test_self_play_search_records_under_its_own_name() -> None:
    """`select_ply_with_policy` is the self-play entry point and is reported
    separately from play-time search."""
    engine = timed_engine()

    with timing_session("test") as session:
        ply, policy = engine.select_ply_with_policy(ongoing_position())

    assert ply is not None and policy
    assert child(session.root, SEARCH_WITH_POLICY).calls == 1
    assert SEARCH not in session.root.children


def test_tree_maintenance_calls_are_recorded() -> None:
    engine = timed_engine()
    position = ongoing_position()

    with timing_session("test") as session:
        engine.reset()
        ply = engine.select_ply(position)
        engine.observe_ply(position, ply, position.apply_ply(ply))

    assert child(session.root, SEARCH_RESET).calls == 1
    assert "search-observe-ply" in session.root.children


def test_the_self_play_engine_factory_produces_a_timed_engine() -> None:
    engine = CtfEngineFactory(
        CtfNNEvaluator(small_network()), iterations=SEARCH_ITERATIONS
    )()

    with timing_session("test") as session:
        engine.select_ply_with_policy(ongoing_position())

    assert child(session.root, SEARCH_WITH_POLICY).calls == 1


def test_the_learned_player_seat_produces_a_timed_engine() -> None:
    player = build_neural_player(
        "Neural", network=small_network(), iterations=SEARCH_ITERATIONS
    )

    with timing_session("test") as session:
        player.select_ply(ongoing_position())

    assert child(session.root, SEARCH).calls == 1


def test_search_records_nothing_without_a_session() -> None:
    engine = timed_engine()
    position = ongoing_position()

    ply = engine.select_ply(position)

    assert ply in position.legal_plies

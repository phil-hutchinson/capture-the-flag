"""What the game-mechanics seams record, and how it nests.

Assertions are on region *names, counts, and shape* — never on durations, which
are real wall-clock here and therefore not reproducible. Counts are exact: a
known sequence of operations produces a known number of calls, which is also the
determinism property the story relies on for before/after comparisons.
"""

from types import MappingProxyType

from capture_the_flag.board import STANDARD_144, Square
from capture_the_flag.engines.neural_network.ctf_position_factory import (
    CtfPositionFactory,
)
from capture_the_flag.instrumentation.timing import RegionNode, region, timing_session
from capture_the_flag.outcome import INACTIVITY_LIMIT
from capture_the_flag.pieces import PieceType as P
from capture_the_flag.position import CtfPosition
from capture_the_flag.side import Side
from capture_the_flag.timing_regions import (
    APPLY_PLY,
    LEGAL_PLIES,
    OUTCOME,
    OUTCOME_REASON,
    STARTING_POSITION,
)
from tests.engines.neural_network.small_networks import BATTLE_SETUP

_WHITE_FLAG_SQUARE = Square(11, 1)  # L1
_BLACK_FLAG_SQUARE = Square(11, 12)  # L12


def ongoing_position() -> CtfPosition:
    """Both flags standing and both sides mobile — a position whose outcome
    check runs every rule in Section 5, including the no-legal-move test."""
    return CtfPosition(
        board=MappingProxyType(
            {
                _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
                _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
                Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
                Square(5, 8): (Side.BLACK, P.FOOT_SOLDIER),
            }
        ),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=STANDARD_144,
    )


def child(node: RegionNode, *path: str) -> RegionNode:
    current = node
    for name in path:
        assert name in current.children, (
            f"expected {name!r} under {current.name!r}, found {sorted(current.children)}"
        )
        current = current.children[name]
    return current


def test_each_mechanic_records_its_own_region() -> None:
    position = ongoing_position()
    with timing_session("test") as session:
        plies = position.legal_plies
        position.apply_ply(plies[0])
        assert position.outcome is None
        assert position.outcome_reason is None

    assert child(session.root, LEGAL_PLIES).calls == 1
    assert child(session.root, APPLY_PLY).calls == 1
    assert child(session.root, OUTCOME).calls == 1
    assert child(session.root, OUTCOME_REASON).calls == 1


def test_repeated_access_accumulates_calls() -> None:
    """Both properties recompute on every access, so the report counts accesses
    — which is exactly the duplication the story wants made visible."""
    position = ongoing_position()
    with timing_session("test") as session:
        for _ in range(5):
            _ = position.legal_plies

    assert child(session.root, LEGAL_PLIES).calls == 5


def test_legal_plies_computed_inside_outcome_nests_under_it() -> None:
    """Section 5.2's no-legal-move test regenerates the legal plies, so an
    outcome check silently pays for a second ply generation. The call-path rule
    puts that cost under `outcome`, distinct from a direct generation."""
    position = ongoing_position()
    with timing_session("test") as session:
        _ = position.outcome  # reaches 5.2, so generates plies internally
        _ = position.legal_plies  # a direct generation, from the caller

    outcome = child(session.root, OUTCOME)
    assert child(outcome, LEGAL_PLIES).calls == 1
    assert child(session.root, LEGAL_PLIES).calls == 1
    assert outcome.unattributed_ns == outcome.elapsed_ns - child(
        outcome, LEGAL_PLIES
    ).elapsed_ns


def test_a_short_circuiting_outcome_does_not_generate_plies() -> None:
    """The inactivity draw (5.3) is decided before the no-legal-move test, so a
    drawn position's outcome check has no `legal-plies` child at all."""
    drawn = CtfPosition(
        board=ongoing_position().board,
        side_to_move=Side.WHITE,
        inactivity_counter=INACTIVITY_LIMIT,
        layout=STANDARD_144,
    )
    with timing_session("test") as session:
        assert drawn.outcome == 0

    assert LEGAL_PLIES not in child(session.root, OUTCOME).children


def test_mechanics_nest_under_whatever_region_is_open() -> None:
    """The same mechanic reached by two paths is two nodes, so time can be
    attributed to the caller rather than pooled."""
    position = ongoing_position()
    with timing_session("test") as session:
        with region("first-caller"):
            _ = position.legal_plies
        with region("second-caller"):
            for _ in range(2):
                _ = position.legal_plies

    assert child(session.root, "first-caller", LEGAL_PLIES).calls == 1
    assert child(session.root, "second-caller", LEGAL_PLIES).calls == 2
    assert LEGAL_PLIES not in session.root.children


def test_starting_position_generation_is_timed() -> None:
    factory = CtfPositionFactory(setup=BATTLE_SETUP)
    with timing_session("test") as session:
        for _ in range(2):
            factory()

    assert child(session.root, STARTING_POSITION).calls == 2


def test_mechanics_record_nothing_without_a_session() -> None:
    position = ongoing_position()
    plies = position.legal_plies
    moved = position.apply_ply(plies[0])

    assert moved.outcome is None
    assert moved.side_to_move is Side.BLACK

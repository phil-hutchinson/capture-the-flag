"""What the game-mechanics seams record, and how it nests.

Assertions are on region *names, counts, and shape* — never on durations, which
are real wall-clock here and therefore not reproducible. Counts are exact: a
known sequence of operations produces a known number of calls, which is also the
determinism property the story relies on for before/after comparisons.
"""

from types import MappingProxyType

from capture_the_flag.board import Square
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
from tests.engines.neural_network.small_networks import PRE_RELEASE_SETUP

_WHITE_FLAG_SQUARE = Square(7, 1)  # H1
_BLACK_FLAG_SQUARE = Square(7, 8)  # H8
_LAYOUT = PRE_RELEASE_SETUP.layout


def ongoing_position() -> CtfPosition:
    """Both flags standing and both sides mobile — a position whose outcome
    check runs every rule in Section 5 and reaches the end without a
    terminal."""
    return CtfPosition(
        board=MappingProxyType(
            {
                _WHITE_FLAG_SQUARE: (Side.WHITE, P.FLAG),
                _BLACK_FLAG_SQUARE: (Side.BLACK, P.FLAG),
                Square(3, 2): (Side.WHITE, P.FOOT_SOLDIER),
                Square(4, 7): (Side.BLACK, P.FOOT_SOLDIER),
            }
        ),
        side_to_move=Side.WHITE,
        inactivity_counter=0,
        layout=_LAYOUT,
        ply_count=0,
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


def test_an_outcome_check_never_generates_plies() -> None:
    """Every Section 5 rule is decided from the board, the counter and the side
    to move, so an outcome check has no `legal-plies` child whichever way it
    goes — and a direct generation beside it still records at the root.

    This is a cost guard as much as a shape one: while the "no legal move"
    ending stood in as an assertion (peer review #5), reaching the end of
    `_evaluate` rebuilt the whole ply set, and the call-path rule billed that
    second generation to `outcome`. Nothing may quietly put it back.
    """
    ongoing = ongoing_position()
    drawn = CtfPosition(
        board=ongoing.board,
        side_to_move=Side.WHITE,
        inactivity_counter=INACTIVITY_LIMIT,
        layout=_LAYOUT,
        ply_count=0,
    )
    with timing_session("test") as session:
        assert ongoing.outcome is None  # runs every rule and reaches the end
        assert drawn.outcome == 0  # short-circuits at 5.4
        _ = ongoing.legal_plies  # a direct generation, from the caller

    outcome = child(session.root, OUTCOME)
    assert outcome.calls == 2
    assert LEGAL_PLIES not in outcome.children
    assert child(session.root, LEGAL_PLIES).calls == 1
    assert outcome.unattributed_ns == outcome.elapsed_ns


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
    factory = CtfPositionFactory(setup=PRE_RELEASE_SETUP)
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

"""Timing-core tests.

Every timing assertion runs against an injected clock that only moves when the
test says so, so the expected nanosecond figures are exact rather than
approximate — the real clock is never consulted here.
"""

import pytest

from capture_the_flag.instrumentation.timing import (
    RegionNode,
    TimingSession,
    active_session,
    region,
    timed,
    timing_session,
)


class FakeClock:
    """A monotonic nanosecond clock driven by the test."""

    def __init__(self) -> None:
        self.now_ns = 0

    def __call__(self) -> int:
        return self.now_ns

    def advance(self, nanoseconds: int) -> None:
        self.now_ns += nanoseconds


def child(node: RegionNode, *path: str) -> RegionNode:
    """The descendant of `node` at `path`, failing the test if it is missing."""
    current = node
    for name in path:
        assert name in current.children, (
            f"expected a {name!r} region under {current.name!r}, "
            f"found {sorted(current.children)}"
        )
        current = current.children[name]
    return current


def test_sibling_regions_accumulate_independently() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("first"):
            clock.advance(10)
        with region("second"):
            clock.advance(30)

    assert child(session.root, "first").elapsed_ns == 10
    assert child(session.root, "second").elapsed_ns == 30


def test_repeated_entries_accumulate_calls_and_time() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        for _ in range(3):
            with region("repeated"):
                clock.advance(7)

    repeated = child(session.root, "repeated")
    assert repeated.calls == 3
    assert repeated.elapsed_ns == 21


def test_child_time_is_inside_the_parent_and_outside_its_remainder() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("parent"):
            clock.advance(5)  # parent's own work
            with region("child"):
                clock.advance(20)
            clock.advance(5)  # more of the parent's own work

    parent = child(session.root, "parent")
    assert parent.elapsed_ns == 30
    assert child(parent, "child").elapsed_ns == 20
    assert parent.unattributed_ns == 10


def test_uninstrumented_time_inside_a_region_is_its_remainder() -> None:
    """The shared-search-engine case: a region whose children explain only part
    of it reports the rest as unattributed."""
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("search"):
            for _ in range(2):
                clock.advance(100)  # search internals we cannot instrument
                with region("evaluate"):
                    clock.advance(50)

    search = child(session.root, "search")
    assert search.elapsed_ns == 300
    assert child(search, "evaluate").elapsed_ns == 100
    assert search.unattributed_ns == 200


def test_same_name_under_two_parents_is_two_nodes() -> None:
    """The call-path rule: identically named work is attributed to the path that
    reached it, not merged into one bucket."""
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("search"):
            with region("legal-plies"):
                clock.advance(40)
        with region("game-loop"):
            with region("legal-plies"):
                clock.advance(3)

    assert child(session.root, "search", "legal-plies").elapsed_ns == 40
    assert child(session.root, "game-loop", "legal-plies").elapsed_ns == 3


def test_reentering_a_region_deepens_the_tree() -> None:
    """Recursion is not special-cased: the inner activation is a child of the
    outer one, so the outer's inclusive time still covers it exactly once."""
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("recursive"):
            clock.advance(1)
            with region("recursive"):
                clock.advance(9)

    outer = child(session.root, "recursive")
    assert outer.elapsed_ns == 10
    assert child(outer, "recursive").elapsed_ns == 9
    assert outer.unattributed_ns == 1


def test_root_is_all_inclusive() -> None:
    clock = FakeClock()
    with timing_session("whole-run", clock=clock) as session:
        clock.advance(15)  # time inside no named region at all
        with region("named"):
            clock.advance(35)

    assert session.root.name == "whole-run"
    assert session.root.calls == 1
    assert session.root.elapsed_ns == 50
    assert session.root.unattributed_ns == 15


def test_regions_close_when_an_exception_passes_through() -> None:
    clock = FakeClock()
    session = None
    with pytest.raises(ValueError, match="boom"):
        with timing_session("run", clock=clock) as opened:
            session = opened
            with region("failing"):
                clock.advance(4)
                raise ValueError("boom")

    assert session is not None
    assert child(session.root, "failing").elapsed_ns == 4
    assert session.is_finished
    assert active_session() is None


def test_timed_decorator_records_the_call() -> None:
    clock = FakeClock()

    @timed("decorated")
    def work(value: int) -> int:
        clock.advance(12)
        return value * 2

    with timing_session("run", clock=clock) as session:
        assert work(21) == 42

    decorated = child(session.root, "decorated")
    assert decorated.calls == 1
    assert decorated.elapsed_ns == 12


def test_regions_record_nothing_when_no_session_is_active() -> None:
    assert active_session() is None

    @timed("decorated")
    def work() -> str:
        with region("nested"):
            return "done"

    with region("outer"):
        assert work() == "done"

    assert active_session() is None


def test_session_is_deactivated_after_the_block() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        assert active_session() is session
    assert active_session() is None
    assert session.is_finished


def test_sessions_do_not_nest() -> None:
    with timing_session("outer", clock=FakeClock()):
        with pytest.raises(RuntimeError, match="already active"):
            with timing_session("inner", clock=FakeClock()):
                pass
    assert active_session() is None


def test_finishing_with_a_region_still_open_is_an_error() -> None:
    session = TimingSession("run", clock=FakeClock())
    session.enter("leaked")  # entered without its `with`, so never closed
    with pytest.raises(RuntimeError, match="still open: run -> leaked"):
        session.finish()


def test_snapshot_credits_the_regions_that_are_still_open() -> None:
    """A mid-run report's whole point: the root — open for the entire run — would
    otherwise read as zero, and every share computed against it with it."""
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("done"):
            clock.advance(5)
        with region("still-open"):
            clock.advance(30)
            snapshot = session.snapshot()

    assert snapshot.calls == 1  # the root, counted as the call it is part-way through
    assert snapshot.elapsed_ns == 35
    assert child(snapshot, "done").elapsed_ns == 5
    still_open = child(snapshot, "still-open")
    assert still_open.calls == 1
    assert still_open.elapsed_ns == 30


def test_snapshot_does_not_disturb_the_live_measurement() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("work"):
            clock.advance(10)
            session.snapshot()
            clock.advance(10)

    work = child(session.root, "work")
    assert work.calls == 1  # not the snapshot's in-flight extra
    assert work.elapsed_ns == 20
    assert session.root.elapsed_ns == 20


def test_snapshotting_a_finished_session_copies_the_tree_unchanged() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("work"):
            clock.advance(12)

    snapshot = session.snapshot()

    assert snapshot is not session.root
    assert (snapshot.calls, snapshot.elapsed_ns) == (1, 12)
    assert child(snapshot, "work").elapsed_ns == 12


def test_finish_is_idempotent() -> None:
    clock = FakeClock()
    session = TimingSession("run", clock=clock)
    clock.advance(6)
    assert session.finish().elapsed_ns == 6
    clock.advance(100)
    assert session.finish().elapsed_ns == 6

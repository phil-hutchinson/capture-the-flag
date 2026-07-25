"""Nested, cumulative wall-clock accounting for hot pipelines.

The question this answers is "over a whole run, how much time went into this
section of code, across all the times it ran" — not "how long did this one call
take." Regions accumulate an elapsed total and a call count; nothing per-call is
retained.

**Regions nest by call path, not by name.** Whichever regions are open when a
region is entered become its ancestors, so the same instrumented function
accumulates separately under each distinct path that reaches it: legal-ply
generation reached from inside a search is a different node from legal-ply
generation reached from the game loop. That is what makes the gap between a
parent's own elapsed time and the sum of its children a meaningful "unattributed"
figure — it can only contain work done *inside* that parent, never time spent
elsewhere in the process.

**One all-inclusive root.** A session opens a root region covering everything, so
no measured time is parentless and the root's own unattributed remainder catches
whatever the instrumentation missed.

Three properties keep this cheap enough to leave switched on:

- With no session active, `region()` returns a shared do-nothing object — no
  allocation, no clock reads, one module-global load and a comparison.
- With a session active, entering a region allocates nothing either: regions
  nest strictly, so the session itself serves as the context manager for every
  region and keeps the open ones on a stack.
- Time is read from a monotonic nanosecond counter and accumulated as integers;
  the conversion to seconds happens once, at report time.

A session is single-threaded — every instrumented call site in this project runs
on the main thread, and the stack discipline assumes it. Instrumenting work that
genuinely runs on several threads would need per-thread stacks; that is not what
this is for.
"""

import functools
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import ParamSpec, TypeVar

Clock = Callable[[], int]
"""A monotonic nanosecond clock. Injectable so tests can drive time exactly."""

DEFAULT_ROOT_NAME = "run"

_P = ParamSpec("_P")
_R = TypeVar("_R")


class RegionNode:
    """One node of the call-path tree: a region as reached by one particular
    chain of ancestors.

    `elapsed_ns` is *inclusive* — it covers everything that happened inside the
    region, children included. The unattributed remainder (inclusive minus the
    children's inclusive total) is derived at report time rather than stored, so
    accumulation stays a pair of integer additions.
    """

    __slots__ = ("name", "calls", "elapsed_ns", "children")

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0
        self.elapsed_ns = 0
        self.children: dict[str, RegionNode] = {}

    @property
    def children_elapsed_ns(self) -> int:
        return sum(child.elapsed_ns for child in self.children.values())

    @property
    def unattributed_ns(self) -> int:
        """Inclusive time this region did not spend inside an instrumented child.

        For a region wrapping a call into uninstrumented code (the shared search
        engine, say) this *is* the measurement: everything that call cost that we
        cannot name.
        """
        return self.elapsed_ns - self.children_elapsed_ns

    def __repr__(self) -> str:
        return (
            f"RegionNode(name={self.name!r}, calls={self.calls}, "
            f"elapsed_ns={self.elapsed_ns})"
        )


class _InactiveRegion:
    """The do-nothing region handed out when no session is active.

    A single shared instance, so an uninstrumented run pays for a global load, a
    comparison, and an empty `with` — and never touches the clock.
    """

    __slots__ = ()

    def __enter__(self) -> "_InactiveRegion":
        return self

    def __exit__(self, *_exception: object) -> bool:
        return False


_INACTIVE_REGION = _InactiveRegion()


class TimingSession:
    """An in-progress measurement: the root region, the stack of open regions,
    and the tree they accumulate into.

    The session doubles as the context manager for every region it hands out
    (`enter` pushes and returns the session; `__exit__` pops). Regions nest
    strictly, so one object can serve them all and per-region entry allocates
    nothing.
    """

    __slots__ = ("root", "_clock", "_open", "_started_ns")

    def __init__(
        self, name: str = DEFAULT_ROOT_NAME, clock: Clock = time.perf_counter_ns
    ) -> None:
        self._clock = clock
        self.root = RegionNode(name)
        # The root is open from construction: everything the session measures is
        # inside it by definition.
        self._open: list[RegionNode] = [self.root]
        self._started_ns: list[int] = [clock()]

    @property
    def is_finished(self) -> bool:
        return not self._open

    def enter(self, name: str) -> "TimingSession":
        """Open a region named `name` as a child of whichever region is
        currently open, and return the context manager that closes it."""
        parent = self._open[-1]
        node = parent.children.get(name)
        if node is None:
            node = RegionNode(name)
            parent.children[name] = node
        self._open.append(node)
        self._started_ns.append(self._clock())
        return self

    def __enter__(self) -> "TimingSession":
        return self

    def __exit__(self, *_exception: object) -> bool:
        # Read the clock first: everything after it is the measurement's own
        # overhead and belongs to nobody.
        ended_ns = self._clock()
        node = self._open.pop()
        node.elapsed_ns += ended_ns - self._started_ns.pop()
        node.calls += 1
        return False

    def snapshot(self) -> RegionNode:
        """A copy of the tree as it stands, reportable while the run continues.

        Regions accumulate on exit, so an open region holds nothing yet — the
        root above all, which would otherwise read as zero for the whole of a
        run. A snapshot credits every currently-open region the time it has been
        open for and counts it as one call, so a report taken part-way through
        reconciles exactly the way a finished one does.

        The live tree is not touched, so snapshotting is invisible to the
        measurement: a run that writes one after every checkpoint measures the
        same thing as one that writes only at the end.
        """
        now = self._clock()
        # Keyed by identity: a node cannot be its own descendant, so no node
        # appears twice on the open stack.
        in_flight = {
            id(node): now - started_ns
            for node, started_ns in zip(self._open, self._started_ns, strict=True)
        }
        return _copy_tree(self.root, in_flight)

    def finish(self) -> RegionNode:
        """Close the root region and return the completed tree.

        Every region opened inside a `with` has already closed by the time a
        session ends, so anything still open beyond the root means a region was
        entered without its context manager — a wiring bug worth failing on
        rather than silently reporting nonsense.
        """
        if self.is_finished:
            return self.root
        if len(self._open) > 1:
            still_open = " -> ".join(node.name for node in self._open)
            raise RuntimeError(
                f"timing session finished with regions still open: {still_open}"
            )
        self.__exit__()
        return self.root


def _copy_tree(node: RegionNode, in_flight: dict[int, int]) -> RegionNode:
    """`node` and its descendants copied, with any open region's elapsed time
    topped up by how long it has been open (see `TimingSession.snapshot`)."""
    copy = RegionNode(node.name)
    pending_ns = in_flight.get(id(node))
    copy.calls = node.calls + (1 if pending_ns is not None else 0)
    copy.elapsed_ns = node.elapsed_ns + (pending_ns or 0)
    copy.children = {
        name: _copy_tree(child, in_flight) for name, child in node.children.items()
    }
    return copy


_active_session: TimingSession | None = None


def active_session() -> TimingSession | None:
    """The session regions are currently recording into, if any."""
    return _active_session


def region(name: str) -> TimingSession | _InactiveRegion:
    """Time the enclosing `with` block as `name`, nested under whatever region
    is already open.

    The hot path of this module: called hundreds of thousands of times per game,
    so it stays a global load, a comparison, and (when active) a dict lookup and
    two list appends.
    """
    session = _active_session
    if session is None:
        return _INACTIVE_REGION
    return session.enter(name)


def timed(name: str) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    """Decorator form of `region`, for when the region is exactly one function."""

    def decorate(function: Callable[_P, _R]) -> Callable[_P, _R]:
        @functools.wraps(function)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
            with region(name):
                return function(*args, **kwargs)

        return wrapper

    return decorate


@contextmanager
def timing_session(
    name: str = DEFAULT_ROOT_NAME, clock: Clock = time.perf_counter_ns
) -> Generator[TimingSession]:
    """Activate a session for the duration of the block: open the all-inclusive
    root region, make `region()` record into it, and close it on the way out.

    Sessions do not nest — a run has one root by construction — so activating
    one while another is active is an error rather than a silently discarded
    measurement.
    """
    global _active_session
    if _active_session is not None:
        raise RuntimeError(
            f"a timing session ({_active_session.root.name!r}) is already active"
        )
    session = TimingSession(name, clock=clock)
    _active_session = session
    try:
        yield session
    finally:
        # Deactivate before closing, so a region entered during unwinding cannot
        # record into a session that is on its way out.
        _active_session = None
        session.finish()

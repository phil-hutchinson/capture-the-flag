"""Turning a finished timing tree into its two output forms.

A `RegionNode` tree holds raw integer nanoseconds; a report holds what a reader
actually wants — seconds, means, shares, and each region's unattributed
remainder — in a shape that serialises straight to JSON (`report_to_dict`) or
renders as an indented console tree (`format_report`).

Children are ordered by inclusive time descending at every level, so the
expensive path reads top-down: the first child of the first child of the root is
where the run went. A region whose children do not account for all of its time
gets an explicit `(unattributed)` row, sorted among them by size — for a region
wrapping a call into uninstrumented code, that row *is* the measurement.
"""

from dataclasses import dataclass, field

from .timing import RegionNode

UNATTRIBUTED_LABEL = "(unattributed)"

_NANOSECONDS_PER_SECOND = 1_000_000_000


@dataclass(frozen=True)
class RegionReport:
    """One region as reported: inclusive totals, derived shares, and children.

    `percent_of_root` is what makes two regions in different branches
    comparable; `percent_of_parent` is what says whether a child explains its
    parent. Both are carried because a reader needs both questions answered
    without doing arithmetic.
    """

    name: str
    calls: int
    seconds: float
    unattributed_seconds: float
    percent_of_root: float
    percent_of_parent: float
    children: tuple["RegionReport", ...] = field(default_factory=tuple)

    @property
    def mean_seconds(self) -> float:
        """Mean inclusive time per call, or 0.0 for a region that never ran."""
        return self.seconds / self.calls if self.calls else 0.0


def build_report(root: RegionNode) -> RegionReport:
    """Convert a finished timing tree into a report tree."""
    return _build(root, root_ns=root.elapsed_ns, parent_ns=root.elapsed_ns)


def report_to_dict(report: RegionReport) -> dict[str, object]:
    """The report as JSON-ready nested dictionaries.

    Seconds are rounded to microsecond precision: the underlying clock does not
    justify more, and full float repr would make the file needlessly unreadable.
    """
    return {
        "name": report.name,
        "calls": report.calls,
        "seconds": round(report.seconds, 6),
        "mean_seconds": round(report.mean_seconds, 9),
        "unattributed_seconds": round(report.unattributed_seconds, 6),
        "percent_of_root": round(report.percent_of_root, 2),
        "percent_of_parent": round(report.percent_of_parent, 2),
        "children": [report_to_dict(child) for child in report.children],
    }


def format_report(report: RegionReport, max_name_width: int = 44) -> str:
    """The report as an indented console tree, widest cost first."""
    header = (
        f"{'region':<{max_name_width}} {'calls':>10} {'total':>11} "
        f"{'mean':>11} {'%root':>7} {'%parent':>8}"
    )
    lines = [header, "-" * len(header)]
    _format_rows(report, depth=0, max_name_width=max_name_width, lines=lines)
    return "\n".join(lines)


def _build(node: RegionNode, *, root_ns: int, parent_ns: int) -> RegionReport:
    children = tuple(
        _build(child, root_ns=root_ns, parent_ns=node.elapsed_ns)
        for child in sorted(
            node.children.values(), key=lambda child: child.elapsed_ns, reverse=True
        )
    )
    return RegionReport(
        name=node.name,
        calls=node.calls,
        seconds=_seconds(node.elapsed_ns),
        unattributed_seconds=_seconds(node.unattributed_ns),
        percent_of_root=_percent(node.elapsed_ns, root_ns),
        percent_of_parent=_percent(node.elapsed_ns, parent_ns),
        children=children,
    )


def _format_rows(
    report: RegionReport, *, depth: int, max_name_width: int, lines: list[str]
) -> None:
    lines.append(
        _format_row(
            name=report.name,
            depth=depth,
            calls=f"{report.calls:,}",
            seconds=report.seconds,
            mean=_format_duration(report.mean_seconds),
            percent_of_root=report.percent_of_root,
            percent_of_parent=report.percent_of_parent,
            max_name_width=max_name_width,
        )
    )
    if not report.children:
        return

    # The unattributed remainder is presented as a sibling of the children it
    # sits alongside, in the same size ordering, so "what is this region's time
    # actually going into" reads off one sorted list.
    # A `None` row is the remainder, which has no report node of its own.
    rows: list[tuple[float, RegionReport | None]] = [
        (child.seconds, child) for child in report.children
    ]
    if report.unattributed_seconds > 0:
        rows.append((report.unattributed_seconds, None))
    rows.sort(key=lambda row: row[0], reverse=True)

    for seconds, child in rows:
        if child is not None:
            _format_rows(
                child, depth=depth + 1, max_name_width=max_name_width, lines=lines
            )
            continue
        of_root, of_parent = _unattributed_shares(seconds, report)
        lines.append(
            _format_row(
                name=UNATTRIBUTED_LABEL,
                depth=depth + 1,
                calls="-",
                seconds=seconds,
                mean="-",
                percent_of_root=of_root,
                percent_of_parent=of_parent,
                max_name_width=max_name_width,
            )
        )


def _format_row(
    *,
    name: str,
    depth: int,
    calls: str,
    seconds: float,
    mean: str,
    percent_of_root: float,
    percent_of_parent: float,
    max_name_width: int,
) -> str:
    label = "  " * depth + name
    if len(label) > max_name_width:
        label = label[: max_name_width - 1] + "…"
    return (
        f"{label:<{max_name_width}} {calls:>10} {_format_duration(seconds):>11} "
        f"{mean:>11} {percent_of_root:>6.1f}% {percent_of_parent:>7.1f}%"
    )


def _unattributed_shares(seconds: float, parent: RegionReport) -> tuple[float, float]:
    """The unattributed row's `(percent_of_root, percent_of_parent)`.

    A report tree does not carry absolute root seconds, but the parent's own
    root share encodes the ratio needed, so the remainder's root share is scaled
    from it.
    """
    if parent.seconds <= 0:
        return 0.0, 0.0
    share = seconds / parent.seconds
    return share * parent.percent_of_root, 100.0 * share


def _seconds(nanoseconds: int) -> float:
    return nanoseconds / _NANOSECONDS_PER_SECOND


def _percent(part_ns: int, whole_ns: int) -> float:
    return 100.0 * part_ns / whole_ns if whole_ns else 0.0


def _format_duration(seconds: float) -> str:
    """A duration in whichever unit keeps it readable — regions here span nine
    orders of magnitude, from a microsecond ply application to an hour-long run."""
    if seconds >= 1.0:
        return f"{seconds:.3f}s"
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.3f}ms"
    return f"{seconds * 1e6:.1f}us"

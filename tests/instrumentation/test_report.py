"""Report-rendering tests.

The tree under test is built through the real timing API against a fake clock,
so the reported seconds are exact and the assertions can be written as the
figures a reader would expect to see.
"""

import json

import pytest

from capture_the_flag.instrumentation.report import (
    UNATTRIBUTED_LABEL,
    RegionReport,
    build_report,
    format_report,
    report_to_dict,
)
from capture_the_flag.instrumentation.timing import RegionNode, region, timing_session

from .test_timing import FakeClock

_SECOND = 1_000_000_000


def sample_tree() -> RegionNode:
    """A run shaped like the real thing: a dominant search branch whose children
    explain only part of it, a cheap sibling branch, and time in the root that no
    region claims."""
    clock = FakeClock()
    with timing_session("whole-run", clock=clock) as session:
        clock.advance(1 * _SECOND)  # root's own unattributed time
        with region("self-play"):
            for _ in range(2):
                with region("search"):
                    clock.advance(1 * _SECOND)  # uninstrumented search internals
                    with region("evaluate"):
                        clock.advance(3 * _SECOND)
                    with region("legal-plies"):
                        clock.advance(1 * _SECOND)
        with region("train"):
            clock.advance(2 * _SECOND)
    return session.root


def find(report: RegionReport, *path: str) -> RegionReport:
    current = report
    for name in path:
        matches = [child for child in current.children if child.name == name]
        assert matches, f"no {name!r} under {current.name!r}"
        current = matches[0]
    return current


def test_report_carries_totals_calls_and_means() -> None:
    report = build_report(sample_tree())

    evaluate = find(report, "self-play", "search", "evaluate")
    assert evaluate.calls == 2
    assert evaluate.seconds == 6.0
    assert evaluate.mean_seconds == 3.0


def test_shares_are_relative_to_root_and_to_parent() -> None:
    report = build_report(sample_tree())

    assert report.percent_of_root == 100.0
    assert report.seconds == 13.0

    search = find(report, "self-play", "search")
    assert search.seconds == 10.0
    assert search.percent_of_root == pytest.approx(10.0 / 13.0 * 100.0)
    assert search.percent_of_parent == 100.0  # self-play is nothing but search


def test_remainder_is_the_uninstrumented_time_inside_a_region() -> None:
    report = build_report(sample_tree())

    search = find(report, "self-play", "search")
    assert search.unattributed_seconds == 2.0  # 10s total, 8s in children

    # The root's remainder is time the instrumentation never claimed at all.
    assert report.unattributed_seconds == 1.0


def test_children_are_ordered_by_cost() -> None:
    report = build_report(sample_tree())

    assert [child.name for child in report.children] == ["self-play", "train"]
    search = find(report, "self-play", "search")
    assert [child.name for child in search.children] == ["evaluate", "legal-plies"]


def test_dict_form_round_trips_through_json_and_keeps_the_nesting() -> None:
    report = build_report(sample_tree())

    restored = json.loads(json.dumps(report_to_dict(report)))

    assert restored["name"] == "whole-run"
    assert restored["seconds"] == 13.0
    self_play = restored["children"][0]
    assert self_play["name"] == "self-play"
    assert self_play["children"][0]["name"] == "search"
    assert self_play["children"][0]["unattributed_seconds"] == 2.0
    assert self_play["children"][0]["children"][0]["name"] == "evaluate"


def test_leaf_regions_report_no_remainder() -> None:
    """A childless region's remainder is its whole inclusive time, which explains
    nothing and would double-count almost the entire run if summed. The console
    form has never shown it; the dict form does not carry it either."""
    restored = json.loads(json.dumps(report_to_dict(build_report(sample_tree()))))

    search = restored["children"][0]["children"][0]
    assert search["name"] == "search"
    assert search["unattributed_seconds"] == 2.0
    evaluate = search["children"][0]
    assert evaluate["name"] == "evaluate" and not evaluate["children"]
    assert "unattributed_seconds" not in evaluate


def test_console_tree_indents_by_depth_and_shows_the_remainder() -> None:
    rendered = format_report(build_report(sample_tree()))
    lines = rendered.splitlines()
    named = {line.split()[0]: line for line in lines if line.strip()}

    assert lines[0].startswith("region")
    # Depth shows as indentation: root flush left, its children one level in.
    assert lines[2].startswith("whole-run")
    assert "  self-play" in rendered
    assert "      evaluate" in rendered

    # The unattributed row appears under search, sized and shared correctly.
    unattributed = [line for line in lines if UNATTRIBUTED_LABEL in line]
    assert len(unattributed) == 2  # one under search, one under the root
    assert "2.000s" in unattributed[0]

    assert "6.000s" in named["evaluate"]
    assert "3.000s" in named["evaluate"]  # its mean


def test_zero_duration_run_does_not_divide_by_zero() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("instant"):
            pass

    report = build_report(session.root)
    assert report.percent_of_root == 0.0
    assert find(report, "instant").mean_seconds == 0.0
    assert format_report(report)  # renders rather than raising


def test_long_region_names_are_truncated_to_the_column() -> None:
    clock = FakeClock()
    with timing_session("run", clock=clock) as session:
        with region("a-region-name-far-longer-than-the-column-allows"):
            clock.advance(_SECOND)

    lines = format_report(build_report(session.root), max_name_width=20).splitlines()
    assert all(line.split()[0] != "" for line in lines)
    assert any(line.startswith("  a-region-name-far…") for line in lines)

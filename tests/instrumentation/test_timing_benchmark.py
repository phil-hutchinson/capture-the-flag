"""The benchmark's reporting arithmetic.

The measurement itself is a manual, minutes-long command whose output is
recorded in the story folder; what is worth pinning down automatically is how it
turns two arms into a verdict — in particular that it says so when the machine
was too noisy for the answer to mean anything.
"""

import pytest

from capture_the_flag.timing_benchmark import ArmResult, format_comparison


def test_arm_summarises_its_repetitions() -> None:
    arm = ArmResult("timing on", [10.0, 11.0, 12.0])

    assert arm.mean == 11.0
    assert arm.fastest == 10.0
    assert arm.spread_percent == pytest.approx(20.0)  # 12.0 / 10.0 - 1


def test_overhead_is_reported_against_both_arms() -> None:
    untimed = ArmResult("timing off", [10.0, 10.0, 10.0])
    timed = ArmResult("timing on", [10.2, 10.2, 10.2])

    comparison = format_comparison(untimed, timed)

    assert "+2.0% by mean" in comparison
    assert "+2.0% by fastest run" in comparison


def test_a_noisy_machine_is_called_out() -> None:
    """An overhead figure smaller than the run-to-run spread is an upper bound,
    not a measurement — the report has to say so rather than let the number be
    quoted as precise."""
    untimed = ArmResult("timing off", [10.0, 10.0, 10.0])
    timed = ArmResult("timing on", [10.1, 12.0, 10.1])

    assert "upper bound" in format_comparison(untimed, timed)


def test_a_quiet_machine_is_not_called_out() -> None:
    untimed = ArmResult("timing off", [10.0, 10.01, 10.0])
    timed = ArmResult("timing on", [11.0, 11.01, 11.0])

    assert "upper bound" not in format_comparison(untimed, timed)

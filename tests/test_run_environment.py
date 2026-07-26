import torch

from capture_the_flag.device import ResolvedDevice, resolve_device
from capture_the_flag.run_environment import environment_facts


def _machine_facts(resolved: ResolvedDevice) -> dict[str, object]:
    machine = environment_facts(resolved)["machine"]
    assert isinstance(machine, dict)
    return machine


def test_facts_report_the_resolved_device_not_availability(monkeypatch) -> None:
    # Simulates the exact scenario the story calls out: a CPU-resolved run
    # inside a machine that could do CUDA. Constructible without a real GPU by
    # forcing `is_available` and resolving CPU explicitly (always honoured
    # regardless of availability).
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    resolved = resolve_device("cpu")

    machine = _machine_facts(resolved)

    assert machine["torch_device"] == "cpu"
    assert "cuda_device_name" not in machine


def test_facts_report_cuda_when_resolved_to_cuda(monkeypatch) -> None:
    # No real GPU needed: the fact-gathering trusts the resolved device it is
    # handed rather than querying torch itself, so a hand-built ResolvedDevice
    # is enough to prove it reports what it was given. `get_device_name` is
    # stubbed since it would otherwise reach for hardware that may not exist.
    monkeypatch.setattr(torch.cuda, "get_device_name", lambda _index: "stub-gpu")
    resolved = ResolvedDevice(device=torch.device("cuda"), tf32_allowed=False)

    machine = _machine_facts(resolved)

    assert machine["torch_device"] == "cuda"
    assert machine["cuda_device_name"] == "stub-gpu"


def test_facts_report_the_precision_setting() -> None:
    resolved = resolve_device("cpu")

    machine = _machine_facts(resolved)

    assert machine["torch_tf32_allowed"] == resolved.tf32_allowed

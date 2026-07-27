"""What a run ran against: versions, commit, and the machine's compute shape.

Timings are only comparable across runs that agree on these. A breakdown taken
today and one taken after an optimization say nothing to each other unless both
record which commit produced them, which torch was underneath, and how much
compute the machine gave them — thread counts in particular move self-play
wall-clock around by more than most optimizations will.

Everything here is best-effort: a missing git binary or an unreadable
`/proc/cpuinfo` yields `None` for that fact rather than failing a run that was
otherwise fine.
"""

import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from types import ModuleType

from .device import ResolvedDevice


def environment_facts(resolved_device: ResolvedDevice) -> dict[str, object]:
    """The full environment record written alongside a run's timings.

    `resolved_device` is what the run actually resolved to (see `device.py`),
    not what the machine merely has available — a CPU-forced run in the CUDA
    container must report `cpu`, not `cuda`.
    """
    return {
        "git_commit": git_commit(),
        "versions": {
            "python": platform.python_version(),
            "game_engine_core": distribution_version("game-engine-core"),
            "capture_the_flag": distribution_version("capture-the-flag"),
            "torch": _torch_version(),
        },
        "machine": _machine_facts(resolved_device),
    }


def distribution_version(name: str) -> str | None:
    """The installed version of a distribution, or None if it is not installed
    (e.g. running from a source tree that was never `pip install`-ed)."""
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def git_commit() -> str | None:
    """This repo's short commit hash, or None if git is unavailable or the source
    is not inside a working tree — the record is best-effort, never fatal.

    Asked of the package's own directory rather than the process's: a run
    launched from anywhere else (an output directory, a scratch folder) must
    still record which commit produced the code being measured.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _machine_facts(resolved_device: ResolvedDevice) -> dict[str, object]:
    """Compute-shape facts, in rough order of how much they move timings."""
    facts: dict[str, object] = {
        "platform": platform.platform(),
        "processor": _processor_name(),
        "cpu_count": os.cpu_count(),
    }
    facts.update(_torch_compute_facts(resolved_device))
    return facts


def _processor_name() -> str | None:
    """A human-readable CPU name.

    `platform.processor()` is empty on most Linux systems, so the model line
    from `/proc/cpuinfo` is preferred where it exists.
    """
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as cpuinfo:
            for line in cpuinfo:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def _torch_version() -> str | None:
    torch = _import_torch()
    return None if torch is None else str(torch.__version__)


def _torch_compute_facts(resolved_device: ResolvedDevice) -> dict[str, object]:
    """The device and thread budget torch will actually use.

    The device and precision come from `resolved_device` rather than an
    availability check: `torch.cuda.is_available()` says what the machine
    *could* do, not what this run resolved to, and the two differ exactly when
    a run forces CPU inside the CUDA container.

    Thread counts are recorded because they are the usual explanation for two
    runs of identical code disagreeing on wall clock — a container with a
    different CPU allocation changes them without anything else changing.
    """
    torch = _import_torch()
    if torch is None:
        return {}
    facts: dict[str, object] = {
        "torch_device": resolved_device.device.type,
        "torch_tf32_allowed": resolved_device.tf32_allowed,
        "torch_threads": torch.get_num_threads(),
        "torch_interop_threads": torch.get_num_interop_threads(),
    }
    if resolved_device.is_cuda:
        facts["cuda_device_name"] = torch.cuda.get_device_name(0)
    return facts


def _import_torch() -> ModuleType | None:
    """torch if it is importable, else None.

    This once deferred torch's import cost so a random-vs-random batch would not
    pay it merely to write down its environment. It no longer does: the module
    takes a resolved device, and `device.py` imports torch at module scope, so
    anything reaching these facts has already paid. The lookup stays because it
    keeps the best-effort discipline these facts are gathered under — a missing
    fact yields `None`, never a failed run — which is worth preserving even
    though torch is a hard dependency and the fallback is unreachable in
    practice.
    """
    return sys.modules.get("torch") or _import_torch_module()


def _import_torch_module() -> ModuleType | None:
    try:
        import torch
    except ImportError:  # pragma: no cover - torch is a hard dependency
        return None
    return torch

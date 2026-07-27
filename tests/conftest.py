"""Fixtures shared across the suite."""

import pytest
import torch


@pytest.fixture(autouse=True)
def restore_tf32_flags():
    """Put torch's precision flags back after every test.

    Resolving a device pins these process-globals, so any test that reaches
    `device.py` — directly, or through the run record's environment facts —
    mutates state the rest of the suite runs under. Restoring keeps that from
    making outcomes depend on collection order, and lets a test deliberately turn
    TF32 *on* to prove pinning works without leaving it on for whatever runs next.

    Autouse and suite-wide rather than per-module: the modules that touch the
    flags are not obviously the ones that read them, so opting in per file is a
    thing to forget.
    """
    matmul = torch.backends.cuda.matmul.allow_tf32
    cudnn = torch.backends.cudnn.allow_tf32
    yield
    torch.backends.cuda.matmul.allow_tf32 = matmul
    torch.backends.cudnn.allow_tf32 = cudnn

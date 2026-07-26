"""Skipping, not failing, when there is no GPU.

The default dev container installs CPU-only torch and passes no device through,
and it stays the default precisely so ordinary work does not pay for the CUDA
stack. The suite therefore has to be green there: a test that needs a GPU is
*inapplicable* without one, not broken. Collected here so every such test skips
for the same reason and one grep finds them all.
"""

import pytest
import torch

requires_cuda = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="needs a CUDA device; open the repository in .devcontainer/cuda to run it",
)
"""Mark a test that can only run on a GPU. Evaluated once at import, so the
reason is decided by the container the suite is running in."""

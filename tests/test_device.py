import pytest
import torch

from capture_the_flag.device import (
    DEVICE_AUTO,
    DEVICE_CHOICES,
    DEVICE_CPU,
    DEVICE_CUDA,
    DeviceUnavailableError,
    resolve_device,
)
from tests.gpu import requires_cuda


@pytest.fixture(autouse=True)
def restore_tf32_flags():
    """Resolution pins process-global precision flags, so put them back.

    Nothing else in the suite reads them, but a test that deliberately turns TF32
    *on* to prove pinning works must not leave it on for whatever runs next.
    """
    matmul = torch.backends.cuda.matmul.allow_tf32
    cudnn = torch.backends.cudnn.allow_tf32
    yield
    torch.backends.cuda.matmul.allow_tf32 = matmul
    torch.backends.cudnn.allow_tf32 = cudnn


def test_auto_resolves_to_cpu_when_cuda_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    resolved = resolve_device(DEVICE_AUTO)

    assert resolved.device == torch.device(DEVICE_CPU)
    assert not resolved.is_cuda


def test_auto_is_the_default_request(monkeypatch) -> None:
    # The entry points pass nothing when the developer says nothing, so the
    # no-argument call has to be the one that takes what the container offers.
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    assert resolve_device() == resolve_device(DEVICE_AUTO)


@requires_cuda
def test_auto_resolves_to_cuda_when_a_gpu_is_present() -> None:
    resolved = resolve_device(DEVICE_AUTO)

    assert resolved.device.type == DEVICE_CUDA
    assert resolved.is_cuda


@pytest.mark.parametrize("cuda_available", [False, True], ids=["no_gpu", "gpu"])
def test_explicit_cpu_is_honoured_whether_or_not_a_gpu_exists(
    monkeypatch, cuda_available: bool
) -> None:
    # Forcing CPU inside the CUDA container is how the two devices get compared
    # at all, and how a GPU-only failure gets bisected — so an available GPU must
    # not be able to override the request.
    monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda_available)

    resolved = resolve_device(DEVICE_CPU)

    assert resolved.device == torch.device(DEVICE_CPU)
    assert not resolved.is_cuda


def test_explicit_cuda_raises_a_named_error_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    # Named and catchable: a silent fall back to CPU would let a run that was
    # supposed to exercise the GPU report success having never touched one.
    with pytest.raises(DeviceUnavailableError) as failure:
        resolve_device(DEVICE_CUDA)

    # The message has to say what to do next, not just what went wrong.
    message = str(failure.value)
    assert ".devcontainer/cuda" in message
    assert f"--device {DEVICE_CPU}" in message


def test_unknown_request_is_a_value_error_naming_the_choices() -> None:
    with pytest.raises(ValueError) as failure:
        resolve_device("gpu")

    message = str(failure.value)
    assert "gpu" in message
    for choice in DEVICE_CHOICES:
        assert choice in message


def test_every_offered_choice_is_accepted() -> None:
    # DEVICE_CHOICES is what the entry points offer as their `--device` values,
    # so a choice this module would reject as unknown is a wiring bug, not a
    # user error. An unavailable CUDA is a different failure and is allowed here.
    for choice in DEVICE_CHOICES:
        try:
            resolve_device(choice)
        except DeviceUnavailableError:
            pass


def test_resolution_pins_tf32_off_and_reports_it() -> None:
    # Start from the wrong state on purpose: cuDNN convolution defaults to TF32
    # on recent architectures, and the trunk is all convolutions.
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    resolved = resolve_device(DEVICE_CPU)

    assert not torch.backends.cuda.matmul.allow_tf32
    assert not torch.backends.cudnn.allow_tf32
    # Read back from torch rather than asserted from what we set, so this is a
    # fact about the process the run record can quote.
    assert resolved.tf32_allowed is False


def test_pinning_leaves_both_tf32_apis_readable() -> None:
    # The legacy `allow_tf32` flags and the newer `fp32_precision` attributes
    # cannot be mixed: pin through the new API and reading the legacy cuDNN flag
    # raises instead of answering. That getter is therefore the canary — it is
    # the one that would blow up in code that never set anything.
    resolve_device(DEVICE_CPU)

    assert torch.backends.cudnn.allow_tf32 is False
    assert torch.backends.cuda.matmul.allow_tf32 is False
    # And the new API agrees with the legacy one rather than contradicting it.
    assert torch.backends.cuda.matmul.fp32_precision != "tf32"

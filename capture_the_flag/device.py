"""The one place that answers "what device is this run using, at what precision".

Two decisions are made together here because they are the same decision: a run
that has chosen a device has also, implicitly, chosen how that device rounds. On
CUDA those are separate knobs with separate defaults, and leaving the second one
inherited would make the first one's numerical meaning depend on which GPU the
container happened to open on.

**Device.** `auto` takes whatever the container provides — CPU where torch cannot
see a GPU, CUDA where it can — so the configuration a developer opened is the
device they get without restating it anywhere. An explicit `cuda` that cannot be
honoured is a `DeviceUnavailableError`, never a quiet downgrade: a run launched
to exercise the GPU must not report success having spent an hour on the CPU.

**Precision.** torch's reduced-precision (TF32) defaults are both architecture-
and version-dependent, and on this project's hardware they are *not* uniform: a
fresh import leaves matmul at full fp32 but cuDNN convolution at TF32, which
truncates inputs to a 10-bit mantissa. The trunk is all convolutions, so that is
the path that matters — measured on an RTX 3060, it moves a single convolution's
disagreement with the CPU from ~1e-6 to ~8e-4. Both paths are therefore pinned to
fp32 here, so the two containers compute alike and the cross-device tolerance the
suite claims is a property of the code rather than of the card.

Pinning uses the legacy `allow_tf32` flags rather than the newer
`fp32_precision` attributes, and that is load-bearing rather than nostalgic: the
two APIs cannot be mixed. Setting `torch.backends.fp32_precision = "ieee"` makes
a subsequent read of `torch.backends.cudnn.allow_tf32` raise, because the legacy
getter cannot express the value the new API stored. Anything reading the legacy
flag — our own record, a test, a library — would then fail on a flag it never
set. Setting the legacy flags leaves every getter in *both* APIs readable and
agreeing, so this module writes the one that keeps the other honest.

The resolved facts are returned rather than stashed in a global: the run record
consumes them (see `run_environment`), and the pipeline is handed the device
explicitly rather than reaching for an ambient one.
"""

from dataclasses import dataclass

import torch

DEVICE_AUTO = "auto"
DEVICE_CPU = "cpu"
DEVICE_CUDA = "cuda"

DEVICE_CHOICES = (DEVICE_AUTO, DEVICE_CPU, DEVICE_CUDA)
"""Every accepted device request, in the order the entry points offer them.

`auto` first because it is the default and the one that needs no explanation;
the two explicit choices exist to force a device for comparison and bisection.
Non-CUDA accelerators are deliberately absent — a single CUDA device is the whole
target, and an accelerator we cannot test is worse than one we do not offer.
"""


class DeviceUnavailableError(RuntimeError):
    """A device was explicitly requested and cannot be provided.

    Named and distinct from the `ValueError` an unrecognized request raises: this
    one means "you asked for something real that this machine does not have,"
    which is a environment problem, not a typo.
    """


@dataclass(frozen=True)
class ResolvedDevice:
    """What a run resolved to, and how it will round — the answer every other
    module asks for rather than deciding for itself."""

    device: torch.device
    """The concrete device every tensor in the run belongs on."""

    tf32_allowed: bool
    """Whether reduced-precision TF32 paths are enabled, *read back from torch*
    after pinning rather than asserted from what we set. A recorded fact is only
    worth recording if it describes the process that ran."""

    @property
    def is_cuda(self) -> bool:
        return self.device.type == DEVICE_CUDA


def resolve_device(request: str = DEVICE_AUTO) -> ResolvedDevice:
    """Turn a device request into the device a run will use, pinning precision.

    `request` is one of `DEVICE_CHOICES`. `auto` resolves to CUDA when it is
    available and CPU otherwise; `cpu` is always honoured; `cuda` raises
    `DeviceUnavailableError` when no GPU is reachable. An unrecognized request is
    a `ValueError`.

    Precision is pinned on every call, on both devices. The flags are inert on
    CPU, but recording "TF32 off" is a claim about the process, and a run that
    never set them could not honestly make it.
    """
    device = _resolve_request(request)
    tf32_allowed = _pin_fp32_precision()
    return ResolvedDevice(device=device, tf32_allowed=tf32_allowed)


def pipeline_device() -> ResolvedDevice:
    """The device this repository's pipeline actually runs on: the CPU, always.

    `resolve_device` answers what a run *could* use; this answers what the code as
    written *does* use. Nothing here places a network or a tensor on a GPU — that
    waits on device support in the shared engine — so a run started in the CUDA
    container still computes on the CPU, and its record has to say so. Reporting
    the `auto` resolution instead would recreate, pointed the other way, exactly
    the misreporting this module was written to end: a record naming a GPU that
    ran nothing.

    Every run record resolves its device through here, so the stories that make
    the pipeline device-aware have one call to replace with the run's real choice
    rather than four scattered assumptions to find.
    """
    return resolve_device(DEVICE_CPU)


def _resolve_request(request: str) -> torch.device:
    if request == DEVICE_AUTO:
        return torch.device(DEVICE_CUDA if torch.cuda.is_available() else DEVICE_CPU)
    if request == DEVICE_CPU:
        return torch.device(DEVICE_CPU)
    if request == DEVICE_CUDA:
        if not torch.cuda.is_available():
            raise DeviceUnavailableError(
                "CUDA was requested explicitly but torch cannot reach a GPU "
                f"(installed torch: {torch.__version__}). The default dev "
                "container installs CPU-only wheels and passes no device "
                "through; reopen the repository in the CUDA configuration "
                "(.devcontainer/cuda) to run on a GPU, or pass "
                f"--device {DEVICE_CPU} to run here deliberately."
            )
        return torch.device(DEVICE_CUDA)
    raise ValueError(
        f"unknown device request {request!r}; expected one of "
        f"{', '.join(DEVICE_CHOICES)}"
    )


def _pin_fp32_precision() -> bool:
    """Disable TF32 on the matmul and convolution paths, and report what torch
    says afterwards.

    Both flags are set even though only cuDNN's defaults to on today: the point
    is that neither is inherited. The return value is read back rather than
    assumed, so a torch version that stops honouring one of these is visible in
    the run record instead of silently contradicting it.
    """
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    return bool(torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32)

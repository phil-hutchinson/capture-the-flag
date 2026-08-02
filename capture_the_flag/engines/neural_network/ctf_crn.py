from typing import Self

import torch
import torch.nn as nn

from ...instrumentation.timing import timed
from ...timing_regions import NETWORK_FORWARD, NETWORK_MODE_SWITCH
from .tensor_layout import TensorLayout

DEFAULT_FEATURE_COUNT: int = 64
"""Trunk width: how many features the stem projects the input planes into, and
the channel count every residual block preserves. The working default the engine
is trained at — deliberately wider than the 34 input planes, so the trunk is not
a bottleneck on its own input."""

DEFAULT_RESIDUAL_BLOCK_COUNT: int = 10
"""Trunk depth. Each block is two 3x3 convolutions, so depth also sets how far
information can travel across the board before the heads see it."""

MAX_FEATURE_COUNT: int = 256
MAX_RESIDUAL_BLOCK_COUNT: int = 24
"""Sanity bounds on the architecture, not a claim about what is best — choosing
the right width and depth is a strength question, answerable only once strength
can be measured. They exist to turn a mistyped flag or a corrupt checkpoint stamp
into an immediate, named error rather than a run that quietly trains a trunkless
network or exhausts memory several minutes in. A residual block at 256 features
is already ~1.2M parameters, so 24 of them is far past anything this board size
plausibly needs; raise the ceilings if a real experiment ever wants more."""


def _check_architecture_bound(name: str, value: int, maximum: int) -> None:
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be between 1 and {maximum}, got {value}")


class CtfCrn(nn.Module):
    """The learned play engine's convolutional residual network.

    `tensor_layout` is the I/O contract the network is built to: the stem's input
    width, the policy head's channel count, and the value head's flattened extent
    all follow from it, so a network built for one board cannot be fed another's
    positions. It is held on the instance because it is also what a checkpoint of
    these weights is stamped with — the network knows which contract produced it.

    Width and depth are constructor parameters rather than fixed constants: the
    defaults are the working training scale, but callers that only need *a*
    network (tests, quick experiments) can build a cheap one, and checkpoints
    record the sizes they were trained at so they rebuild at their own scale
    rather than at whatever the current defaults happen to be. Both are bounded
    (see `MAX_FEATURE_COUNT` / `MAX_RESIDUAL_BLOCK_COUNT`), so a value that could
    only be a mistake fails here rather than downstream.
    """

    def __init__(
        self,
        tensor_layout: TensorLayout,
        *,
        feature_count: int = DEFAULT_FEATURE_COUNT,
        residual_block_count: int = DEFAULT_RESIDUAL_BLOCK_COUNT,
    ):
        super().__init__()
        _check_architecture_bound("feature_count", feature_count, MAX_FEATURE_COUNT)
        _check_architecture_bound(
            "residual_block_count", residual_block_count, MAX_RESIDUAL_BLOCK_COUNT
        )
        self._tensor_layout = tensor_layout
        self._feature_count = feature_count
        self._residual_block_count = residual_block_count

        input_planes, input_rows, input_columns = tensor_layout.input_shape

        self._stem = nn.Sequential(
            nn.Conv2d(input_planes, feature_count, kernel_size = 3, padding = 1, bias = False),
            nn.BatchNorm2d(feature_count),
            nn.ReLU(),
        )

        self._residual_blocks = nn.ModuleList()
        self._residual_block_relu = nn.ReLU()
        for _ in range(residual_block_count):
            block = nn.Sequential(
                nn.Conv2d(feature_count, feature_count, kernel_size = 3, padding = 1, bias = False),
                nn.BatchNorm2d(feature_count),
                nn.ReLU(),
                nn.Conv2d(feature_count, feature_count, kernel_size = 3, padding = 1, bias = False),
                nn.BatchNorm2d(feature_count),
            )
            self._residual_blocks.append(block)

        self._policy_head = nn.Sequential(
            nn.Conv2d(feature_count, feature_count, kernel_size = 3, padding = 1, bias = False),
            nn.BatchNorm2d(feature_count),
            nn.ReLU(),
            nn.Conv2d(feature_count, tensor_layout.action_space_shape[0], kernel_size = 3, padding = 1), # Bias set to True here since there's no batchnorm after
        )

        self._value_head = nn.Sequential(
            nn.Conv2d(feature_count, 1, kernel_size = 1, bias = False),
            nn.BatchNorm2d(1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(input_rows * input_columns, feature_count),
            nn.ReLU(),
            nn.Linear(feature_count, 1),
            nn.Tanh(),
        )

    @property
    def tensor_layout(self) -> TensorLayout:
        """The I/O contract this instance was built to (what a checkpoint stamps
        its engine spec from)."""
        return self._tensor_layout

    @property
    def feature_count(self) -> int:
        """The trunk width this instance was built at (what a checkpoint stamps)."""
        return self._feature_count

    @property
    def residual_block_count(self) -> int:
        """The trunk depth this instance was built at (what a checkpoint stamps)."""
        return self._residual_block_count

    # One region covers the whole trunk-and-heads pass. It is entered from both
    # sides of the pipeline — search evaluates one position at a time, training
    # pushes whole minibatches through — and the call-path nesting keeps those
    # two on separate branches of the report without needing separate names.
    # Timed for what it costs rather than for what it looks like. Torch
    # implements a mode switch as a recursive walk over every submodule, so at
    # this trunk's depth one costs several hundred microseconds — and the shared
    # evaluator performs one per single-position evaluation, over a million times
    # in a training run. `eval()` routes through here too, being `train(False)`.
    #
    # The region belongs to the network because the walk is the network's own
    # work; the call-path rule then files it under whichever caller triggered it,
    # so search evaluations and the training loop's own mode switches stay on
    # separate branches of the report without a second name.
    @timed(NETWORK_MODE_SWITCH)
    def train(self, mode: bool = True) -> Self:
        return super().train(mode)

    @timed(NETWORK_FORWARD)
    def forward(self, x) -> tuple[torch.Tensor, torch.Tensor]:
        trunk = self._stem(x)

        for block in self._residual_blocks:
            residual = trunk
            relu = self._residual_block_relu
            trunk = block(trunk)
            trunk = trunk + residual
            trunk = relu(trunk)

        value = self._value_head(trunk)
        policy_logits = self._policy_head(trunk)

        return value, policy_logits

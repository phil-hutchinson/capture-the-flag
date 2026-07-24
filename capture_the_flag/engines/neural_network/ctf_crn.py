import torch
import torch.nn as nn

from .tensor_layout import ACTION_SPACE_SHAPE, INPUT_SHAPE, TOTAL_FP_COUNT

DEFAULT_FEATURE_COUNT: int = 64
"""Trunk width: how many features the stem projects the input planes into, and
the channel count every residual block preserves. The working default the engine
is trained at — deliberately wider than the 34 input planes, so the trunk is not
a bottleneck on its own input."""

DEFAULT_RESIDUAL_BLOCK_COUNT: int = 10
"""Trunk depth. Each block is two 3x3 convolutions, so depth also sets how far
information can travel across the board before the heads see it."""


class CtfCrn(nn.Module):
    """The learned play engine's convolutional residual network.

    Width and depth are constructor parameters rather than fixed constants: the
    defaults are the working training scale, but callers that only need *a*
    network (tests, quick experiments) can build a cheap one, and checkpoints
    record the sizes they were trained at so they rebuild at their own scale
    rather than at whatever the current defaults happen to be.
    """

    def __init__(
        self,
        *,
        feature_count: int = DEFAULT_FEATURE_COUNT,
        residual_block_count: int = DEFAULT_RESIDUAL_BLOCK_COUNT,
    ):
        super().__init__()
        self._feature_count = feature_count
        self._residual_block_count = residual_block_count

        self._stem = nn.Sequential(
            nn.Conv2d(TOTAL_FP_COUNT, feature_count, kernel_size = 3, padding = 1, bias = False),
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
            nn.Conv2d(feature_count, ACTION_SPACE_SHAPE[0], kernel_size = 3, padding = 1), # Bias set to True here since there's no batchnorm after
        )

        self._value_head = nn.Sequential(
            nn.Conv2d(feature_count, 1, kernel_size = 1, bias = False),
            nn.BatchNorm2d(1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(INPUT_SHAPE[1] * INPUT_SHAPE[2], feature_count),
            nn.ReLU(),
            nn.Linear(feature_count, 1),
            nn.Tanh(),
        )

    @property
    def feature_count(self) -> int:
        """The trunk width this instance was built at (what a checkpoint stamps)."""
        return self._feature_count

    @property
    def residual_block_count(self) -> int:
        """The trunk depth this instance was built at (what a checkpoint stamps)."""
        return self._residual_block_count

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

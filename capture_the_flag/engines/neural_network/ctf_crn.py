import torch
import torch.nn as nn

from .tensor_layout import ACTION_SPACE_SHAPE, INPUT_SHAPE, TOTAL_FP_COUNT


class CtfCrn(nn.Module):
    _FEATURE_COUNT: int = 32
    _RESIDUAL_BLOCK_COUNT: int = 6

    def __init__(self):
        super().__init__()
        self._stem = nn.Sequential(
            nn.Conv2d(TOTAL_FP_COUNT, CtfCrn._FEATURE_COUNT, kernel_size = 3, padding = 1, bias = False),
            nn.BatchNorm2d(CtfCrn._FEATURE_COUNT),
            nn.ReLU(),
        )
        
        self._residual_blocks = nn.ModuleList()
        self._residual_block_relu = nn.ReLU()
        for _ in range(CtfCrn._RESIDUAL_BLOCK_COUNT):
            block = nn.Sequential(
                nn.Conv2d(CtfCrn._FEATURE_COUNT, CtfCrn._FEATURE_COUNT, kernel_size = 3, padding = 1, bias = False),
                nn.BatchNorm2d(CtfCrn._FEATURE_COUNT),
                nn.ReLU(),
                nn.Conv2d(CtfCrn._FEATURE_COUNT, CtfCrn._FEATURE_COUNT, kernel_size = 3, padding = 1, bias = False),
                nn.BatchNorm2d(CtfCrn._FEATURE_COUNT),
            )
            self._residual_blocks.append(block)

        self._policy_head = nn.Sequential(
            nn.Conv2d(CtfCrn._FEATURE_COUNT, CtfCrn._FEATURE_COUNT, kernel_size = 3, padding = 1, bias = False),
            nn.BatchNorm2d(CtfCrn._FEATURE_COUNT),
            nn.ReLU(),
            nn.Conv2d(CtfCrn._FEATURE_COUNT, ACTION_SPACE_SHAPE[0], kernel_size = 3, padding = 1), # Bias set to True here since there's no batchnorm after
        )

        self._value_head = nn.Sequential(
            nn.Conv2d(CtfCrn._FEATURE_COUNT, 1, kernel_size = 1, bias = False),
            nn.BatchNorm2d(1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(INPUT_SHAPE[1] * INPUT_SHAPE[2], CtfCrn._FEATURE_COUNT),
            nn.ReLU(),
            nn.Linear(CtfCrn._FEATURE_COUNT, 1),
            nn.Tanh(),
        )

    def forward(self, x) -> tuple[torch.Tensor, torch.Tensor]:
        trunk = self._stem(x)

        for block_number in range(CtfCrn._RESIDUAL_BLOCK_COUNT):
            residual = trunk
            block = self._residual_blocks[block_number]
            relu = self._residual_block_relu
            trunk = block(trunk)
            trunk = trunk + residual
            trunk = relu(trunk)

        value = self._value_head(trunk)
        policy_logits = self._policy_head(trunk)
        
        return value, policy_logits

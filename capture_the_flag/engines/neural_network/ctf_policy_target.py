from collections.abc import Mapping, Sequence

import torch
import torch.nn.functional as F
from game_engine_learning.training_loop import PolicyLossFn
from torch import Tensor

from ...instrumentation.timing import timed
from ...ply import parse_ply
from ...position import CtfPosition
from ...timing_regions import POLICY_LOSS, POLICY_TRANSFORM
from .ctf_nn_evaluator import policy_logit_location_for_ply, rotate_ply
from .tensor_layout import TensorLayout


@timed(POLICY_TRANSFORM)
def transform_policy_to_white_perspective(position: CtfPosition, policy: dict[str, float]) -> dict[str, float]:
    if position.active_player_id == 1:
        return policy

    rotated_policy: dict[str, float] = {}

    for ply_str, value in policy.items():
        ply = parse_ply(ply_str)
        rotated_ply_str = str(rotate_ply(ply, position.layout))
        rotated_policy[rotated_ply_str] = value

    return rotated_policy


def ctf_policy_loss_for(tensor_layout: TensorLayout) -> PolicyLossFn:
    """The policy loss for one tensor contract.

    A factory rather than a plain function because the library's `PolicyLossFn`
    is `(policy_logits, target_policies) -> loss` and nothing else: the targets
    arrive as `str(ply)` keys with no position attached, so the board they are to
    be laid out against cannot come from the arguments and has to be bound here.
    """
    action_space_shape = tensor_layout.action_space_shape
    layout = tensor_layout.layout

    @timed(POLICY_LOSS)
    def ctf_policy_loss(
        policy_logits: Tensor, target_policies: Sequence[Mapping[str, float]]
    ) -> Tensor:
        """Cross-entropy between the MCTS visit distributions and the policy head.

            This method looks at the board in universal position (i.e. from white's perspective), so this requires that
            PolicyTransform be implemented and passed into SelfPlayCollector
        """
        targets = torch.zeros((len(target_policies), *action_space_shape), dtype=torch.float32)
        for row, policy in enumerate(target_policies):
            for ply_str, prob in policy.items():
                ply = parse_ply(ply_str)
                d1, d2, d3 = policy_logit_location_for_ply(ply, 1, layout) #always go from White's perspecive as this has been normalized
                targets[row, d1, d2, d3] = prob

        policy_logits = policy_logits.flatten(1)
        targets = targets.flatten(1)
        log_probs = F.log_softmax(policy_logits, dim=-1)
        return -(targets * log_probs).sum(dim=-1).mean()

    return ctf_policy_loss

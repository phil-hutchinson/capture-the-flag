"""Tensor contracts and a deliberately tiny `CtfCrn` for the network tests.

`CtfCrn`'s defaults are the scale the engine is actually trained at, which is far
more forward-pass cost than a wiring or shape test needs — and several of these
tests run a whole self-play game through the network. Tests that assert something
about the *pipeline* rather than about the architecture build one of these
instead, so the default suite stays fast; the tests that genuinely care about the
default architecture construct it explicitly.

The two published tensor contracts live here too. Nothing in the package holds a
tensor layout as a constant any more — a run derives one from its configuration —
but a test naming a fixture board still has to say which, so the resolutions are
done once here rather than in every module that needs one.
"""

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.tensor_layout import TensorLayout
from capture_the_flag.game_setup import BATTLE_SETUP, setup_for_ruleset

__all__ = [
    "BATTLE_SETUP",
    "BATTLE_TENSOR_LAYOUT",
    "SKIRMISH_SETUP",
    "SKIRMISH_TENSOR_LAYOUT",
    "SMALL_FEATURE_COUNT",
    "SMALL_RESIDUAL_BLOCK_COUNT",
    "small_network",
]

SKIRMISH_SETUP = setup_for_ruleset("SKIRMISH")

BATTLE_TENSOR_LAYOUT = TensorLayout.for_setup(BATTLE_SETUP)
SKIRMISH_TENSOR_LAYOUT = TensorLayout.for_setup(SKIRMISH_SETUP)

SMALL_FEATURE_COUNT = 8
SMALL_RESIDUAL_BLOCK_COUNT = 2


def small_network(tensor_layout: TensorLayout = BATTLE_TENSOR_LAYOUT) -> CtfCrn:
    """A `CtfCrn` small enough to be cheap, large enough to be a real network
    (a trunk narrower than the input planes, and more than one residual block)."""
    return CtfCrn(
        tensor_layout,
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
    )

"""A deliberately tiny `CtfCrn` for tests that only need *a* network.

`CtfCrn`'s defaults are the scale the engine is actually trained at, which is far
more forward-pass cost than a wiring or shape test needs — and several of these
tests run a whole self-play game through the network. Tests that assert something
about the *pipeline* rather than about the architecture build one of these
instead, so the default suite stays fast; the tests that genuinely care about the
default architecture construct it explicitly.
"""

from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn

SMALL_FEATURE_COUNT = 8
SMALL_RESIDUAL_BLOCK_COUNT = 2


def small_network() -> CtfCrn:
    """A `CtfCrn` small enough to be cheap, large enough to be a real network
    (a trunk narrower than the input planes, and more than one residual block)."""
    return CtfCrn(
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
    )

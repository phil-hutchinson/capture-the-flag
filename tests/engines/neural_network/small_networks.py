"""A tensor contract and a deliberately tiny `CtfCrn` for the network tests.

`CtfCrn`'s defaults are the scale the engine is actually trained at, which is far
more forward-pass cost than a wiring or shape test needs — and several of these
tests run a whole self-play game through the network. Tests that assert something
about the *pipeline* rather than about the architecture build one of these
instead, so the default suite stays fast; the tests that genuinely care about the
default architecture construct it explicitly.

The one published tensor contract lives here too, at the size these tests
exercise. Nothing in the package holds a tensor layout as a constant any more —
a run derives one from its configuration — but a test naming a fixture board
still has to say which, so the resolution is done once here rather than in
every module that needs one.

`OTHER_SETUP`/`OTHER_TENSOR_LAYOUT` is a second, differently-shaped setup for
tests that need to show the network's I/O shape follows its configured board
rather than being a constant — major 2 used Skirmish for this; major 3 has only
one published board and army (`doc/ruleset/CLAUDE.md`), so this is a hand-built
setup naming no published edition, purely to give those tests a second shape.
"""

from capture_the_flag.board import BoardLayout
from capture_the_flag.engines.neural_network.ctf_crn import CtfCrn
from capture_the_flag.engines.neural_network.tensor_layout import TensorLayout
from capture_the_flag.game_setup import PRE_RELEASE_SETUP, GameSetup
from capture_the_flag.pieces import ArmyComposition, PieceType

__all__ = [
    "OTHER_SETUP",
    "OTHER_TENSOR_LAYOUT",
    "PRE_RELEASE_SETUP",
    "PRE_RELEASE_TENSOR_LAYOUT",
    "SMALL_FEATURE_COUNT",
    "SMALL_RESIDUAL_BLOCK_COUNT",
    "small_network",
]

PRE_RELEASE_TENSOR_LAYOUT = TensorLayout.for_setup(PRE_RELEASE_SETUP)

OTHER_SETUP = GameSetup(
    layout=BoardLayout(
        layout_id="test_only_small",
        columns=4,
        rows=6,
        home_rows=1,
    ),
    composition=ArmyComposition(
        composition_id="test_only_small_army",
        counts={PieceType.PEASANT: 3, PieceType.FLAG: 1},
    ),
)
OTHER_TENSOR_LAYOUT = TensorLayout.for_setup(OTHER_SETUP)

SMALL_FEATURE_COUNT = 8
SMALL_RESIDUAL_BLOCK_COUNT = 2


def small_network(tensor_layout: TensorLayout = PRE_RELEASE_TENSOR_LAYOUT) -> CtfCrn:
    """A `CtfCrn` small enough to be cheap, large enough to be a real network
    (a trunk narrower than the input planes, and more than one residual block)."""
    return CtfCrn(
        tensor_layout,
        feature_count=SMALL_FEATURE_COUNT,
        residual_block_count=SMALL_RESIDUAL_BLOCK_COUNT,
    )

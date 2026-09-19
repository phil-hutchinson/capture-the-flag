"""The tensor contract between a game and the learned play engine.

`TensorLayout` is that contract as a **value**: the input and action-space shapes
a network is built at, and the engine-spec name a checkpoint trained against them
is stamped with. It is derived from a `GameSetup`, so a run plays, encodes, and
trains under one configuration rather than under a build constant — the plane
layout below is the same for every setup, but its extent is not.

The plane indices, `TOTAL_FP_COUNT`, and `MOVEMENT_INDEX` stay module constants
because they are the part of the contract that does *not* vary: every
composition encodes into the same fourteen planes, and every board addresses
the same twelve movement offsets. That is deliberate rather than incidental — see
`TOTAL_FP_COUNT` and `MOVEMENTS_PER_POSITION` below.

The specification these constants implement is `doc/neuralnetwork/eng-nn-4.md`.
"""

from dataclasses import dataclass, field

from ...board import BoardLayout
from ...game_setup import GameSetup
from ...pieces import ArmyComposition

# The engine I/O spec this tensor layout implements. Checkpoints stamp it so a
# checkpoint saved against a superseded spec is rejected at load time instead of
# silently mismapping onto the current, differently-shaped input (see
# ctf_checkpoint.py).
ENGINE_SPEC_NAME = "ENG_NN_4"

# Feature Planes:
FP_OUR_FLAG = 0
FP_OUR_RANK_5 = 1
FP_OUR_RANK_4 = 2
FP_OUR_RANK_3 = 3
FP_OUR_RANK_2 = 4
FP_OUR_RANK_1 = 5
FP_THEIR_FLAG = 6
FP_THEIR_RANK_5 = 7
FP_THEIR_RANK_4 = 8
FP_THEIR_RANK_3 = 9
FP_THEIR_RANK_2 = 10
FP_THEIR_RANK_1 = 11
FP_PASSABLE = 12
FP_INACTIVITY_COUNT = 13

TOTAL_FP_COUNT = 14

# Every offset a legal ply can have, in three groups: the one-square orthogonal
# step, the two-square orthogonal step the unencumbered bonus allows, and the
# one-square diagonal attack added to the baseline at major 2 (rules.md 4.3).
#
# The diagonals are appended rather than interleaved so the orthogonal indices
# keep the values they had under ENG_NN_2 — which buys nothing at load time
# (a differently-shaped policy head is rejected on the spec stamp regardless)
# but keeps a hand-read logit index meaning the same thing across the two specs.
#
# A diagonal offset is only ever an attack: diagonal movement onto an empty
# square is never legal, so no index has to distinguish the two. The action
# space addresses ply *geometry*; legality comes from the rules engine at decode
# time (see doc/neuralnetwork/README.md).
MOVEMENT_INDEX = {
    #(row_delta, column_delta)
    (1, 0): 0,
    (0, 1): 1,
    (-1, 0): 2,
    (0, -1): 3,
    (2, 0): 4,
    (0, 2): 5,
    (-2, 0): 6,
    (0, -2): 7,
    (1, 1): 8,
    (1, -1): 9,
    (-1, 1): 10,
    (-1, -1): 11,
}

MOVEMENTS_PER_POSITION = len(MOVEMENT_INDEX)
"""Movement offsets, which — like the plane count — do not vary by board.

The offsets are square-to-square deltas, so the same twelve address every ply on
every layout; only how many source squares they are addressed *from* changes."""


@dataclass(frozen=True)
class TensorLayout:
    """The shapes and spec name one board and army encode to.

    Held as a value rather than read from module constants because a board is a
    property of the ruleset, not a build default: a position from a differently
    shaped board would index cleanly into this one's tensor rather than failing,
    so the contract has to be checked rather than assumed. Everything that builds
    a network, encodes a position, or stamps a checkpoint takes one of these.

    Board and composition are held separately rather than as the `GameSetup` they
    came from: two setups resolved from different configurations that reach the
    same board and army are the *same* tensor contract, and comparing them should
    say so. `for_setup` is the constructor every seam actually uses.
    """

    layout: BoardLayout
    composition: ArmyComposition

    spec: str = field(init=False, compare=False, repr=False)
    input_shape: tuple[int, int, int] = field(init=False, compare=False, repr=False)
    action_space_shape: tuple[int, int, int] = field(
        init=False, compare=False, repr=False
    )

    def __post_init__(self) -> None:
        # Derived members are excluded from equality for the reason `BoardLayout`
        # excludes its own: they are a function of the defining fields, so
        # comparing them would compare the same thing twice.
        object.__setattr__(
            self, "spec", f"{ENGINE_SPEC_NAME}/{self.layout.layout_id}"
        )
        object.__setattr__(
            self,
            "input_shape",
            (TOTAL_FP_COUNT, self.layout.rows, self.layout.columns),
        )
        object.__setattr__(
            self,
            "action_space_shape",
            (MOVEMENTS_PER_POSITION, self.layout.rows, self.layout.columns),
        )

    @classmethod
    def for_setup(cls, setup: GameSetup) -> "TensorLayout":
        """The tensor contract a game played under `setup` encodes to."""
        return cls(setup.layout, setup.composition)

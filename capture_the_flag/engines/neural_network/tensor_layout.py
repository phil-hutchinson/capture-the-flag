"""The tensor contract between a game and the learned play engine.

`TensorLayout` is that contract as a **value**: the input and action-space shapes
a network is built at, and the engine-spec name a checkpoint trained against them
is stamped with. It is derived from a `GameSetup`, so a run plays, encodes, and
trains under one configuration rather than under a build constant — the plane
layout below is the same for every setup, but its extent and its per-rank
normalisers are not.

The plane indices, `TOTAL_FP_COUNT`, and `MOVEMENT_INDEX` stay module constants
because they are the part of the contract that does *not* vary: every
composition encodes into the same thirty-four planes, and every board addresses
the same twelve movement offsets. That is deliberate rather than incidental — see
`TOTAL_FP_COUNT` and `MOVEMENTS_PER_POSITION` below.

The specification these constants implement is `doc/neuralnetwork/eng-nn-3.md`.
"""

from dataclasses import dataclass, field

from ...board import BoardLayout
from ...game_setup import GameSetup
from ...pieces import ArmyComposition

# The engine I/O spec this tensor layout implements. Checkpoints stamp it so a
# checkpoint saved against a superseded spec is rejected at load time instead of
# silently mismapping onto the current, differently-shaped input (see
# ctf_checkpoint.py).
#
# ENG_NN_3 supersedes ENG_NN_2 (doc/neuralnetwork/eng-nn-2.md) because major 2's
# diagonal attack is exactly the case doc/neuralnetwork/README.md names as
# forcing a new spec: ply geometry the old action space cannot address.
ENGINE_SPEC_NAME = "ENG_NN_3"

# Feature Planes:
FP_OUR_FLAG = 0
FP_OUR_TOWER = 1
FP_OUR_RANK_1 = 2
FP_OUR_RANK_2 = 3
FP_OUR_RANK_3 = 4
FP_OUR_RANK_4 = 5
FP_OUR_RANK_5 = 6
FP_OUR_RANK_6 = 7
FP_THEIR_FLAG = 8
FP_THEIR_TOWER = 9
FP_THEIR_RANK_1 = 10
FP_THEIR_RANK_2 = 11
FP_THEIR_RANK_3 = 12
FP_THEIR_RANK_4 = 13
FP_THEIR_RANK_5 = 14
FP_THEIR_RANK_6 = 15
FP_PASSABLE = 16
FP_INACTIVITY_COUNT = 17
# Engineered Planes
FP_OUR_FLAG_RELATIVE_ROW = 18
FP_OUR_FLAG_RELATIVE_COLUMN = 19
FP_THEIR_FLAG_RELATIVE_ROW = 20
FP_THEIR_FLAG_RELATIVE_COLUMN = 21
FP_OUR_RANK_1_QUANTITY = 22
FP_OUR_RANK_2_QUANTITY = 23
FP_OUR_RANK_3_QUANTITY = 24
FP_OUR_RANK_4_QUANTITY = 25
FP_OUR_RANK_5_QUANTITY = 26
FP_OUR_RANK_6_QUANTITY = 27
FP_THEIR_RANK_1_QUANTITY = 28
FP_THEIR_RANK_2_QUANTITY = 29
FP_THEIR_RANK_3_QUANTITY = 30
FP_THEIR_RANK_4_QUANTITY = 31
FP_THEIR_RANK_5_QUANTITY = 32
FP_THEIR_RANK_6_QUANTITY = 33

TOTAL_FP_COUNT = 34
"""The plane count, which is **one number across every composition**.

An army fielding no Foot Soldier still encodes into a tensor with a Foot Soldier
presence plane and a Foot Soldier quantity plane; both simply read zero
throughout. Dropping the unused planes would shrink `standard_skirmish`'s input
by four channels and make the two compositions two different contracts, under
which the question of whether a Battle-trained trunk transfers to Skirmish could
not even be asked. Keeping the layout fixed leaves that an open experiment rather
than a foreclosed one, at the cost of four dead channels on the smaller army."""

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

    Held as a value rather than read from module constants because two rulesets
    are live and their boards differ: a 12 x 12 encoder and an 8 x 8 one are two
    incompatible tensor contracts, and a position from the wrong one would index
    cleanly into the other rather than failing. Everything that builds a network,
    encodes a position, or stamps a checkpoint takes one of these.

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

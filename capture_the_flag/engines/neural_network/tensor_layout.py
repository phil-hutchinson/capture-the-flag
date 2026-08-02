from ...board import STANDARD_144

ENCODED_LAYOUT = STANDARD_144
"""The board this tensor contract is shaped for.

Still a constant, and still Battle: the shapes below are module-level, so they
cannot yet vary per run. Making them derive from the run's configuration -- and
qualifying `ENGINE_SPEC_NAME` by layout so a checkpoint trained on one board
cannot meet a differently-shaped input -- is step 8 of story 37. Named here
rather than left as bare numbers so that step has one place to change."""

# The engine I/O spec this tensor layout implements. Checkpoints stamp this name
# so a checkpoint saved against a superseded spec is rejected at load time
# instead of silently mismapping onto the current, differently-shaped input (see
# ctf_checkpoint.py).
#
# ENG_NN_3 supersedes ENG_NN_2 (doc/neuralnetwork/eng-nn-2.md) because major 2's
# diagonal attack is exactly the case doc/neuralnetwork/README.md names as
# forcing a new spec: ply geometry the old action space cannot address. Its
# spec document is minted at the end of story 37, once the rest of the contract
# — board-parametric shapes and composition-driven quantity planes — has settled;
# minting it now would publish a contract this story goes on to change.
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
ACTION_SPACE_SHAPE = (MOVEMENTS_PER_POSITION, ENCODED_LAYOUT.rows, ENCODED_LAYOUT.columns)
INPUT_SHAPE = (TOTAL_FP_COUNT, ENCODED_LAYOUT.rows, ENCODED_LAYOUT.columns)


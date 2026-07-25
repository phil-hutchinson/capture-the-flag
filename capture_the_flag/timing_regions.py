"""The region vocabulary: every name this project's timing reports can contain.

Collected in one place so the names in a report are a fixed, greppable set
rather than string literals scattered across the modules that record them, and
so the shape of a report can be read here without running one.

Names are kebab-case and describe *work*, not the function that happens to do
it — a report is read by someone asking where the time went, not by someone
navigating the call graph. Nesting is by call path (see
`instrumentation/timing.py`), so the same name legitimately appears at several
places in a tree: `legal-plies` under `search` is a different line from
`legal-plies` under `outcome`.

One family of names lives elsewhere: the search-boundary regions (`search`,
`search-with-policy`, and the tree-maintenance calls) are defined in
`instrumentation/timed_search.py`, next to the engine that records them, because
that module is shareable and cannot import this game-specific one.
"""

# Root regions — one per entry point, covering everything that entry point does.
ROOT_BATCH = "game-batch"
ROOT_TRAINING = "training-run"

# Batch play. The games themselves run inside the shared tournament runner, so
# `play-games` is one region covering all of them; per-game structure shows up
# through `starting-position`, which the runner calls back into once per game.
PLAY_GAMES = "play-games"
WRITE_RECORDS = "write-records"

# Training. `generation` accumulates across every generation of a run — the
# report is cumulative, so its call count is the number of generations and its
# mean is what one generation costs. Batch assembly, the backward pass, and the
# optimizer step happen inside the shared training loop and land in `train`'s
# unattributed remainder; instrumenting them would need a change upstream.
GENERATION = "generation"
SELF_PLAY = "self-play"
TRAIN = "train"
BUILD_OPTIMIZER = "build-optimizer"
"""Constructing the generation's optimizer. Nominally trivial, but the first one
in a process pays torch's lazy optimizer initialization — around a second, once
per run — which is worth naming rather than leaving as a mystery gap in the
first generation."""
SAVE_CHECKPOINT = "save-checkpoint"
POLICY_LOSS = "policy-loss"
POLICY_TRANSFORM = "policy-transform"

# Game mechanics: the per-position work that search calls hundreds of thousands
# of times per game.
LEGAL_PLIES = "legal-plies"
APPLY_PLY = "apply-ply"
OUTCOME = "outcome"
OUTCOME_REASON = "outcome-reason"
STARTING_POSITION = "starting-position"

# The learned evaluator: one position in, a value and a policy out. The four
# children below account for `evaluate-position`; what they leave over is the
# shared base class's own tensor plumbing (batching a single sample, unwrapping
# the value tensor, entering the no-grad context) — microseconds a call, and
# nameable only by copying that class's body into this repository, which is not
# worth doing for it.
EVALUATE_POSITION = "evaluate-position"
ENCODE_POSITION = "encode-position"
NETWORK_FORWARD = "network-forward"
DECODE_POLICY = "decode-policy"
NETWORK_MODE_SWITCH = "network-mode-switch"
"""Switching the network between training and evaluation mode.

Nominally a flag, actually a recursive walk over every submodule — which at trunk
depth costs more per call than encoding a position does. The shared evaluator
performs one on *every* single-position evaluation, so this appears under
`evaluate-position` in search, and separately on the training branch where the
training loop switches the shared model to train mode."""

# Policy decoding, phase by phase. The first full-scale run left three quarters
# of `decode-policy` unattributed — 9.4% of the whole run, and a ceiling on what
# any optimization could claim — so its four phases are named individually. Each
# is one region per decode, never one per ply: a phase costs a couple of hundred
# microseconds, some hundreds of times a region entry, while a region per ply
# would be entered tens of millions of times per run to time work only a few
# times its own cost. `legal-plies` stays a sibling of these four rather than a
# parent of the first, so its line in a report means what it meant before.
MAP_PLY_SLOTS = "map-ply-slots"
"""Locating each legal ply's slot in the action space."""
BUILD_POLICY_MASK = "build-policy-mask"
"""Building the additive mask that leaves only legal slots unmasked."""
POLICY_SOFTMAX = "policy-softmax"
"""The masked softmax: raw logits to a distribution over legal plies."""
READ_PLY_PROBABILITIES = "read-ply-probabilities"
"""Reading each legal ply's probability back out of the tensor."""

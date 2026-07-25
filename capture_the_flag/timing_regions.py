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

# The learned evaluator: one position in, a value and a policy out. The three
# children below account for `evaluate-position`; what they leave over is the
# shared base class's own wrapping (eval-mode switching, batching a single
# sample, unwrapping the value tensor).
EVALUATE_POSITION = "evaluate-position"
ENCODE_POSITION = "encode-position"
NETWORK_FORWARD = "network-forward"
DECODE_POLICY = "decode-policy"

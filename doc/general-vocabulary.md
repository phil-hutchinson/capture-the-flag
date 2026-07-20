# General Vocabulary

A living glossary of non-domain terms (machine learning, game theory, search,
and related computer-science concepts) that have come up in developer
discussion — built up by `/learning-assistant` rather than written in one
pass. Entries are short, plain-language groundings, not formal definitions.
Game-specific terms already have a glossary in
[`doc/ruleset/rules.md`](ruleset/rules.md#7-glossary); this document is for
everything else.

Avoid trademarked product names here — describe concepts generically.

## Machine learning

**Inductive bias** — knowledge built into a model's structure rather than
learned from data, biasing it toward solutions of a known shape. Convolutions
are an inductive bias ("patterns that work in one place work everywhere");
choosing whether to encode a game symmetry into the network or let training
discover it is choosing how much inductive bias to add.

**Equivariance / weight sharing** — a model is equivariant to a transform when
shifting the input shifts the output the same way, usually achieved by reusing
(sharing) the same weights across positions. Convolutions are equivariant to
board translation; the same trick can be applied along any axis with a genuine
symmetry (e.g. piece rank, when interactions depend only on rank differences).

**Feature engineering** — hand-computing input features the network could in
principle derive itself, to spend architecture budget elsewhere. Best
candidates are facts that are static or rule-derived, cheap to compute, and
expensive for the network to reconstruct (e.g. anything requiring many
layers of spatial propagation). The risk is baking in something wrong or
perspective-inconsistent, not redundancy — redundant inputs are cheap.

**Inference** — running a network forward-only to get its outputs, with no
gradient bookkeeping and no parameter changes. Everything outside training is
inference; in self-play training schemes, inference (one network evaluation
per search simulation) dominates the compute, not the parameter updates.

**Loss / gradient** — the loss is one scalar scoring how wrong the network's
outputs are on a batch of examples; the gradient, computed from it by
backpropagation, is one value per parameter saying how much the loss would
fall if that parameter nudged up. Each training step: forward pass → scalar
loss → gradient → small parameter update against the gradient.

**Replay buffer** — the pool of stored training examples that self-play
writes into and training samples minibatches out of. Decouples the two
loops: game generation appends (position, search visit-distribution,
outcome) tuples; training repeatedly draws random batches, so each example
is reused across many updates and consecutive (correlated) positions from
one game get shuffled apart.

## Neural networks

**Feature plane / channel** — one 2D grid-shaped layer of a network's input,
holding a single kind of fact about each board square (e.g. "is there an own
Knight here"). Planes stack along the *channel* axis to form the full input
(a 12×12×N tensor is an N-channel image). Only the grid axes carry spatial
meaning; channels have no adjacency or ordering significance, so their order
just needs to be fixed and consistent.

**One-hot encoding** — representing a category as a vector (or plane stack)
that is all zeros except a single 1 marking which category applies. Preferred
over numeric codes (Knight=3, Tower=7) because a network would otherwise have
to learn to undo the arbitrary arithmetic relationships the codes imply.

**Logit** — a network's raw, unbounded output score before any normalization:
any real number, often negative. Logits express *relative* preference only and
only become probabilities after softmax. A policy head emits one logit per
action-space entry — including entries no legal move maps to.

**Softmax** — the standard operation turning a vector of logits into a
probability distribution: exponentiate each entry, then divide by the sum.
Exponentiation makes everything positive (so negative logits are fine) while
preserving order — bigger logit, bigger probability. Restricting to a subset
(e.g. legal moves) by gathering-then-softmaxing or masking to −∞ gives the
same result.

**Policy head / value head** — the two small output branches of a two-headed
game network, sitting on one shared body (the *trunk*). The value head is the
network's gut sense of how good the current position is (a single number in
[-1, 1]); the policy head is its gut sense of which moves look promising (one
logit per action-space entry). Keeping the heads thin forces most learning
into the shared trunk, so one board representation serves both judgments.

**Residual block / skip connection** — a network building block whose output
is its input *plus* a learned correction (the input is added back in via a
"skip connection" around the layers). Each block then only learns a small
refinement rather than rebuilding the whole representation, and gradients
flow straight through the additions — the trick that makes very deep
convolutional towers trainable.

**Batch normalization** — a layer that rescales its inputs to a standard
range (roughly zero mean, unit spread, with learned adjustments) using
statistics gathered during training. Keeps activations well-behaved as depth
grows, making deep networks train faster and more stably; conventionally
inserted after each convolution, before the ReLU.

**Element / elementwise** — an element is one cell of a tensor (one number at
one index); an elementwise operation applies independently at each cell,
pairing corresponding elements of same-shaped tensors. The residual skip
connection is an elementwise add — which is why a block's output must have
exactly its input's shape.

**Distributed representation / polysemantic channel** — learned channels
rarely correspond one-to-one with human-nameable concepts; a concept is
usually spread as a *pattern* across many channels, and one channel
participates in many concepts. Named examples ("threat detector") are
pedagogical shorthand for directions in the network's feature space, not
predictions of what individual filters will mean.

**Presence detector (one-sided activation)** — after ReLU, a channel can only
fire positively or stay silent, so each unit reports the *presence* of its
pattern, never its opposite. Good-vs-bad meaning lives in the downstream
weights (which can be negative), not in the activation's sign; networks
typically learn paired channels for the two poles of a signed concept.

**Receptive field** — the patch of the input board that can influence a given
activation. Each 3×3 conv layer widens it by one square in every direction,
so depth determines how far apart two squares can be and still be related by
the network: a tower needs roughly board-diagonal-many conv layers before any
single activation can "see" the whole board.

**Depth vs. width** — the two scaling knobs of a conv tower. Width (filters)
is the per-square vocabulary: how many distinct features the network can
track about each square at once; parameters grow with width². Depth (blocks)
is composition: each layer builds features *of* the previous layer's
features and extends spatial reach one step per conv; parameters grow
linearly with depth.

**Zero-padding** — inserting a ring of zero-valued fake squares around a
convolution's input so the output keeps the board's size (a 3×3 conv would
otherwise shrink it by one square per side). The padding value is always
zero and applies at every conv layer, so input planes should be oriented so
that zero is the *correct* meaning for off-board — e.g. a "passable" plane
(0 off-board reads as impassable) rather than an "impassable" plane
(0 off-board would read as open ground).

**Cumulative (thermometer) encoding** — an ordinal alternative to one-hot:
entry *k* means "value is *k* or beyond," so a rank-2 piece lights planes 2
through 6 rather than plane 2 alone. Makes order comparisons ("outranks")
directly readable as differences, letting one learned pattern apply across
all rank levels.

**Model interchange format** — a single exported file bundling a network's
architecture (as a computation graph of standard operations) and its trained
parameters, runnable by a lightweight runtime with no training framework and
no knowledge of the network's internals. It makes the tensor input/output
shapes the *entire* integration contract: internals can change freely between
exports without the consumer noticing. What it deliberately excludes is the
semantics of those tensors — what the planes mean, how outputs map to moves —
which must live in a separate written spec.

## Game theory

**Markov property / Markov-complete state** — a state representation is
Markov-complete when the current state alone determines the game's entire
future (legal moves, outcomes, transitions), independent of the path taken to
reach it. Test: walk the rules and ask, for each rule affecting legality or
outcome, whether it is decidable from the state alone; any history-dependent
rule (repetition, no-progress limits, "has this piece moved") must have its
relevant history folded into the state, e.g. as a counter or rights flag.

## Search / PUCT

**Policy prior** — the network's decoded move distribution as consumed by
search: not a rule for picking the move, but a hint about which branches
deserve exploration budget (the P term in PUCT). The move actually played
comes from the visit counts the search accumulates, which can override the
prior when lookahead disagrees with the network's gut feeling.

**Temperature** — a knob controlling randomness when sampling from a
distribution (e.g. selecting a ply from visit counts). Temperature 1 samples
proportionally; lowering it sharpens toward always picking the top choice
(→ 0 is fully greedy); raising it flattens toward uniform. Mnemonic: heat is
randomness — freeze it and all randomness stops.

## Python

**Module vs. package** — a module is a single `.py` file; a package is a
directory of modules with an `__init__.py` (which makes the directory itself
importable, so a package is also a module). "Put it in a shared module" just
means "make another `.py` file in a sensible place and import from it."

## Mathematics

**Involution** — an operation that is its own undo: applying it twice gets you
back exactly where you started (like flipping a card face-down and back). Both
a 180° board rotation and a single-axis mirror are involutions; that property
is what lets the encoder and decoder share one perspective transform without
needing separate "forward" and "inverse" versions.


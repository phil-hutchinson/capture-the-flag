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

**Epoch / minibatch / epoch loss** — an *epoch* is one full pass over the whole
training dataset; within it the data is split into *minibatches* and one
gradient update is taken per minibatch, so an epoch is many updates, not one.
"Train for N epochs" means show the network the same dataset N times over. The
*epoch loss* is the average loss across one such pass — a single summary number
(here the combined value + policy loss, each minibatch weighted by its sample
count) whose downward trend across epochs is the signal that learning is
happening. Training repeatedly on one fixed batch (the overfit-a-batch sanity
check) lets the loss fall by memorization, which tests the plumbing without
proving general strength.

**Optimizer** — the component that turns each computed gradient into an actual
weight change; backprop produces the gradient, the optimizer decides the step.
You select and configure one from the framework (e.g. Adam, SGD) over the
network's parameters rather than implementing it, and the training loop calls its
step after each minibatch. Plain SGD applies one global learning rate; Adam
adapts a per-parameter step size from recent gradient history, so it mostly "just
works" without careful learning-rate tuning — which is why it's the usual default
for a "does this learn at all" check.

**Optimizer state (moment estimates / momentum)** — the running per-parameter
statistics an adaptive optimizer carries *between* steps: Adam keeps a first
moment (an EMA of the gradient) and a second moment (an EMA of the squared
gradient), plus a timestep for bias correction; SGD-with-momentum keeps a
velocity buffer. It is separate from the weights — dropping it leaves the model
intact but makes the optimizer "re-warm up" (moments restart at zero, so the
first few steps are noisier and mis-scaled until the EMAs refill). Persisting it
across a training resume only matters when one long-lived optimizer spans the
whole run (e.g. with a replay buffer and a learning-rate schedule); if a fresh
optimizer is built per generation, its state never crosses a generation boundary
anyway, so saving weights only and re-initialising on resume is exactly
consistent with normal operation.

**Backpropagation** — the algorithm that turns the one scalar loss into a
gradient over every parameter, by applying the chain rule backward through the
network layer by layer. The forward pass records what each operation did; the
backward pass walks it in reverse, accumulating each parameter's share of the
loss. This is why collapsing a batch to a single number (via `.sum()` /
`.mean()`) loses nothing: differentiation re-expands that scalar into a full
per-parameter — and, one step earlier, per-logit — signed correction.

**Softmax cross-entropy gradient** — the reason the policy loss can train from a
scalar. For a softmax followed by cross-entropy against a target distribution,
the gradient on each logit collapses to `predicted_i − target_i`: a signed,
per-column error. A column the network favoured more than the search visited
gets a positive gradient (descent lowers it); one it favoured less gets a
negative gradient (descent raises it); an exact match gets zero. So the "this
was too high, this too low, by how much" signal lives in the gradient, not the
scalar loss — the scalar is only a summary to watch trend down. A corollary:
since the target is zero on illegal columns, any illegal move the network likes
gets gradient `predicted − 0 > 0` and is pushed down, so an unmasked loss still
teaches legality.

**Cross-entropy** — the standard loss for scoring a predicted probability
distribution against a target one: it sums, over the possible outcomes, the
target probability times the negative log of the predicted probability, so it
rewards putting mass where the target has mass and punishes confident wrong
guesses hardest. In this project it scores the policy head (a softmax over the
legal plies) against the search's visit distribution; the target is itself a
full distribution, not a single "correct" move. At a perfect match it does
*not* reach zero — it bottoms out at the *entropy* of the target distribution
(see below) — reaching zero only when the target puts all its mass on one
option. Its gradient drives the prediction toward the target either way.

**Entropy** — how spread-out a distribution is: its probability-weighted
average surprisal, −Σ p·log p (in bits when the log is base 2). Largest for a
uniform distribution, zero for a certain (one-hot) one. It is the *floor* of
cross-entropy — scoring a distribution against itself yields its entropy, not
zero — so a perfectly-matched policy prediction still shows a positive loss
equal to that entropy.

**Surprisal** — the surprise of a single outcome under a prediction, −log p:
near zero for something you called almost certain, growing without bound as the
predicted probability approaches zero. Cross-entropy is the target-weighted
average of the prediction's surprisals; entropy is the special case where a
distribution weights its own surprisals.

**Mode-covering (cross-entropy asymmetry)** — because surprisal −log q is
unbounded as q→0 but bounded (→0) as q→1, cross-entropy punishes
*under*-prediction of an important option far more than *over*-prediction of an
unimportant one. Assigning near-zero probability to a ply the target weights
heavily costs enormously; keeping a little leftover probability on plies that
turn out unimportant costs almost nothing. So the loss drives a prediction to
*cover* every option the target cares about (never zero one out) rather than to
commit to a single peak — exactly the right pressure for a policy target: the
network is penalized hardest for ignoring a move the search rated well.

**KL divergence (relative entropy)** — how far a prediction q sits from a
target p: Σ p·log(p/q), equivalently cross-entropy minus the target's entropy.
Zero exactly when the two match, positive otherwise. Because a training
target's entropy is a fixed constant, minimizing cross-entropy and minimizing
KL divergence give identical gradients — so the simpler cross-entropy is used
as the loss even though KL is the "distance" that reads zero at a match.

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

**Broadcast plane (global scalar as constant plane)** — the standard way to
feed a whole-board scalar (e.g. a per-rank material count, side-to-move flag)
to a convolutional trunk: fill an entire 12×12 plane with that one value so it
rides alongside the spatial planes. It hands the network a global fact
directly, sparing it from reconstructing it via board-spanning receptive field
and a summation path the conv tower lacks until its head.

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

**Weight initialization / symmetry breaking** — networks start from *small
random* weights, never all zeros. Zero (or any identical) init makes every unit
in a layer compute the same output and receive the same gradient, so they update
in lockstep and never differentiate — the layer collapses to acting like a single
unit. Random init breaks that symmetry; the "small" keeps early activations and
gradients in a sane range. A consequence at cold start: a tanh value head from
literal zero weights would output exactly 0, but real (random) init emits small
nonzero noise, so an all-draw batch still shows a tiny value loss that training
drives toward the constant 0 target.

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

## Reinforcement learning / training dynamics

**Sparse reward / cold start** — the situation where the only learning signal
(here, the game outcome) appears rarely, because a near-random early policy
almost never reaches a decisive terminal. Until *something* produces a
non-neutral result the value targets are almost all the same value (draws → 0),
giving the network nothing to distinguish positions by, so it collapses to
predicting that constant. The flywheel that turns weak play into strong play
cannot start until decisive terminals appear often enough to bite.

**Credit assignment** — the problem of deciding *which* earlier decisions
deserve the blame or credit for a final outcome. When the collector labels
every ply of a game with the same terminal ±outcome (no discounting) and the
policy was near-random over a long horizon, most of those labels are
unattributable: the win wasn't *caused* by the aimless midgame positions it's
stamped onto, so the same-looking position ends up labeled "win" once and
"draw" ninety-nine times. Sparse *and* noisy-labeled is worse than sparse
alone — the signal has to be local (outcome tight in time and reliably caused
by the position) to be learnable.

**Bootstrapping (value)** — improving the value estimate of a position from the
(searched) value estimates of positions just after it, rather than only from
final outcomes. It's how a tight, learnable signal near a terminal — e.g. "a
piece adjacent to the enemy flag ≈ win" — leaks backward one ply per
generation into earlier positions, gradually extending the network's sense of
"good position" away from the terminal. This is the mechanism that lets the
cold-start flywheel turn once *any* attributable signal exists.

**Curriculum learning** — training on a sequence of progressively harder
versions of the task instead of the full task from the start, so the early,
easy stages produce a learnable signal that bootstraps the harder ones. Here:
begin self-play with a tiny army (low branching, frequent decisive terminals),
then grow the army toward the real game. Works when each stage's lesson is
directionally right but incomplete; breaks when an early stage teaches
something the later stages must actively un-learn.

**Catastrophic forgetting** — a network overwriting earlier-learned competence
when the training distribution shifts to something new, because the same
weights get repurposed for the new data. The failure mode of a hard-switched
curriculum (or any non-stationary training): mitigated by *ramping* stages —
keeping some earlier-stage examples in the replay buffer during the transition
— rather than switching cleanly between them.

**Non-stationarity (training distribution)** — when the distribution of
training examples changes over the course of training rather than being drawn
from one fixed source, so the network chases a moving target. Inherent to
self-play (the opponent is the improving network itself) and amplified by a
curriculum that deliberately shifts the position distribution across stages.

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

## Hardware / performance

**Batch-1 GPU latency (launch overhead & occupancy)** — for a *single* small
input, a GPU is often no faster than a CPU, for two reasons unrelated to the
arithmetic (which is genuinely microseconds). First, a forward pass issues one
scheduled operation ("kernel") per layer — dozens of them, each carrying a
fixed host-side launch/dispatch cost and chained by data dependency, so the
overheads serialize and dwarf the compute. Second, a tiny per-position result
can only occupy a sliver of the GPU's thousands of cores (low *occupancy*).
Both overheads are per *call*, not per position, so the fix is batching many
positions into one forward pass: it amortizes the launch cost and fills the
cores, which is the only regime where a GPU's throughput advantage appears.
A CPU "wins" at batch-1 not by faster math but by paying none of these
overheads. In serial MCTS every leaf evaluation is a batch-1 call, which is
why plain self-play does not benefit from a GPU until the search is
parallelized enough to batch its evaluations.

**Eager vs. graph/compiled execution** — in *eager* mode each network
operation runs the moment Python reaches it (simple and debuggable, but paying
per-op launch/dispatch overhead every call); *graph* or *compiled* mode captures
the whole forward pass once into a static graph and replays it, fusing
operations, folding inference-time constants (e.g. batch-norm into the
preceding convolution), and collapsing many kernel launches into one. Compiling
attacks launch overhead (helping even at batch-1) but not occupancy — the
kernels are still small — so it complements batching rather than replacing it.
The cost is flexibility: graph capture wants static input shapes and has a
warm-up cost, so the usual pattern is develop eager, compile for the long run.

## Python

**`Callable[[args], Return]` (function type)** — the type annotation for "a
function/callable." Two slots: the inner list is the *parameter types*, the
second is the *return type*. Empty inner brackets `Callable[[], T]` mean **takes
no arguments** (a populated-with-nothing parameter list, not "unspecified") and
returns `T`; `Callable[[int, str], bool]` takes those two and returns a bool.
Distinct from `Callable[..., T]`, where the literal `...` means "any arguments,
don't care." A zero-arg factory like the self-play `position_factory` is
`Callable[[], TPosition]`: call it with nothing, get a position.

**Type variable / generic (`TPosition`, `TPly`)** — a placeholder type that a
generic class or function is defined over, pinned to a concrete type when
instantiated. `SelfPlayCollector[TPosition]` is written against an abstract
"position" and "ply" type; for this repo they resolve to the Capture the Flag
position and ply. Conventionally named with a leading `T`.

**Closure** — a function that captures ("closes over") variables from the scope
it was defined in, so those values ride along when it's called later. A factory
function returning an inner function is the usual way to bake settings into a
zero-arg callable: the inner function reads the enclosing parameters even after
the outer one has returned.

**Partial application (`functools.partial`)** — pre-binding some of a function's
arguments to produce a new callable that needs only the rest (here, none). The
Python analogue of currying: `partial(build, army_size=2)` returns something you
call with the remaining args. Freezes settings into a function without writing a
closure by hand.

**Callable object (`__call__`)** — an instance of a class that defines
`__call__` can be invoked like a function (`obj()` runs `obj.__call__()`).
Preferred over a closure/partial when there is real configuration to hold: the
class is named, importable, and testable, configured in `__init__` and invoked
with no further args — so an instance *is* a `Callable[[], T]`. Keep per-call
behaviour (e.g. fresh randomness) inside `__call__`, not `__init__`.

**Structural typing (duck typing)** — a value satisfies a type by having the
right shape/behaviour, not by declaring it inherits from a named type. Python's
`Callable[[], T]` is structural: a plain function, a closure, a `partial`, and a
class instance with `__call__` are all interchangeable at that seam because each
is callable-with-no-args — which is what lets one factory be swapped for another
without the consumer knowing.

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


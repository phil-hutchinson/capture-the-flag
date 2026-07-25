# Story: CUDA in the container — a GPU-capable development environment

## Summary

Make the GPU an available option for this project, end to end. Today the
development container installs CPU-only torch wheels by deliberate choice
(`.devcontainer/Dockerfile`: "the container has no GPU passthrough, and the
default Linux wheels pull in the multi-GB CUDA stack"), the container is started
with no device passthrough, and the training and self-play code has never run
anywhere but the default device. This story delivers:

- **Two container configurations** — the existing CPU one, which stays the
  default, and a CUDA one that installs GPU-capable torch wheels and passes the
  host GPU through.
- **A single device decision that flows through the whole stack** — whichever
  configuration the developer opened, torch uses that device everywhere: the
  network, the evaluator's encode/forward/decode path, the training batches, and
  the loss functions. No module decides for itself.
- **The code changes that make a GPU run actually work** — chiefly, every tensor
  that meets another tensor has to be on the same device, which is not true of
  the code as written.

This story is about **availability, not speed**. It makes CUDA usable and proves
a GPU run is correct. It does not measure a speedup, does not claim one, and does
not restructure anything in pursuit of one. Measurement happens afterwards, on
the developer's own initiative, using the apparatus story 00000029 already
delivered.

## Motivation

Every part of the pipeline that could benefit from a GPU is now in place — a
configurable-width residual trunk (story 00000026), a self-play/training loop
(story 00000009), and instrumentation that can say where the time goes (story
00000029) — and none of it has ever executed a single CUDA kernel. The gate is
not the code being unready; it is that the environment offers no way to try.

Three things make this worth doing as its own story rather than as a preamble to
a performance push:

- **The environment change is self-contained and reusable.** A GPU-capable
  container is infrastructure. Once it exists, every later experiment — batched
  inference, a wider trunk, longer training runs — can use it without
  relitigating build arguments, wheel indexes, and driver passthrough.
- **The code is quietly CPU-dependent in ways that only surface on a GPU.** The
  failure mode is a hard `RuntimeError` at the first device mismatch, not a
  silent wrong answer, so it will surface immediately — but debugging it cold, in
  the middle of a performance investigation, is a bad use of the investigation.
  Story 00000009's peer review found one such site and deliberately deferred it
  to GPU enablement; it is an example of the class, not the whole of it, and this
  story owns finding the rest.
- **Whether the GPU helps is genuinely open.** Self-play evaluates one position
  at a time; a batch-of-one forward pass through a small convolutional trunk may
  well be *slower* on a GPU than on a CPU once transfer overhead is counted.
  Training on real batches is the more plausible beneficiary. Bundling an
  unproven speedup into the enablement story would put a claim we cannot yet
  support on the critical path of a change that is useful regardless.

## What we want

### Two container configurations, CPU by default

The repository should offer a choice at "Reopen in Container" time:

- **CPU (default).** Behaviourally identical to today's container: same wheels,
  same image size, same rebuild cost, no GPU requirement on the host. A developer
  who does nothing differently gets exactly what they get today.
- **CUDA.** GPU-capable torch wheels, and the host GPU passed through to the
  container so `torch.cuda.is_available()` is true inside it.

Constraints on how the two relate:

- **One image definition, parameterized — not two Dockerfiles.** The two
  configurations differ in which torch wheels are installed and whether the GPU
  is passed through. Everything else — the Python version, pyright, ruff,
  pytest, the git and Claude Code setup, the editable install — is common and
  must not be duplicated into a second file that will drift.
- **The same torch version in both.** The configurations must differ by *build*
  (CPU vs CUDA), not by version. Otherwise any difference observed between them
  is unattributable, which would poison exactly the comparison the developer
  intends to run next.
- **The chosen wheel must survive container creation.** The project's editable
  install runs after the image is built and pulls `game-engine-core[learning]`,
  which depends on torch. It must not replace the deliberately-chosen build with
  a different one. This needs verifying, not assuming.
- **Cost stays opt-in.** The CUDA stack is multi-GB. The CPU configuration
  remains the default precisely so ordinary work does not pay for it.

The host prerequisites for the CUDA configuration (an NVIDIA driver, container
GPU support, and — on this developer's machine — WSL2 GPU passthrough) are
documented alongside it, including what to expect if the configuration is opened
on a machine that does not meet them.

### One device decision, honoured everywhere

There should be a single place that answers "what device is this run using," and
everything else should ask it rather than deciding independently. No scattered
`.cuda()` calls, no module that assumes the default device.

- **Default: whatever the container offers.** In the CPU container, torch cannot
  see a GPU, so the answer is CPU with no configuration required. In the CUDA
  container, the answer is the GPU. This is what makes "the configuration you
  opened is the device you get" true without the developer restating it.
- **Explicitly overridable.** Entry points that run games or training accept an
  explicit device choice, so CPU can be forced inside the CUDA container. This is
  not a nicety — it is how the two devices get compared at all, and how a GPU
  problem gets bisected.
- **An explicit request that cannot be honoured is an error, not a downgrade.**
  Asking for CUDA where CUDA is unavailable must fail with a clear message.
  Silently falling back to CPU would let a run that was supposed to exercise the
  GPU quietly not do so.
- **The device in use is visible.** Which device a run actually used is stated
  where a developer will see it, and recorded in the run's own record.
  `run_environment.py` already captures `torch_device` and `cuda_device_name`;
  this story's job is to make sure what it reports is the device actually used
  rather than merely the device available.

### Every tensor on the same device

The substance of the code work. The pipeline currently mixes tensors created in
several places, and today they agree only because everything defaults to CPU.
The known crossings, each of which needs an owner:

- **The evaluator's encode → forward → decode path.** A position is encoded into
  a fresh tensor, pushed through the network, and its outputs decoded back into
  plain Python values for search. The network may be on the GPU; the encoding is
  built on the CPU; search wants floats. There should be one documented crossing
  point in each direction, not an ad-hoc `.to(...)` wherever an error appeared.
- **Self-play samples.** Collected samples hold encoded positions and are
  accumulated across a whole generation before training sees them. They must be
  stored device-independently — holding a generation's worth of tensors in GPU
  memory would be both wasteful and a distinct failure mode — which means the
  batch that training builds from them starts on the CPU regardless of where the
  network lives.
- **The shared training loop's batch assembly, which we do not own.**
  `TrainingLoop._train_batch` in `game-engine-core` stacks the batch's encoded
  positions and builds its value targets with no device argument, then calls the
  model and the two loss functions. It offers no device parameter. The
  consequence is a design constraint, not a defect to fix upstream: **the model
  and the loss functions are the seams this repository owns, and the device
  crossing has to be handled there.** Both loss functions are injectable and the
  network is ours, so this is achievable without changing the pinned dependency —
  and this story does not change it.
- **The policy loss.** `ctf_policy_loss` allocates its dense target with
  `torch.zeros(...)` and no device, then multiplies it against the logits. This
  is the site story 00000009's peer review deferred to GPU enablement; the fix is
  known and belongs here.
- **The value loss.** The shared loop's default MSE compares the model's
  predictions against a CPU-built target tensor. If predictions are on the GPU,
  this has the same mismatch as the policy loss, in code we do not own — so it
  needs handling on our side of the seam.
- **Checkpoints.** A checkpoint written from a GPU run must load in the CPU
  container, and vice versa. Trained parameters are portable artifacts; the
  device they happened to be trained on is not part of their identity and must
  not become a compatibility stamp alongside the engine-spec and architecture
  stamps that already exist.

The list above is what is known from reading the code. Part of the deliverable is
confirming it is *complete* — a GPU run that gets through self-play, training,
checkpoint write, resume, and a played game is the evidence.

### Correctness on the GPU, stated honestly

The bar is that a GPU run does the same job as a CPU run, with a precise and
honest account of what "the same" can mean:

- **The stack runs end to end on CUDA** — self-play games complete, training
  steps run, losses decrease as they do on CPU, checkpoints round-trip, and a
  played game is legal and complete.
- **Same-device reproducibility holds.** Under a fixed seed, two CUDA runs on the
  same machine reproduce each other, exactly as two CPU runs do today.
- **Cross-device bit-parity is explicitly not claimed.** Not because floating
  point is loosely specified — IEEE 754 pins each individual operation down to
  the bit — but because a convolution is a *composite* of many operations, and
  nothing constrains how it is decomposed. Floating-point addition is not
  associative, so a tree reduction across GPU threads and a sequential reduction
  on the CPU disagree in the last bits while both being correctly rounded;
  fused multiply-add rounds once where an unfused path rounds twice; and library
  autotuning picks different algorithms on different hardware. All of this is
  ordinary and is documented as such by torch. A seeded CPU run and a seeded CUDA
  run may therefore diverge into entirely different games — one flipped selection
  at one search node is enough — and that is expected rather than a bug. Neither
  game is more correct than the other. Equivalence is demonstrated where it is
  meaningful — the same position encoding and forward pass agreeing within a
  documented tolerance across devices — and the divergence is written down so a
  later reader does not mistake it for a defect.
- **Reduced-precision defaults are a deliberate, recorded choice.** Distinct from
  the ordering effects above, TF32 is an actual precision reduction: on recent
  NVIDIA architectures, convolution and matmul inputs are truncated to a 10-bit
  mantissa, taking relative error from roughly `1e-7` to roughly `1e-3`. Our
  trunk is all convolutions, so this is not a marginal setting — and torch's
  defaults for it are both architecture-dependent and version-dependent. The
  story's requirement is that the setting be **explicit and recorded in the run's
  environment facts, not inherited silently**, since it determines what tolerance
  the cross-device comparison above can honestly claim. Whether to enable it for
  throughput is a later question; whether we know what it is set to is this one.
- **The test suite passes in both containers.** Tests that construct tensors must
  not silently assume CPU. GPU-specific tests are skipped, not failed, when no
  GPU is present, so the default CPU container stays green.

### The existing timing apparatus must still mean what it says

Taking measurements is not part of this story. But story 00000029's timing report
is always-on, so it will be running during every GPU run whether or not anyone is
reading it — and it must not quietly become wrong. The story owns establishing
that the existing approach transfers to CUDA, and making it clean where it does
not.

The specific hazard is that GPU kernel launches are **asynchronous**. A region
wrapped around a forward pass measures the time taken to *queue* the work, not to
do it. The queued work is then paid for later, at whatever point something forces
a wait — and in this pipeline that point is identifiable: the evaluator reads its
results back to the CPU in order to decode them. So the network's forward-pass
cost would be booked against the *decode* region, and story 00000029's report
would state, in good faith and with correct arithmetic, that decoding the policy
is the expensive part of evaluation. That is a worse outcome than no measurement
at all, because it is credible.

What we want:

- **The report's regions attribute GPU work to the region that caused it**, so
  the breakdown means under CUDA what it already means under CPU. The nesting and
  unattributed-remainder discipline story 00000029 established continues to hold.
- **The CPU path is untouched** — whatever is added for device work is inert when
  the run is on CPU, with no added cost and no behaviour change to the default
  configuration.
- **The cost of doing this is understood and stays within story 00000029's
  overhead discipline.** Synchronizing at a region boundary is not free, and the
  boundaries in question sit on the exact path a later story will want to
  optimize. This is a design decision to be made and justified in the
  implementation plan — which boundaries synchronize and which do not — not a
  blanket synchronize-everywhere.
- **Anything that still cannot be attributed honestly is documented** where the
  report is read, rather than left for a future reader to discover.

## Relationship to other work

- **Consumes** story 00000029's run record and environment facts, which already
  have a place for the device and the GPU name.
- **Resolves** the deferred policy-loss device mismatch — issue 6 in
  `doc/plan/00000009-phase-2-ai-self-play-training/peer-review.md`, deferred there
  explicitly until GPU enablement. That row should be updated to point here once
  this lands.
- **Unblocks, but does not perform, the throughput work.** The deferred phase-2
  strength-measurement work is gated on self-play throughput. A GPU is one of the
  candidate levers; this story makes the lever reachable and leaves pulling it,
  and measuring the result, to a later conversation.
- **Does not touch `game-engine-core`.** The pinned dependency is unchanged. The
  device crossing is handled at the seams this repository owns.

## Noted ideas (optional, not acceptance criteria)

- **Batched inference at the search seam.** Almost certainly where a GPU would
  actually pay, and equally certainly a larger change — it needs the shared
  engine to be able to ask for several evaluations at once. Named here so it is
  not mistaken for something this story delivers.
- **Enabling mixed precision / TF32 for throughput.** A cheap knob once there is
  a baseline to compare against, and meaningless before one exists. This story
  only requires that the setting be known and recorded, not that it be turned on.
- **Splitting self-play and learning across separate machines.** The
  non-determinism analysis above has a useful corollary: such a split would
  exchange weights and training samples, not a replayable random stream, so the
  workers would *not* need identical hardware. Two workers producing different
  games is data diversity rather than an error, and weights move as fp32 state
  dicts, which is a bit-exact transfer. What would have to match is semantics —
  model code, the engine I/O spec already stamped on every checkpoint, and the
  ruleset — not silicon. The one thing lost is reproducing a specific run's exact
  game history on different hardware, which is why the environment facts are
  recorded per run and why reproduction is better aimed at a saved position than
  at a whole run.
- **Deterministic cuDNN algorithm selection.** Would tighten same-device
  reproducibility guarantees at some cost; only worth it if run-to-run CUDA
  variation proves to be a nuisance in practice.
- **A GPU-enabled CI or remote training target.** Out of reach and out of scope,
  but the parameterized image is the thing that would make it possible.

## Out of scope

- **Any performance claim, target, or measurement.** No speedup is asserted, no
  benchmark is required, no CPU-versus-GPU timing comparison is part of
  acceptance. The developer will measure afterwards. (Keeping story 00000029's
  existing apparatus truthful under CUDA is a separate obligation — it is about
  not degrading what we already have, not about producing a new number.)
- **Any optimization** undertaken to make the GPU look good — batching, precision
  changes, transfer elimination, model-size retuning.
- **Non-CUDA accelerators** (Apple MPS, ROCm) and multi-GPU or distributed
  training. A single CUDA device is the whole target.
- **Changes to `game-engine-core`**, including adding device support to the
  shared training loop.
- **Retraining, retuning, or rerunning anything.** No hyperparameter changes and
  no new training runs beyond what verification needs; existing checkpoints stay
  valid.
- **GPU memory profiling, kernel-level profiling, and OOM-driven batch-size
  tuning.**

## Acceptance criteria

- **Two container configurations exist**, selectable when opening the repository
  in a container, with CPU the default and behaviourally unchanged from today.
  The CUDA configuration installs GPU-capable torch wheels of the *same* torch
  version and passes the host GPU through, so `torch.cuda.is_available()` is true
  inside it and the installed torch reports a CUDA build after container creation
  completes.
- **A single device decision governs the whole stack.** It defaults to what the
  container provides, can be explicitly overridden at the entry points that run
  games and training, errors clearly when CUDA is explicitly requested and
  unavailable, and is reported both to the developer and into the run's record as
  the device actually used.
- **A full run completes on CUDA** — self-play, training, checkpoint write, and
  resume — with no device-mismatch error, and a game plays through the learned
  engine on the GPU.
- **No tensor site is left device-assuming.** The policy-loss target, the value
  target, the encoded-position path in and out of the evaluator, and the samples
  held between self-play and training all resolve to the run's device, with
  samples stored device-independently rather than pinned to GPU memory.
- **Checkpoints are portable across configurations** — one written under CUDA
  loads and resumes in the CPU container, and one written under CPU loads and
  resumes in the CUDA container. The device is not a compatibility stamp.
- **The test suite passes in both containers**, with GPU-requiring tests skipped
  rather than failed when no GPU is present.
- **Cross-device numerical agreement is demonstrated where it is meaningful** —
  the same position encodes identically and the same forward pass agrees within a
  documented tolerance across devices — and the fact that seeded whole-run
  divergence between devices is expected is written down.
- **The reduced-precision (TF32) setting is explicit and recorded** in the run's
  environment facts rather than inherited from torch's architecture- and
  version-dependent defaults, and the tolerance claimed above is consistent with
  it.
- **Story 00000029's timing report still means under CUDA what it means under
  CPU** — GPU work is attributed to the region that caused it rather than to
  whichever region later blocks, the CPU path is unaffected, and the choice of
  which region boundaries synchronize is recorded with its reasoning.
- **The setup is documented** in `CONTRIBUTING.md`: how to choose a
  configuration, what the host must provide for the CUDA one, the image-size
  trade-off, and how to force a device explicitly.

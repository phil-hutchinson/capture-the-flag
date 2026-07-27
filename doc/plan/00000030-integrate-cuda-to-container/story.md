# Story: CUDA in the container — a GPU-capable development environment

## Summary

Make a GPU *reachable* from the development environment. Today the container
installs CPU-only torch wheels by deliberate choice (`.devcontainer/Dockerfile`:
"the container has no GPU passthrough, and the default Linux wheels pull in the
multi-GB CUDA stack") and is started with no device passthrough, so there is no
way to try a GPU at all. This story delivers:

- **Two container configurations** — the existing CPU one, which stays the
  default, and a CUDA one that installs GPU-capable torch wheels of the same
  version and passes the host GPU through.
- **One place that answers "what device, at what precision"** — a resolution
  module with an explicit fp32 pinning, and a run record that states the device
  the run actually used rather than the one the machine merely has.

This story is about **reachability, not use**. It stops at the point where
`torch.cuda.is_available()` is true inside the container and the suite is green
there. It does not put a single tensor on a GPU.

### Why the code work is not here

This story originally carried the device through the whole pipeline — the
network's forward pass, the evaluator's decode, both loss functions, checkpoint
placement, and the timing regions. That scope was cut deliberately, and the two
commits that had begun it were dropped rather than kept.

The reason is that the seams turned out to be in the wrong repository. The shared
`TrainingLoop._train_batch` stacks its batch and builds its value targets with no
device argument, and the shared `NeuralNetworkEvaluator.evaluate_position` hands
the model whatever `encode_position` returned. Neither can be told a device. Work
on our side of those seams — a `forward` that relocates its own input, a decode
that copies back, losses that chase the logits' device — is a set of one-sided
compensations for an interface that should carry the device itself. Written now,
each one becomes something to unpick when the shared engine grows real device
support, which is the change that is actually wanted.

So the ordering is: make the GPU reachable (this story), fix the seams in
`game-engine-core`, then make this repository device-aware against an interface
that supports it. The middle step is what the two dropped commits were working
around, and it is cheaper to do it once than to build the workaround and remove
it.

## Motivation

Every part of the pipeline that could benefit from a GPU is in place — a
configurable-width residual trunk (story 00000026), a self-play/training loop
(story 00000009), and instrumentation that can say where the time goes (story
00000029) — and none of it has ever executed a single CUDA kernel. The gate is
not the code being unready; it is that the environment offers no way to try.

A GPU-capable container is infrastructure, and it is worth having before the work
that consumes it. Once it exists, the upstream engine changes can be developed
and tested against real hardware instead of theorized about, and every later
experiment — batched inference, a wider trunk, longer training runs — can use it
without relitigating build arguments, wheel indexes, and driver passthrough.

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
  intends to run later.
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

### One place that answers the device question

There should be a single module that turns a requested device into a concrete
one, so that when the pipeline does become device-aware it has somewhere to ask
rather than a scattering of independent decisions to make.

- **`auto` takes what the container provides.** CPU where torch cannot see a GPU,
  CUDA where it can.
- **An explicit request that cannot be honoured is an error, not a downgrade.**
  Asking for CUDA where CUDA is unavailable must fail with a clear, named
  message. Silently falling back would let a run that was supposed to exercise
  the GPU quietly not do so.
- **Precision is pinned, not inherited.** torch's reduced-precision (TF32)
  defaults are architecture- and version-dependent, and TF32 is a real precision
  reduction — convolution and matmul inputs truncated to a 10-bit mantissa,
  relative error from roughly `1e-7` to roughly `1e-3`. The trunk is all
  convolutions, so this is not a marginal setting. Both containers must compute
  in fp32 by explicit choice, and the setting must be recorded.

### A run record that does not overclaim

`run_environment.py` reports `torch_device` and `cuda_device_name`. It derived
them from availability, which would have named a GPU for a CPU-forced run in the
CUDA container. It must instead state the device the run actually used.

That obligation binds in both directions, and after this story's scope cut it is
the second direction that matters: **nothing in this repository places a tensor
on a GPU**, so a run started in the CUDA container computes on the CPU and its
record must say `cpu`. Recording the `auto` resolution would name a device that
ran nothing — the same defect, pointed the other way. The pipeline's device is
therefore a single hardcoded answer with one call site, so the story that makes
the pipeline device-aware has one thing to replace rather than four assumptions
to hunt down.

### The suite green in both containers

The default container must stay green, and the CUDA container must be usable:
`pytest`, `pyright`, and `ruff` all clean in each. Tests that need a GPU skip
rather than fail when there is none.

## Relationship to other work

- **Consumes** story 00000029's run record and environment facts, which already
  have a place for the device and the GPU name.
- **Blocks nothing, unblocks the upstream work.** Device support in
  `game-engine-core` can now be developed against real hardware.
- **Leaves story 00000009's peer-review issue 6 deferred.** The policy-loss
  device mismatch is a real defect, but fixing it now means writing a
  compensation for a seam that is about to change. That row stays open and
  points here for why.
- **Does not touch `game-engine-core`.** The pinned dependency is unchanged.

## Deferred to the pipeline-integration work

Named here so they are not mistaken for things this story dropped silently. Each
was specified in this story's original scope and is still wanted:

- **Every tensor on the same device** — the encode → forward → decode path, the
  policy-loss target, the value loss, and device placement for networks built,
  loaded, resumed, and played.
- **Device selection at the entry points** — a `--device` option on the training
  runner, the batch runner, and the timing benchmark, so CPU can be forced inside
  the CUDA container for comparison and bisection.
- **Checkpoint portability across devices**, with the device explicitly *not*
  becoming a compatibility stamp alongside the engine-spec and architecture
  stamps.
- **Cross-device numerical agreement**, demonstrated where it is meaningful — the
  same position encoding identically, the same forward pass agreeing within a
  tolerance the fp32 pinning justifies — together with the written-down fact that
  seeded *whole-run* divergence between devices is expected rather than a bug.
  A convolution is a composite of many operations and nothing constrains how it
  is decomposed; floating-point addition is not associative, so a tree reduction
  across GPU threads and a sequential CPU reduction disagree in the last bits
  while both are correctly rounded. One flipped selection at one search node is
  enough to send two seeded runs into entirely different games.
- **Honest timing under asynchronous execution** — GPU kernel launches are
  asynchronous, so a region wrapped around a forward pass measures the time to
  *queue* the work. The cost is paid at the next point something blocks, which in
  this pipeline is the read-back for decoding, so story 00000029's report would
  state in good faith and with correct arithmetic that decoding the policy is the
  expensive part of evaluation. This is inert until something actually runs on a
  GPU, but it comes due the moment one does.

## Out of scope

- **Putting any tensor on a GPU**, and therefore any device-mismatch fix,
  device threading, or GPU-vs-CPU numerical comparison (see above).
- **Any performance claim, target, or measurement.** No speedup is asserted and
  no benchmark is required.
- **Non-CUDA accelerators** (Apple MPS, ROCm) and multi-GPU or distributed
  training. A single CUDA device is the whole target.
- **Changes to `game-engine-core`.** They are the next story, not this one.
- **Retraining, retuning, or rerunning anything.** Existing checkpoints stay
  valid; nothing about how they are produced changes.

## Acceptance criteria

- **Two container configurations exist**, selectable when opening the repository
  in a container, with CPU the default and behaviourally unchanged from today.
  The CUDA configuration installs GPU-capable torch wheels of the *same* torch
  version and passes the host GPU through, so `torch.cuda.is_available()` is true
  inside it and the installed torch reports a CUDA build after container creation
  completes — from a no-cache build, with no manual repair step.
- **A device-resolution module exists** that honours `auto`, `cpu`, and `cuda`,
  raises a clear named error for an unavailable explicit `cuda`, and pins fp32
  precision explicitly on both devices.
- **The run record states the device actually used.** In the CUDA container, with
  no pipeline code on the GPU, a run records `cpu` — not the device the machine
  happens to have. The TF32 setting is recorded alongside it, read back from
  torch rather than asserted.
- **The test suite passes in both containers**, with GPU-requiring tests skipped
  rather than failed when no GPU is present. `pyright` and `ruff` clean in both.
- **The setup is documented** in `CONTRIBUTING.md`: how to choose a
  configuration, what the host must provide for the CUDA one, the image-size
  trade-off, and the explicit statement that the CUDA container does not yet make
  anything run on the GPU.

# Implementation Plan: CUDA in the container

See [story.md](story.md) for full context. This plan makes a GPU reachable from
the development environment and stops there: a second container configuration, a
single place that resolves a device, and a run record that does not claim to have
used one when it has not.

## Approach

**The device crossings are not on our side of the seam.** Two pieces of
third-party code hand the network a tensor and neither can be told a device:
`NeuralNetworkEvaluator.evaluate_position` calls `self._model(...)` with whatever
`encode_position` returned, and `TrainingLoop._train_batch` stacks the batch and
builds its value targets with no `device=` argument. Anything this repository does
about that is a one-sided compensation for an interface that should carry the
device itself — a `forward` that relocates its own input, a decode that copies
back, losses that chase the logits' device. Each would be unpicked when the shared
engine gains real device support. So the pipeline work waits for that change, and
this plan delivers only the environment it will be developed against. The story's
[Deferred](story.md#deferred-to-the-pipeline-integration-work) section holds what
was cut, in the detail it was originally specified in.

**Nothing here runs on a GPU, and the record must say so.** That is the one
non-obvious consequence of the scope cut. Step 3 changed the environment facts
from an availability check to the run's resolved device precisely so a CPU-forced
run in the CUDA container would not be recorded as CUDA. With no pipeline code on
the GPU, resolving `auto` for the record recreates that defect pointed the other
way: a run in the CUDA container would record a device that executed nothing.
Step 4 closes it.

**The container comes first**, because it has no code dependency and every later
question — including the upstream engine work this unblocks — needs the GPU
reachable before it can be asked.

Steps 1–3 have landed. Step 4 is implemented and its automated test passes, but
its manual GPU verification is outstanding and it is not yet committed. Step 5 has
not been started.

---

### Step 1 — The CUDA container configuration ✅

Parameterize the existing `.devcontainer/Dockerfile` so the torch wheel index is
a build argument, defaulting to the CPU index it hard-codes today. Add a second
dev container configuration in its own subdirectory that reuses that same
Dockerfile (with the CUDA index, and `.devcontainer` as the build context so both
configurations resolve the same one — the Dockerfile `COPY`s nothing, and a
repository-root context would ship the whole workspace, training artifacts
included, to the daemon on every build), requests GPU passthrough from the host,
and keeps everything else — the env-file handling, the Claude Code volume and its
`initializeCommand`, the `postCreateCommand`, the VS Code extensions and settings
— identical to the CPU one. The existing configuration stays exactly where it is
and keeps its current behaviour, so it remains the default offered when reopening
the repository in a container.

**Everything this step adds is declarative infrastructure, checked in.** The whole
difference between the two configurations lives in the Dockerfile, the two
`devcontainer.json` files, and the build argument that connects them — no setup
script to run afterwards, no manual `pip install` to repair a wheel, nothing a
developer has to remember. A clone of this repository, built from scratch with no
Docker cache, must come up fully working in either configuration. The one existing
exception stays as it is: `devcontainer.env` is gitignored personal configuration,
already created by the existing `initializeCommand` before the container starts.

That standard is what makes the wheel-clobbering risk from the story a blocking
concern rather than a footnote. `postCreateCommand` runs
`pip install --editable '.'`, which resolves `game-engine-core[learning]` and its
torch dependency *after* the image layer has installed the chosen wheel. If that
resolution replaces the CUDA build, the fix belongs in the image or the dependency
declaration — not in a step the developer performs by hand.

Depends on: nothing (first step). Everything else depends on it.

Verification (manual): **Before building anything**, confirm the host can do this
at all — `nvidia-smi` on the *host* (not in the container) should list a GPU. Then
reopen the repository in the CUDA configuration and run
`python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`:
the version must match the CPU container's, `torch.version.cuda` must be a version
rather than `None`, and availability must be `True`. Reopen in the CPU
configuration and confirm the same command still reports a `+cpu` build — the
default path is unchanged. Then rebuild each configuration **without cache** and
run the same command immediately, with no manual steps in between; both must come
up correct on the first try, and `pytest` must pass in each.

### Step 2 — Device and precision resolution ✅

Add a small module that turns a requested device (`auto`, `cpu`, `cuda`) into a
concrete torch device, and that pins precision. `auto` resolves to CUDA when it is
available and CPU otherwise; an explicit `cuda` request that cannot be honoured
raises a clear, named error rather than downgrading silently. The same module
disables reduced-precision (TF32) matmul/convolution paths so both configurations
compute in fp32 regardless of torch's architecture- and version-dependent
defaults, and exposes what it resolved — device and precision setting — for the
run record to consume.

Nothing calls this yet; it is scaffolding, introduced separately from the
behaviour that uses it.

Depends on: nothing in the code (Step 1 only for exercising the CUDA branch).

Verification (automated): `pytest tests/test_device.py`. Cover: `auto` resolves to
CPU when CUDA is unavailable; explicit `cpu` is honoured everywhere; explicit
`cuda` raises a named error when unavailable; and — skipped without a GPU — `auto`
resolves to CUDA when one is present. Also assert the precision flags read back as
pinned after resolution.

### Step 3 — Record the device actually used ✅

`run_environment._torch_compute_facts` reported `cuda` whenever CUDA was merely
*available*, which after Step 1 would misreport any CPU-forced run in the CUDA
container. Change the environment record to state the device the run resolved and
is actually using, along with the precision setting, keeping the existing
best-effort discipline (a missing fact yields `None`, never a failed run). The GPU
name continues to be recorded when the device is CUDA.

Depends on: Step 2 (it is what supplies the resolved device).

Verification (automated): `pytest tests/test_run_environment.py` — the facts
report the device passed to them rather than what is available, including the case
of a CPU-resolved run on a CUDA-capable machine (constructible without a GPU by
passing the resolved value in).

### Step 4 — The recorded device tells the truth about this repository

Step 3 left the four run-record call sites resolving `auto`, on the assumption
that the pipeline would shortly be placed on the resolved device. It will not be,
in this story. Give the pipeline's device a single named answer — CPU,
unconditionally — and have every run record go through it, so a run in the CUDA
container records the device that actually computed rather than the one the
machine happens to have.

The hardcoding is the point, not a shortcut: there is no honest way to *derive*
this answer, because the fact being recorded is a property of the code rather than
of the machine. One call site, documented as the thing the pipeline-integration
story replaces with the run's real choice.

Depends on: Step 3 (which is what introduced the call sites).

Verification (automated): `pytest tests/test_device.py` — the pipeline's device is
CPU whether or not a GPU is reachable, with the GPU case constructible without
one.

Verification (manual, GPU only): in the CUDA container, run the timing benchmark
briefly and confirm the printed machine facts and the written record both name
`cpu`, with no `cuda_device_name`, while `torch.cuda.is_available()` in the same
container is `True`.

### Step 5 — Documentation and README check

Document the setup in `CONTRIBUTING.md`: how to choose between the two
configurations, what the host must provide for the CUDA one, the image-size
trade-off that keeps CPU the default, and — the part a reader will otherwise get
wrong — that opening the CUDA configuration does not currently make anything run
on the GPU. It makes one reachable; the pipeline follows in a later story.

Then verify `README.md` is still accurate given the story's changes — the
environment section and any runner invocations it shows are the likely touch
points — using `/update-readme`, which reviews the branch diff and updates it if
warranted.

Finally, leave story 00000009's peer-review issue 6 (the policy-loss device
mismatch) deferred, and update that row to point here: GPU enablement landed, but
the fix waits on device support in the shared engine rather than being written as
a compensation for its absence.

Depends on: Steps 1–4 (documents what they built).

Verification (manual): follow the `CONTRIBUTING.md` instructions from scratch to
open the CUDA configuration; it should work as written without needing anything
the document does not mention, and a developer following it should not come away
expecting a training run to use the GPU.

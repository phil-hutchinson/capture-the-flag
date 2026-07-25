# Implementation Plan: CUDA in the container

See [story.md](story.md) for full context. This plan adds a second, GPU-capable
container configuration alongside the CPU default, then makes the device an
explicit, threaded-through choice that the whole pipeline honours.

## Approach

Four findings from reading the code shape every step below.

**The device crossing is owned at three seams, all of them ours.** Two pieces of
third-party code hand the network a tensor and neither can be told a device:
`NeuralNetworkEvaluator.evaluate_position` calls `self._model(encoded.unsqueeze(0))`
with whatever `encode_position` returned, and `TrainingLoop._train_batch` stacks
the batch and builds its value targets with no `device=` argument. Both funnel
into the *model's* `forward`. So making `CtfCrn.forward` responsible for placing
its own input onto its own device fixes both call paths at once, and is what
allows the pinned dependency to stay untouched. The other two seams are
`decode_policy` (the policy egress) and the two loss functions — both ours, both
injectable.

**Tensors are built on the CPU and transferred once, whole.** `encode_position`,
`decode_policy`'s mask, and `ctf_policy_loss`'s dense target are all filled by
per-element writes in Python loops, and on a GPU each such write would be a
separate kernel launch. Each of these therefore stays a CPU-side build, and only
the finished tensor crosses to the device.

**Device-independent samples come for free, and must be kept that way.** Because
encoding stays on the CPU, the `TrainingSample` tensors the collector accumulates
across a generation are CPU tensors with no further work. This is a property to
protect with a test, not a thing to build.

**The timing core stays torch-free.** `instrumentation/timing.py` is a
shared-library migration candidate and may not know about this game; it should
not learn about torch either. The synchronization that Step 10 needs therefore
belongs at the `CtfCrn` seam, which already owns the device, not inside the
timing machinery.

One ordering decision follows from all this: **the container comes first.**
It has no code dependency and could sit anywhere, but every subsequent step's
real verification is "does this work on a GPU," and that question cannot be asked
until the GPU is reachable. Building it first means steps 4–11 are each verified
on the hardware they exist for, rather than accumulating skipped tests that all
come due at the end.

---

### Step 1 — The CUDA container configuration

Parameterize the existing `.devcontainer/Dockerfile` so the torch wheel index is
a build argument, defaulting to the CPU index it hard-codes today. Add a second
dev container configuration in its own subdirectory that reuses that same
Dockerfile (with the CUDA index and the repository root as build context),
requests GPU passthrough from the host, and keeps everything else — the env-file
handling, the Claude Code volume and its `initializeCommand`, the
`postCreateCommand`, the VS Code extensions and settings — identical to the CPU
one. The existing configuration stays exactly where it is and keeps its current
behaviour, so it remains the default offered when reopening the repository in a
container.

**Everything this step adds is declarative infrastructure, checked in.** The
whole difference between the two configurations lives in the Dockerfile, the two
`devcontainer.json` files, and the build argument that connects them — no setup
script to run afterwards, no manual `pip install` to repair a wheel, nothing a
developer has to remember. A clone of this repository, built from scratch with no
Docker cache, must come up fully working in either configuration. The one
existing exception stays as it is: `devcontainer.env` is gitignored personal
configuration, already created by the existing `initializeCommand` before the
container starts.

That standard is what makes the wheel-clobbering risk from the story a blocking
concern rather than a footnote. `postCreateCommand` runs
`pip install --editable '.'`, which resolves `game-engine-core[learning]` and its
torch dependency *after* the image layer has installed the chosen wheel. If that
resolution replaces the CUDA build, the fix belongs in the image or the
dependency declaration — not in a step the developer performs by hand.

Depends on: nothing (first step). Every later step that needs GPU verification
depends on this.

Verification (manual): **Before building anything**, confirm the host can do this
at all — `nvidia-smi` on the *host* (not in the container) should list a GPU. The
current container has no passthrough (`/dev/dxg` and `/usr/lib/wsl/lib` are both
absent) so this has never been exercised. Then reopen the repository in the CUDA
configuration and run
`python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`:
the version must match the CPU container's, `torch.version.cuda` must be a
version rather than `None`, and availability must be `True`. Reopen in the CPU
configuration and confirm the same command still reports a `+cpu` build — the
default path is unchanged.

Then verify the from-scratch guarantee, which is the part a cached rebuild will
hide: rebuild each configuration **without cache** and run the same command
immediately, with no manual steps in between. Both must come up correct on the
first try. `pytest` should pass in each as well, confirming the editable install
completed and the workspace is importable.

### Step 2 — Device and precision resolution

Add a small module that turns a requested device (`auto`, `cpu`, `cuda`) into a
concrete torch device, and that pins precision. `auto` resolves to CUDA when it
is available and CPU otherwise; an explicit `cuda` request that cannot be honoured
raises a clear, named error rather than downgrading silently. The same module
disables reduced-precision (TF32) matmul/convolution paths so both configurations
compute in fp32 regardless of torch's architecture- and version-dependent
defaults, and exposes what it resolved — device and precision setting — for the
run record to consume.

Nothing calls this yet; it is scaffolding, introduced separately from the
behaviour that uses it.

Depends on: nothing in the code (Step 1 only for exercising the CUDA branch).

Verification (automated): `pytest tests/test_device.py`. Cover: `auto` resolves
to CPU when CUDA is unavailable; explicit `cpu` is honoured everywhere; explicit
`cuda` raises a named error when unavailable; and — skipped without a GPU —
`auto` resolves to CUDA when one is present. Also assert the precision flags read
back as pinned after resolution.

### Step 3 — Record the device actually used

`run_environment._torch_compute_facts` currently reports `cuda` whenever CUDA is
merely *available*, which after Step 1 would misreport any CPU-forced run in the
CUDA container. Change the environment record to state the device the run
resolved and is actually using, along with the precision setting, keeping the
existing best-effort discipline (a missing fact yields `None`, never a failed
run). The GPU name continues to be recorded when the device is CUDA.

Depends on: Step 2 (it is what supplies the resolved device).

Verification (automated): `pytest tests/test_run_environment.py` — the facts
report the device passed to them rather than what is available, including the
case of a CPU-resolved run on a CUDA-capable machine (constructible without a GPU
by passing the resolved value in).

### Step 4 — The network places its own input

Make `CtfCrn.forward` move its input to the device its parameters live on. This
is the single ingress both call paths funnel through, so after this step a
GPU-resident network can be driven by the shared evaluator and the shared
training loop without either of them knowing about devices. `CtfCrn` is an
`nn.Module`, so `.to(device)` already works on it; this step is about the input
side.

Depends on: Step 2 (for a device to move to).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_crn.py` —
a network fed a CPU tensor returns outputs on the network's own device, and the
CPU-to-CPU case is unchanged. The cross-device half is skipped without a GPU.

Verification (manual, GPU only): in the CUDA container, build a small network,
`.to("cuda")` it, and run one `evaluate_position` through `CtfNNEvaluator` — it
should reach `decode_policy` rather than failing in the shared base class, which
is the proof that the shared `evaluate_position` path no longer needs changing.
It will still fail *inside* decode until Step 5.

### Step 5 — Policy decoding returns to the CPU

Bring the policy logits back to the CPU once, at the top of `decode_policy`, and
leave the four existing phases untouched below it. Those phases build a mask by
per-element writes, then read probabilities back one legal ply at a time via
`.item()` — all work that belongs on the CPU. One transfer of one tensor replaces
what would otherwise be thousands of tiny device round trips.

Depends on: Step 4 (which is what can now deliver GPU-resident logits).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_nn_evaluator.py`
— decoding produces the same distribution as before for CPU logits, and (skipped
without a GPU) an identical distribution for the same logits on CUDA.

Verification (manual, GPU only): the Step 4 manual check now completes and
returns a `PositionEvaluation` with a value and a legal-ply distribution.

### Step 6 — The policy loss target reaches the logits' device

Keep `ctf_policy_loss` building its dense target on the CPU — the scatter loop
over each sample's visit distribution must stay there — and move the finished
tensor onto the logits' device immediately before the elementwise multiply
against the log-probabilities.

This is the site raised as issue 6 in
`doc/plan/00000009-phase-2-ai-self-play-training/peer-review.md` and deferred
there until GPU enablement. Note that the remedy recorded in that row — passing
`device=policy_logits.device` to the `torch.zeros` the scatter loop then writes
into — would put the per-element writes on the device, so it is not the fix taken
here; that row should be updated to point at this story's resolution.

Depends on: Step 4 (logits can now be on a device other than the CPU).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_policy_target.py`
— the loss value for CPU inputs is unchanged, and (skipped without a GPU) the
loss computes without error and agrees within tolerance when the logits are on
CUDA.

### Step 7 — A device-correct value loss

`TrainingLoop` is currently constructed in `ctf_training.py` with only a policy
loss, so it falls back to the default `F.mse_loss` — which would compare
GPU-resident predictions against the CPU value targets the loop builds
internally. Supply an explicit value loss that places the target on the
predictions' device before scoring, and inject it at construction. It must remain
mean-reduced: the loop weights each batch's loss by its sample count when
averaging an epoch, which is only correct for a mean.

Depends on: Step 4 (predictions can now be on a device); Step 6 (completes the
pair of losses, so training can be run end to end at the next step).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_training.py`
— the injected loss matches `F.mse_loss` on CPU inputs (so nothing about CPU
training changes), and (skipped without a GPU) scores GPU predictions against CPU
targets without error.

### Step 8 — Thread the device through training and play

Carry a resolved device through the paths that build or load a network:
`train_generations` and its resume counterpart move the freshly-built or
checkpoint-loaded network onto it, `load_network` keeps loading with
`map_location="cpu"` and then moves, and the player-building path does the same
so a checkpoint can be played on either device.

Two decisions to hold to here:

- **The device is not a `TrainingConfig` field and does not enter
  `run-config.json`.** Every field there is fixed for the life of a run and
  rebuilt from on resume; the device is a per-invocation choice, and a run
  resumed on different hardware must be free to use it. It is recorded in the
  per-invocation environment facts (Step 3) instead.
- **The device is not a checkpoint stamp.** The existing spec and architecture
  stamps gate compatibility; the device a checkpoint was trained on says nothing
  about whether its weights can be loaded, and adding it would break exactly the
  portability the story requires.

Depends on: Steps 4–7 (the whole forward/loss path must be device-correct before
a network is actually placed on a GPU); Step 2 (the resolved device).

Verification (automated): `pytest tests/engines/neural_network/test_ctf_checkpoint.py`
`tests/engines/neural_network/test_ctf_training_run.py` — a checkpoint saved from
a network on one device loads on the other (the GPU direction skipped without a
GPU), and `run-config.json` gains no device field.

### Step 9 — Device selection at the entry points

Add a device option to the three runners that drive networks — the training
runner, the batch runner, and the timing benchmark — defaulting to `auto` so the
container's configuration decides and nothing needs restating. An explicit
setting overrides it, which is what makes CPU forceable inside the CUDA container
for comparison and bisection.

Depends on: Step 8 (something to pass the choice to).

Verification (manual): run a short seeded training run — a couple of generations
at a small search budget — with `--device cpu` and confirm it completes and that
the resulting `timings.json` names `cpu`. In the CUDA container, repeat with
`--device cuda` and confirm the record names `cuda` and the GPU. Then confirm
`--device cuda` in the CPU container fails immediately with the named error from
Step 2 rather than running on the CPU.

### Step 10 — Honest timing under asynchronous execution

GPU kernel launches are asynchronous, so the `network-forward` region currently
measures the time to *queue* the forward pass. The queued work is then paid for
at the next point something blocks — and in this pipeline that point is
identifiable: the shared `evaluate_position` converts the value tensor to a
Python float immediately after the forward pass, and Step 5's copy back to the
CPU does the same for the logits. Left alone, story 00000029's report would
attribute the network's cost to policy decoding, with correct arithmetic and
complete sincerity.

Add device-aware synchronization at the `CtfCrn` seam, where the device is
already known, so that the forward-pass region closes only once the work it
queued has actually happened. It must be inert on CPU — no added cost, no
behaviour change to the default configuration — and it must not put torch inside
`instrumentation/timing.py`, which stays game- and framework-agnostic for its
eventual migration. Consider whether the host-to-device and device-to-host
transfers deserve named regions of their own; they are real work that currently
has no line in the report.

Then record the decision: which boundaries synchronize, which do not, and what
the residual mis-attribution is. Synchronizing is not free — it stalls the
pipelining that a later throughput story will want — so the choice needs its
reasoning written down next to it, in the story folder alongside story
00000029's findings.

Depends on: Steps 5 and 9 (there must be a GPU run producing a report to correct).

Verification (manual, GPU only): take a timing report from a short seeded CUDA
run before and after this step. Before, `network-forward` is implausibly cheap
and `decode-policy` implausibly expensive; after, the cost sits under
`network-forward` and the tree still reconciles against total wall clock. Confirm
on the CPU side that a seeded run's report is unchanged from before the step.

### Step 11 — Cross-device reference comparison and a green suite in both containers

Add the comparison the story asks for: a set of positions whose encodings and
network outputs are computed on both devices and required to agree — encodings
identically, forward-pass outputs within a documented tolerance justified by the
fp32 pinning from Step 2. Sweep the suite for tests that silently assume CPU
tensors and make them device-explicit. GPU-requiring tests skip rather than fail
when no GPU is present, so the default container stays green.

Also assert the property the approach section flagged as free-but-fragile: the
samples a collector accumulates hold CPU tensors even when the network is on a
GPU.

Depends on: Steps 4–8 (there must be a working GPU path to compare against).

Verification (automated): `pytest` and `pytest -m slow` pass in the CPU container
with the GPU tests reported as skipped, and pass in the CUDA container with them
running. `pyright` and `ruff check .` clean in both.

### Step 12 — Documentation and README check

Document the setup in `CONTRIBUTING.md`: how to choose between the two
configurations, what the host must provide for the CUDA one, the image-size
trade-off that keeps CPU the default, and how to force a device explicitly. Then
verify `README.md` is still accurate given the story's changes — the environment
section and any runner invocations it shows are the likely touch points — using
`/update-readme`, which reviews the branch diff and updates it if warranted.

Update issue 6 in `doc/plan/00000009-phase-2-ai-self-play-training/peer-review.md`
from deferred to resolved, noting that the fix taken differs from the remedy that
row proposed (see Step 6).

Depends on: Steps 1–11 (documents what they built).

Verification (manual): follow the `CONTRIBUTING.md` instructions from scratch to
open the CUDA configuration and force a CPU run inside it; both should work as
written without needing anything the document does not mention.

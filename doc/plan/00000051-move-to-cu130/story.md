# Story 51: Move the CUDA container to `cu130`

## Summary

Point the CUDA configuration's `TORCH_INDEX_URL` build argument at
`https://download.pytorch.org/whl/cu130` instead of `cu126`, and rewrite the
rationale comment that justifies the choice.

The change is one line. The reason it is a story rather than a typo fix is that
the line it replaces is *correct-looking and wrong*, and the comment above it
explains the choice in terms that do not constrain what actually failed. Getting
the replacement rationale right is most of the work.

The pinned torch **version** does not move. Neither configuration's torch version
changes, because the two configurations differ by build and not by version — the
Dockerfile pins the version outside the build argument precisely so they cannot
drift.

## Why now

The development machine's GPU is an RTX 5060 Ti, compute capability **sm_120**.
The pinned `torch==2.13.0+cu126` ships compiled kernels for sm_50 through sm_90
and none for sm_120, so the CUDA container detects the card and cannot run a
single kernel on it:

```
NVIDIA GeForce RTX 5060 Ti with CUDA capability sm_120 is not compatible with
the current PyTorch installation.
```

`torch.cuda.is_available()` is `True` and the first allocation fails. This is
exactly the failure mode `CONTRIBUTING.md` already documents (the tensor check at
line 74, and the explanation beneath it), so the diagnosis needed no new
investigation — the repository had already written down what to look for and what
to change. What it could not know was which index to move to.

**This is not the `--device` story.** Nothing here makes the GPU do work; see
Out of scope.

## The comment being replaced

`.devcontainer/cuda/devcontainer.json` currently reads:

> cu126 rather than a newer index: it is the widest driver compatibility that
> still covers this developer's card, and torch's CUDA minor-version
> compatibility means a cu126 build runs on any CUDA 12.x-capable driver.

Both halves need to go, for different reasons:

- **"covers this developer's card"** was true when written and silently stopped
  being true when the card changed. Nothing about a card-specific justification
  signals that it has expired — the comment kept asserting its conclusion after
  its premise was gone.
- **The minor-version compatibility claim is true but irrelevant.** A cu126 build
  does run against any CUDA 12.x-capable *driver*. The driver was never the
  binding constraint. What binds is the set of compute capabilities the wheel was
  compiled for, and no driver version adds an architecture to a wheel that has no
  SASS for it and no PTX to JIT from.

Stating a true fact about the wrong constraint is what made this failure
surprising, so the replacement comment must name the constraint that actually
governs: **architecture coverage**.

## Decisions this story makes

### Record the selection rule, not just the chosen value

The comment states the rule used to pick an index, so it can be re-evaluated
against reality later instead of being a frozen assertion:

> Pick the newest `cuXXX` index that still ships the pinned torch version and
> whose CUDA version is at or below what `nvidia-smi` reports on the host.

A value alone is what went stale. A rule can be checked, and it tells the next
reader what would make the current answer wrong. `CONTRIBUTING.md:83` already
states the same rule loosely — "a CUDA build new enough for the card" — and is
tightened to match.

### `cu130`, and why not the two alternatives

The host driver is **591.44, reporting CUDA 13.1**. Of the indexes carrying torch
2.13.0, three are viable on sm_120:

| Index | sm_120 | torch 2.13.0 | vs. driver CUDA 13.1 |
|---|---|---|---|
| `cu126` | no | yes | fine — and useless, today's failure |
| `cu128` | yes | **absent** | — |
| `cu129` | yes | yes | below |
| **`cu130`** | **yes** | **yes** | **at or below** |
| `cu132` | yes | yes | above — needs minor-version forward compatibility |

- **`cu132` is rejected because it would repeat this story's own mistake.**
  Running a CUDA 13.2 build against a 13.1 driver relies on minor-version forward
  compatibility — the same class of assumption whose failure produced the comment
  being deleted. The pin belongs at or below what the driver reports.
- **`cu130` over `cu129`** because CUDA 13.x is where Blackwell is a primary
  target rather than a late addition, and because 12.x is further along the
  retirement path. That is not speculation: **`cu128` has no torch 2.13.0 at
  all**, which is what index attrition looks like in practice.

### No automated coverage, by nature

The change is a container image build argument. Nothing in the test suite can
observe it, and CI has no GPU. The testing strategy is manual — rebuild the CUDA
container, run the two checks already in `CONTRIBUTING.md` — and the
implementation plan carries that as a reminder rather than a test to run.

## Out of scope

- **Device-awareness — the `--device` flag, and any tensor placement.**
  `capture_the_flag/device.py` is not touched, no entry point gains a flag, and
  no model or tensor moves. That is a substantially larger story: which entry
  points take the flag, whether self-play and training may differ, what
  `timings.json` records, and the collector's `record_device`.
- **The torch version.** Stays `2.13.0`, pinned in `.devcontainer/Dockerfile`.
  Moving it would break the version parity between the two configurations that
  makes any comparison between them meaningful.
- **Python 3.14 and free-threading.** The Dockerfile pins 3.12. The index choice
  is deliberately checked for compatibility with a later free-threaded move —
  `cu130` publishes `cp314t` and `cp315t` wheels — but making that move is its
  own story. Worth noting for whoever picks it up: a `cp314t` wheel existing
  means torch imports and runs without the GIL, not that its internals are
  contention-free under many threads. That is a measurement, not an assumption
  this story is entitled to make.
- **The CPU configuration**, which is unaffected: it takes the Dockerfile's
  default CPU index and passes no device through.
- **Any performance claim.** See below.

## Likely follow-up stories

Sketches, not commitments — recorded so the out-of-scope list above reads as
sequencing rather than omission. Listed in dependency order.

1. **Make the pipeline device-aware (`--device`).** The story this one exists to
   unblock, and the only one that makes the GPU do work. Resolve
   `capture_the_flag/device.py` into a real flag on the training and batch entry
   points, place the model and its tensors, and decide whether self-play and
   training may sit on different devices. It also inherits scope story 45
   deliberately deferred to it: honouring `decode_policies`' host/device transfer
   contract, where `read-ply-probabilities` reads each legal ply back with a
   per-element `.item()` — which costs nothing on CPU and becomes a
   synchronisation per ply on an accelerator. `timings.json`'s `"torch_device"`
   starts saying something other than `cpu`, and `CONTRIBUTING.md`'s "What the
   CUDA configuration does not do" section is finally retired by this story
   rather than by this one.

2. **Exploit fleet width.** Story 45 adopted the v0.1.6 batch seams at width 1
   and vectorized nothing, inheriting the default scalar loop over
   `legal_plies` / `apply_plies` / `outcomes`. Overriding
   `BatchPositionProcessor` to do real vectorized work is what the fleet was for,
   and on a GPU it is what makes a wide batch worth assembling. Wants the device
   story first, so the win is measurable.

3. **Re-baseline above width 1.** The current instrumentation baseline is
   batch-of-one by construction, and story 45 established that call counts are
   only comparable between records taken at the same width. Once tensors are on a
   device and batches are wide, the repository needs a baseline that says what
   width it was taken at — and a documented recipe for taking one — before any
   throughput claim about the GPU means anything.

4. **Move to Python 3.14, free-threaded.** The Dockerfile pins 3.12. Keeping the
   GPU busy is expected to need concurrent self-play, which needs threads that
   actually run in parallel. `cu130` publishes `cp314t` and `cp315t` wheels, so
   this story's index choice does not stand in the way — but the open question is
   torch's own behaviour under many threads without the GIL, which has to be
   measured rather than assumed. Sequencing against items 2 and 3 is a judgement
   call: parallel self-play is another way to widen batches, so whichever lands
   first changes what the other is worth.

## The trap: this story makes nothing faster

After it lands, the CUDA container will be *able* to run kernels and will still
not run any, because nothing in this repository places a tensor on a GPU. Self
play, training and played games all still compute on the CPU, and a run's
`timings.json` will still correctly record `"torch_device": "cpu"`.
`CONTRIBUTING.md`'s "What the CUDA configuration does not do" section stays
accurate word for word and is **not** edited by this story.

This is stated up front because the obvious way to judge a story about GPU
wheels is to time a training run, and by that measure a completely successful
implementation looks like a failure. The acceptance criterion is that a kernel
runs at all.

## Acceptance criteria

- `TORCH_INDEX_URL` in `.devcontainer/cuda/devcontainer.json` is the `cu130`
  index, and the comment above it states the selection rule rather than a
  card-specific justification.
- After a CUDA container rebuild, `python -c "import torch; print(torch.zeros(1,
  device='cuda') + 1)"` prints a tensor. **This command fails today**; it is the
  whole point of the story.
- `python -c "import torch; print(torch.__version__, torch.version.cuda,
  torch.cuda.is_available())"` reports a `+cu130` build and `True`, with the
  torch version unchanged at `2.13.0`.
- No warning about compute capability or unsupported architecture is emitted on
  import or on first CUDA use.
- The torch version in the CUDA container still matches the CPU container's.
- `CONTRIBUTING.md:83`'s "new enough for the card" is tightened to the selection
  rule above. No other section of `CONTRIBUTING.md` changes — in particular, the
  claim that nothing here places a tensor on a GPU remains true.
- `pytest`, `ruff check .` and `pyright` are clean, which they will be trivially:
  no Python changes.

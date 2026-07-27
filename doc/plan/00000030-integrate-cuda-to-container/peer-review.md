# Peer Review — CUDA in the container

## Summary

The branch parameterizes the dev container's torch wheel index, adds a second
GPU-passthrough configuration alongside the CPU default, introduces a device and
precision resolution module, and makes the run record state the device that
actually computed rather than the one the machine has. The story was rescoped
mid-branch to container reachability only — the pipeline places nothing on a GPU
— and the rescope is documented, with the cut work preserved in the story's
Deferred section and the two commits that had begun it dropped rather than left
half-applied.

`pyright` reports 0 errors, 0 warnings, 0 informations. `ruff check .` reports
all checks passed.

The two substantive findings both stem from the same seam — `device.py` acquired
callers in modules that had deliberate properties the new import disturbs — and
neither was visible, because nothing runs on a GPU. That is what made them worth
filing: both were latent until the pipeline-integration story, and both are the
kind of defect that story would have inherited as pre-existing. Both are now
resolved; issue 1 was downgraded to Minor on review, with part of it withdrawn as
misattributed (see its Resolution).

All six issues are resolved. Issue 5 was resolved by adjusting the claim rather
than by verifying it, which is recorded in its Resolution row so the untested
assertion does not simply disappear.

## Comments

### Major

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 2 | Resolved | Fixed — `run_batch` resolves once at the top, before `timing_run`, and passes the result down to `report_timings`. Precision is now pinned for the run whether or not timing is enabled, and the recorded fact covers the games it describes. | [capture_the_flag/batch_runner.py#L137](../../../capture_the_flag/batch_runner.py#L137) | `pipeline_device()` pins the global TF32 flags as a side effect, and in `run_batch` it is called *after* `_play_batch` has finished — inside the record-writing block, at line 137, where the games completed at line 112. So `torch_tf32_allowed` describes the process only from the moment the record is written, contradicting `ResolvedDevice.tf32_allowed`'s own claim that "a recorded fact is only worth recording if it describes the process that ran." Worse, the call sits inside `if session is not None:`, so `--no-timing` skips precision pinning for the batch entirely. Inert today because the device is CPU and the flags do nothing there, but a GPU batch would run its convolutions under torch's inherited cuDNN TF32 default and then record `false`. `timing_benchmark.py` and both `ctf_training_run.py` entry points resolve before their work and are correct; this is the one that does not. | Resolve once at the top of `run_batch`, before `timing_run`, and pass the result down to `report_timings` — so precision is pinned for the run regardless of whether timing is enabled, and the recorded fact covers the games it describes. | `resolved_device=pipeline_device(),` |

### Minor

| # | Status | Resolution | Location | Comment | Suggested Change | Code Snippet |
|---|--------|------------|----------|---------|-----------------|--------------|
| 1 | Resolved | Downgraded from Major, and the finding partly withdrawn: the dead-fallback consequence was misattributed. torch is a hard dependency on `main` too, so `_import_torch_module`'s `ImportError` branch was already unreachable there — it carries a `# pragma: no cover` saying so — and this branch did not create that. What the branch does change is the cost deferral, and the blast radius is narrower than filed: `game_runner`, the human-facing terminal runner, does not pull the chain, so no interactive path got slower. Torch-always is the project's design (see `CONTRIBUTING.md`, "The `learning` extra … is a hard dependency"), so eager torch is accepted rather than worked around; the docstring was rewritten to stop claiming a laziness it no longer delivers, and the lookup kept for the best-effort discipline that is its remaining justification. | [capture_the_flag/run_environment.py#L22](../../../capture_the_flag/run_environment.py#L22) | The module-level `from .device import ResolvedDevice` defeats `run_environment`'s documented lazy-torch discipline. `device.py` imports torch at module scope, so importing `run_environment` — or `batch_runner`, which now imports `pipeline_device` the same way — eagerly imports torch. Verified: on `main`, `import capture_the_flag.batch_runner` leaves `torch` out of `sys.modules`; on this branch it pulls it in, at ~1.4s measured by `python -X importtime`. That is precisely the cost `_import_torch`'s docstring says a random-vs-random batch has no reason to pay, so the docstring no longer describes the module it documents. | Either restore laziness (`if TYPE_CHECKING:` for the annotation-only imports in `run_environment.py` and `timing_record.py`, a function-local import in `batch_runner.py`) or accept eager torch and rewrite the rationale so it stops claiming a property the code no longer has. | `from .device import ResolvedDevice` |
| 3 | Resolved | Fixed — both comments now describe `DEVICE_CHOICES` and the default request as the interface the pipeline-integration story will expose, rather than one that exists today. The assertions are unchanged: they still guard against a choice this module would reject as unknown. | [tests/test_device.py#L97](../../../tests/test_device.py#L97) | Two test comments describe an interface the rescope removed from scope. L97 says "`DEVICE_CHOICES` is what the entry points offer as their `--device` values", and L41 says "the entry points pass nothing when the developer says nothing, so the no-argument call has to be the one that takes what the container offers." No entry point offers a `--device` flag or calls `resolve_device()` with no argument — every production caller now goes through `pipeline_device()`. Step 5 fixed this same staleness in the `DeviceUnavailableError` message and the `DEVICE_CHOICES` docstring but did not sweep the tests. | Reword both to describe the constants as the interface the pipeline-integration story will expose, matching the note already added at `device.py#L52`. The assertions themselves are still worth keeping. | `# DEVICE_CHOICES is what the entry points offer as their `--device` values,` |
| 4 | Resolved | Fixed — the fixture moved to a new `tests/conftest.py` and is autouse suite-wide, so every module that reaches `device.py` (directly or through the environment facts) has its precision flags restored. Suite-wide rather than per-module because the files that mutate the flags are not obviously the ones that read them, which makes opting in per file a thing to forget. | [tests/test_run_environment.py#L19](../../../tests/test_run_environment.py#L19) | `resolve_device("cpu")` mutates process-global precision flags, and this module calls it twice with no cleanup. `test_device.py` has an autouse fixture restoring them precisely because they are global; this module leaves them pinned off for whatever runs next. Harmless in practice (it only ever sets the value the suite wants anyway) but it makes test outcomes order-dependent on a shared global. | Move the `restore_tf32_flags` fixture into `conftest.py` so both modules get it, rather than duplicating it or leaving this module uncovered. | `resolved = resolve_device("cpu")` |
| 5 | Resolved | Text adjusted rather than verified — disabling GPU support to test the failure path is not worth the disruption right now. The specific error string is gone; the paragraph now says only what follows from the configuration itself, that `--gpus all` makes GPU support a hard requirement so the container should be expected to fail at start rather than come up GPU-less. | [CONTRIBUTING.md#L49-L51](../../../CONTRIBUTING.md#L49) | The host-prerequisites paragraph asserts a failure mode that has not been exercised on this project: that Docker "refuses to start the container outright, with a `could not select device driver` error — it does not silently start one without a GPU." This is standard Docker behaviour for `--gpus all` without the NVIDIA container toolkit, but it is stated as an observed property of this configuration and the reader is invited to rely on it to disambiguate a failure. | Either verify it (temporarily disable GPU support and open the configuration) or soften to describe only what has been seen — that the configuration requires GPU support and will not start without it — without naming the specific error text. | `Without that support Docker refuses to start the container outright, with a` |
| 6 | Resolved | Fixed. | [capture_the_flag/device.py#L63](../../../capture_the_flag/device.py#L63) | Typo in `DeviceUnavailableError`'s docstring: "a environment problem". | "an environment problem". | `which is a environment problem, not a typo.` |

## Notes (not findings)

- **The plan includes a README check.** Step 5 covers it, and `README.md` was
  updated on this branch — one clause in the Development section noting the
  second configuration and stating that nothing runs on a GPU yet. The caveat is
  the right call: "a GPU-capable dev container" reads as a performance claim on
  its own.
- **Story and plan agree after the rescope**, including on the awkward part: the
  plan's Approach section explains why hardcoding the pipeline's device is the
  honest answer rather than a shortcut, and the story's Deferred section keeps
  the cut requirements at the detail they were originally specified in rather
  than summarizing them away. Story 00000009's peer-review issue 6 is correctly
  left `Deferred` with its reasoning updated, and the note that its own Suggested
  Change is not the fix to take is a useful thing to have written down.
- **`resolve_device`'s `auto` and `cuda` branches have no production caller** —
  only `pipeline_device` (with `cpu`) and tests reach them. This is deliberate
  scaffolding per the story and is called out there, so it is not filed as dead
  code, but it does mean the branch's most-tested module is its least-used one.
- **Verification coverage.** Steps 1, 4, and 5 carry manual verification that was
  performed; the CUDA container's suite run exercises the `requires_cuda` cases
  rather than skipping them. The story's "passes in both containers" criterion
  was confirmed in both.

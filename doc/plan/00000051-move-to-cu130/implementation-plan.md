# Story 51 — Implementation Plan

Six steps. Only one of them changes a line that affects the container image, and
everything after it depends on a rebuild the developer performs by hand.

## Handoff points

The plan has **one hard handoff**, at Step 3, and it is unusual enough to call out
before the steps themselves:

**This Claude session runs inside the CUDA container.** The installed torch is
`2.13.0+cu126` and the GPU is passed through, which only the CUDA configuration
does. So rebuilding the container tears down the environment the session is
running in — the session will be interrupted, not merely paused, and work resumes
in a new container with a new session. Steps 1–2 must therefore be committed
before the rebuild, or they are lost with the container.

Practically: Claude completes Steps 1–2 and stops. The developer commits,
rebuilds, runs the Step 3 checks, and reports the result. Claude picks up at
Step 4.

## Step 1 — Capture the pre-change failure

Record what the current container does, in the run that is about to become
unreachable. Run the two verification commands from `CONTRIBUTING.md` (lines 63
and 74) and keep their output — the version/availability line, and the tensor
allocation that fails together with the compute-capability warning torch emits on
first CUDA use.

Depends on: nothing. It comes first because it cannot be done later: after the
rebuild the `cu126` state is gone, and the story's headline acceptance criterion
is that a specific command *fails before and passes after*. Without the "before"
captured, Step 3 confirms that a command works but not that this story is what
made it work.

Verification (manual): The first command reports `2.13.0+cu126`, a CUDA version,
and `True`. The second raises rather than printing a tensor, and the output names
`sm_120` as incompatible. Both outputs are recorded in
[`baseline.md`](baseline.md), alongside the Step 3 outputs, so the before/after
pair lives in the repository rather than in a terminal. (The plan originally named
the peer review or a commit message; a dedicated file keeps the pair together and
leaves room for the architecture-list inspection Step 3 added.)

## Step 2 — Move the build argument and rewrite its rationale

In `.devcontainer/cuda/devcontainer.json`, point `TORCH_INDEX_URL` at the `cu130`
index, and replace the comment above it. The new comment states the **selection
rule** the story settles on — newest index that still ships the pinned torch
version, with a CUDA version at or below what `nvidia-smi` reports on the host —
and names architecture coverage, not driver compatibility, as the constraint that
governs. It must not justify the choice by reference to the current card, which is
the failure mode being removed.

Nothing else in the file changes, with one exception found in peer review: the
`postCreateCommand` comment named the installed build as `2.13.0+cu126`, and is
reworded not to name the index at all — the same staleness this story removes.
The Dockerfile is not touched: the torch version
stays pinned there, outside the build argument, so the two configurations cannot
drift apart on version.

Depends on: Step 1 (the before-state must be captured while it still exists).

Verification (manual, partial — and deliberately so): confirm the file is valid
JSON with comments as the devcontainer format expects, that the only changed
values are the index URL, its comment, and the `postCreateCommand` comment's
build reference, and that `git diff` shows no change to
`.devcontainer/Dockerfile` or to the CPU configuration. **Runtime verification is
not possible in this step** and is deferred to Step 3: a build argument is inert
until an image is built from it, so there is nothing to execute here. This is the
one step in the plan whose verification does not demonstrate runtime behaviour,
because the artifact it produces is an instruction to a build rather than code.

## Step 3 — HANDOFF: developer rebuilds the CUDA container and verifies

The developer commits Steps 1–2, then rebuilds using **Dev Containers: Rebuild
Container** with the **capture-the-flag (CUDA)** configuration. This pulls several
gigabytes of CUDA 13.0 wheels, so expect it to take a while. The session running
this plan does not survive it.

In the new container, run the same two commands from Step 1.

Depends on: Step 2 (the image is built from the argument it changed).

Verification (manual — this is the story's acceptance criterion):

1. `python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`
   reports a `+cu130` build, a CUDA version, and `True`. **The torch version must
   still read `2.13.0`** — if it moved, the version parity with the CPU container
   is broken and the change is wrong even though CUDA works.
2. `python -c "import torch; print(torch.zeros(1, device='cuda') + 1)"` prints a
   tensor. This is the command that fails today; it passing is the whole story.
3. No compute-capability or unsupported-architecture warning is printed, on
   import or on first CUDA use. A printed tensor accompanied by a warning is not
   a pass — it means something was JIT'd around a gap rather than the gap being
   closed.

**If the tensor command still fails**, the story's premise is wrong somewhere and
the plan stops rather than improvising. The most likely cause is that `cu130` does
not in fact ship `sm_120` kernels — the story infers that from torch's own
warning naming `cu130` as a fix, not from inspecting the wheel's architecture
list. The selection rule's next candidate is `cu132`, which the story rejected
only because it sits above the driver's reported CUDA 13.1; taking it would mean
accepting the minor-version forward-compatibility assumption, and that is a
decision to reopen with the developer, not one to make inside this step.

## Step 4 — Tighten the rule in `CONTRIBUTING.md`

`CONTRIBUTING.md:83` currently says the fix is an index "new enough for the card,"
which is the right rule stated too loosely to act on. Restate it as the selection
rule now sitting in the devcontainer comment, so the troubleshooting instruction
and the configuration agree and neither has to be reverse-engineered from the
other.

Depends on: Step 3. Writing this after the rebuild means it documents behaviour
that has been observed rather than behaviour that was intended — and if Step 3
had forced a different index, this is the prose that would have to say so.

Verification (manual): read the section back and confirm it names the same rule as
the devcontainer comment, and that a reader hitting the `sm_120` failure could
reach `cu130` by following it.

Scope note, recorded after peer review: the section also gains the
architecture-list check (`torch.cuda.get_arch_list()` against
`get_device_capability`), promoted from the Step 3 inspection in
`baseline.md`, and the rule gains the matching floor clause — the card's `sm_`
entry must be in the wheel's list. Without it the rule is ceiling-only and would
send a pre-Turing card to an index that has dropped its architecture. The
devcontainer comment states the same three-clause rule. Then confirm by inspection that the story's
deliberate non-edits are intact: **the "What the CUDA configuration does not do"
section is unchanged**, because it is still true word for word — nothing in this
repository places a tensor on a GPU.

## Step 5 — Confirm the image change moved nothing else

The rebuild swapped the CUDA runtime libraries underneath everything. Confirm the
repository still behaves exactly as before, and in particular that nothing
silently began using the GPU.

Run the type checker, the linter and the full suite. Then run a short training
run — one generation, a couple of games, the small network — and inspect the run
directory it produces.

Depends on: Step 3 (there is no new image to test before it).

Verification (manual and automated): `pyright` and `ruff check .` are clean and
`pytest` passes, all trivially — no Python changed in this story, so any failure
here is the image, not the code. The training run completes and writes a
checkpoint, and its `timings.json` still records `"torch_device": "cpu"`. That
last check is the one with teeth: it verifies the story's own claim that this
change makes nothing faster and moves no computation, so a later "the GPU isn't
being used" report is not mistaken for a regression from this story. Delete the
scratch run afterwards — `training-runs/` is gitignored, but leaving smoke runs
around invites treating one as a baseline.

## Step 6 — README check

Confirm `README.md` is still accurate given the change, updating it only if it
describes the container setup in terms this story alters. Run `/update-readme`,
which reviews the branch diff and updates the file if warranted.

Depends on: Steps 2 and 4 (the full prose diff must exist to review).

Verification (manual): either `README.md` is updated to match, or it is confirmed
to need no change. A no-change outcome is the expected one — the README is not
where the index is documented — and recording that it was checked is the point.

## Coverage against the story

| Surface the story names | Owning step |
|---|---|
| `TORCH_INDEX_URL` → `cu130` | 2 |
| Rationale comment replaced with the selection rule | 2 |
| Tensor allocation succeeds; no arch warning | 3 |
| torch version unchanged at `2.13.0`; parity with CPU config | 3 |
| `CONTRIBUTING.md:83` "new enough for the card" tightened | 4 |
| "What the CUDA configuration does not do" left unchanged | 4 (verified, not edited) |
| `timings.json` still records `cpu` | 5 |
| `pytest` / `ruff` / `pyright` clean | 5 |
| `README.md` | 6 |

Two story items are covered by having no step, which is the correct treatment
rather than an omission: `capture_the_flag/device.py` and the `--device` flag
belong to the follow-up story the story text names, and **the CPU configuration
is not rebuilt** — its index is the Dockerfile's unchanged default, so version
parity holds by construction and a second multi-gigabyte rebuild would verify
nothing.

# Contributing

## Development environment

The repository ships a [VS Code Dev Container](.devcontainer/) as the supported
development environment. With Docker and the VS Code **Dev Containers** extension
installed, open the repository and choose **Reopen in Container**, taking the
default configuration (see [Choosing a container](#choosing-a-container-cpu-or-cuda)
for the GPU-capable alternative). The container
provisions everything on first build: Python 3.12, the project installed editable
with the pinned `game-engine-core` dependency (which pulls in torch/numpy via its
learning extra), and the type-checking/linting/testing toolchain — no manual setup
and no virtual environment (the container is the isolation boundary).

Personal environment variables (e.g. `TZ=America/Vancouver`) can be set
container-wide in `.devcontainer/devcontainer.env` — one `KEY=VALUE` per line. To
get started, rename (or copy) [`devcontainer.env.example`](.devcontainer/devcontainer.env.example)
to `devcontainer.env`, edit it, and rebuild the container. The file is gitignored
and created empty on first container start if absent, so it is entirely optional.

### Choosing a container: CPU or CUDA

Two configurations are offered when reopening the repository in a container:

| Configuration | When to use it |
|---|---|
| **capture-the-flag** (default) | Everything. Installs CPU-only torch wheels and passes no device through. |
| **capture-the-flag (CUDA)** | Only when a GPU is wanted. Installs GPU-capable wheels of the same torch version and passes the host GPU through. |

CPU is the default deliberately: the CUDA stack is several gigabytes of wheels
baked into the image, and ordinary work should not pay for it. The two share one
[`Dockerfile`](.devcontainer/Dockerfile) and differ only in the `TORCH_INDEX_URL`
build argument and the `--gpus all` run argument, so they cannot drift apart.

**What the CUDA configuration does not do.** It makes a GPU *reachable* —
`torch.cuda.is_available()` is true inside it — but nothing in this repository
places a network or a tensor on it. Self-play, training, and played games all
still compute on the CPU, and a run's `timings.json` correctly records
`"torch_device": "cpu"` there. So opening the CUDA container to make training
faster will not make it faster. Use it to develop and test against real hardware.

**The remaining blocker is here, not upstream.** This was a library limitation
until `game-engine-core` v0.1.6, whose training loop places each minibatch on the
model's device and whose evaluator no longer imposes one; the library now follows
the device it is given. What is missing is this repository choosing one — nothing
here moves the model or its tensors, and no entry point offers a `--device` flag
(see `capture_the_flag/device.py`, which resolves the decision but is not yet
wired to anything).

**Host prerequisites.** An NVIDIA GPU **that the pinned torch build ships kernels
for**, with a current driver, and a Docker installation with GPU support (the
NVIDIA container toolkit; Docker Desktop's
WSL2 backend provides this once the Windows-side NVIDIA driver is installed —
there is no separate driver to install inside WSL). Confirm before building by
running `nvidia-smi` **on the host**, not in a container; it should list the GPU.
The `--gpus all` run argument makes GPU support a hard requirement of this
configuration rather than an optimization, so expect it to fail at container
start on a host without it rather than to come up GPU-less.

Verify the container once it is up:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

The CUDA container reports a `+cuXXX` build, a CUDA version, and `True`; the
default container reports a `+cpu` build, `None`, and `False`. The torch
*version* must match in both — the configurations differ by build, not by
version, or no comparison between them means anything.

In the CUDA container, one more — it should print a tensor, not raise:

```bash
python -c "import torch; print(torch.zeros(1, device='cuda') + 1)"
```

**That allocation is the real check, not `is_available()`.** A torch build ships
compiled kernels for a fixed set of compute capabilities, and a card newer than
the build is detected but cannot be run on: `is_available()` returns `True`, and
the first kernel launch fails with *"no kernel image is available for execution
on the device"*. If that happens, the fix is the `TORCH_INDEX_URL` build argument
in [`.devcontainer/cuda/devcontainer.json`](.devcontainer/cuda/devcontainer.json),
repointed by this rule: **the newest `cuXXX` index that still ships the pinned
torch version, and whose CUDA version is at or below the one `nvidia-smi` reports
on the host.** It is **not** a different torch version, which would break the
version parity the paragraph above requires.

Confirm a candidate index actually covers the card rather than trusting the
suggestion torch prints — that suggestion is a recommendation, not an inspection.
Compare the wheel's compiled architectures against the device:

```bash
python -c "import torch; print(torch.cuda.get_arch_list(), torch.cuda.get_device_capability(0))"
```

The card's `sm_` entry must appear in the list; if it does not, a kernel launch
will fail however current the driver is. Note that a new CUDA release **drops**
old architectures as well as adding new ones, so an index can be too new for an
old card just as easily as too old for a new one — the rule has a floor as well
as a ceiling.

### Type checking and linting

Run from the container terminal, from the repository root:

```bash
pyright        # type check
ruff check .   # lint
```

Both tools are configured in `pyproject.toml` and both should pass clean before a
change is submitted.

### Tests

Run from the container terminal, from the repository root:

```bash
pytest
```

The suite must pass before a change is submitted.

## Python version

This project targets Python 3.12+. Follow up-to-date language standards
accordingly.

## The game-engine-core dependency

This project depends on [game-engine-core](https://github.com/phil-hutchinson/game-engine-core),
consumed exactly as an external third-party consumer would: it is **not** vendored
or path-mounted, but pinned to a specific commit on GitHub in `pyproject.toml`
(`game-engine-core[learning] @ git+https://…@<commit>`). The `learning` extra
(torch/numpy) is a hard dependency — this project always ships the learned play
engine — so there is no separate torch-free install to keep in sync. This keeps
builds reproducible and forces us to exercise the same install path a real
consumer uses.

A pull request **may** bump this pin to a newer `game-engine-core` commit (or a
release tag, once the library publishes them) when it needs a newer feature or
fix. When it does: bump the single pinned dependency, keep the bump in a commit of
its own with a note on why, and rebuild the container so the new version is
actually installed and tested.

## Code conventions

### Imports

**Within the package** (`capture_the_flag/`, and any future sibling packages): use
relative imports.

```python
# correct — inside capture_the_flag
from .board import BOARD_COLUMNS
```

**In `tests/`**: import the project package absolutely, exactly as an external
consumer would. `game-engine-core` is likewise imported absolutely (it is a
third-party dependency).

```python
# correct — inside tests/
from game_engine_core.evaluators.null_evaluator import NullEvaluator
from capture_the_flag.board import BOARD_COLUMNS
```

Ruff enforces these conventions only partially: it bans parent-relative imports
outside a module's own subtree (TID252, via `ban-relative-imports = "parents"`),
but no ruff rule can *require* relative imports, so the within-package convention
relies on code review rather than tooling.

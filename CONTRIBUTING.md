# Contributing

## Development environment

The repository ships a [VS Code Dev Container](.devcontainer/) as the supported
development environment. With Docker and the VS Code **Dev Containers** extension
installed, open the repository and choose **Reopen in Container**. The container
provisions everything on first build: Python 3.12, the project installed editable
with its `learning` extra, the pinned `game-engine-core` dependency, and the
type-checking/linting/testing toolchain — no manual setup and no virtual
environment (the container is the isolation boundary).

Personal environment variables (e.g. `TZ=America/Vancouver`) can be set
container-wide in `.devcontainer/devcontainer.env` — one `KEY=VALUE` per line. To
get started, rename (or copy) [`devcontainer.env.example`](.devcontainer/devcontainer.env.example)
to `devcontainer.env`, edit it, and rebuild the container. The file is gitignored
and created empty on first container start if absent, so it is entirely optional.

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
(`game-engine-core @ git+https://…@<commit>`), with the `learning` extra pinned
identically. This keeps builds reproducible and forces us to exercise the same
install path a real consumer uses.

A pull request **may** bump this pin to a newer `game-engine-core` commit (or a
release tag, once the library publishes them) when it needs a newer feature or
fix. When it does: bump the pin in **both** the base dependency and the `learning`
extra so they stay identical, keep the bump in a commit of its own with a note on
why, and rebuild the container so the new version is actually installed and tested.

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

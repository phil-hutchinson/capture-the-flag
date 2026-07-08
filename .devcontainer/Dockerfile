FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# CLI pyright is an npm package, so the image needs a node runtime.
# Debian bookworm ships node 18 (EOL); take the current LTS from nodesource instead.
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# CLI pyright, baked into the image so the environment type-checks out of the
# box. Pinned so every rebuild produces the same diagnostics; bump the pin
# deliberately in a commit of its own.
RUN npm install -g pyright@1.1.411

# CLI ruff, same rationale and pinning policy. The Ruff VS Code extension is
# told to use this binary (ruff.importStrategy in devcontainer.json), so the
# pin governs both the CLI and the editor.
RUN pip install --no-cache-dir ruff==0.15.20

# pytest, same rationale and pinning policy.
RUN pip install --no-cache-dir pytest==9.1.1

# Pre-create the Claude Code config dir owned by the container user, so the
# named volume mounted here initializes writable (a bare mount point would be
# root-owned and logins would fail to persist).
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude

# Let git operate on the bind-mounted workspace without tripping its
# "dubious ownership" guard. Docker Desktop presents the Windows-host checkout
# with an owner that isn't the container's `vscode` user, so git otherwise
# refuses every command (init/status/commit) until safe.directory is set. This
# is a single-developer, trusted container, so allowing any path is acceptable
# and keeps a fresh clone working with no in-container setup. Written to the
# system config (/etc/gitconfig) so it applies to every user in the image.
RUN git config --system --add safe.directory '*'

# Bake the heavy torch/numpy dependencies (pulled in transitively by
# game-engine-core's `learning` extra) into an image layer so rebuilds hit the
# Docker cache instead of re-downloading them. The project's own editable
# install — and the pinned game-engine-core dependency it pulls from GitHub —
# happens in postCreateCommand, since that needs the workspace mount and
# network, neither of which exist at image build time. CPU wheels: the
# container has no GPU passthrough, and the default Linux wheels pull in the
# multi-GB CUDA stack.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.0" \
    && pip install --no-cache-dir numpy

# Story 51 — before/after baseline

The story's acceptance criterion is that one command fails before the change and
passes after it. The `cu126` state becomes unreachable the moment the container is
rebuilt, so the "before" is captured here first.

Host: RTX 5060 Ti (compute capability **sm_120**), driver **591.44**, reporting
CUDA **13.1**. Recorded on the `feat/51-move-to-cu130` branch at `2ee90d0`.

## Before — `TORCH_INDEX_URL=.../whl/cu126`

`CONTRIBUTING.md:63` — reports a CUDA build and claims the GPU is available:

```
2.13.0+cu126 12.6 True
```

`CONTRIBUTING.md:74` — raises instead of printing a tensor:

```
UserWarning: Found GPU0 NVIDIA GeForce RTX 5060 Ti which is of compute capability (CC) 12.0.
...
Your installed torch==2.13.0+cu126 does not include kernels for this GPU. Reinstall the same version against a CUDA build that does, e.g.:
  For CUDA 12.9 use pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu129
  For CUDA 13.0 use pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu130
  For CUDA 13.2 use pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu132

UserWarning:
NVIDIA GeForce RTX 5060 Ti with CUDA capability sm_120 is not compatible with the current PyTorch installation.
The current PyTorch install supports CUDA capabilities sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90.

Traceback (most recent call last):
  File "<string>", line 1, in <module>
torch.AcceleratorError: CUDA error: no kernel image is available for execution on the device
```

Three things worth keeping from this output:

- **`is_available()` is `True` while no kernel can launch.** This is why
  `CONTRIBUTING.md` names the allocation, not availability, as the real check —
  the documented reasoning is confirmed here rather than merely asserted.
- **The raised error is `cudaErrorNoKernelImageForDevice`**, the exact symptom
  `CONTRIBUTING.md:80` predicts in prose. The repository diagnosed this failure
  before encountering it.
- **torch itself names `cu129`, `cu130` and `cu132` as the fixes**, and excludes
  `cu126` and `cu128`. This is the evidence behind the story's claim that `cu130`
  ships `sm_120` kernels. It is still indirect — it is torch's recommendation, not
  an inspection of the wheel's architecture list — so the rebuild remains the
  confirmation.

## After — `TORCH_INDEX_URL=.../whl/cu130`

Recorded from a container rebuilt from scratch on the same host.

`CONTRIBUTING.md:63` — the torch version is unchanged, so parity with the CPU
configuration holds:

```
2.13.0+cu130 13.0 True
```

`CONTRIBUTING.md:74` — prints a tensor, with **no warning of any kind** on import
or on first CUDA use:

```
tensor([1.], device='cuda:0')
```

All three acceptance conditions met: a `+cu130` build, torch still at `2.13.0`,
a printed tensor, and a silent import.

### Confirming it is kernels, not a JIT fallback

A printed tensor alone would not distinguish real compiled kernels from PTX
JIT'd at load time, so the architecture list the wheel was built for was read
directly rather than inferred from torch's recommendation:

```
arch list: ['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120']
device cc: (12, 0)
device   : NVIDIA GeForce RTX 5060 Ti
```

`sm_120` is present and matches the device's compute capability exactly. This
closes the one gap the story acknowledged: the choice of `cu130` rested on
torch's own warning naming it as a fix, which is a recommendation rather than an
inspection. It is now an inspection.

A 512 × 512 `matmul` was also run to exercise cuBLAS rather than only the
elementwise add in the documented check, and completed with a correct result
after an explicit `synchronize()`.

### A note for whoever revisits the index

Compare the two architecture lists. `cu126` covered `sm_50` through `sm_90`;
`cu130` covers `sm_75` through `sm_120`, having **dropped** `sm_50`, `sm_60` and
`sm_70`. The "widest driver compatibility" the deleted comment was reaching for
is therefore a real trade-off and not an imaginary one — it just does not apply
to a single-developer repository with one known card. If this project ever needs
to run on pre-Turing hardware, that constraint returns and the selection rule
gains a floor as well as a ceiling.

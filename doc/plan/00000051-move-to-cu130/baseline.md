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

To be filled in at Step 3, from the rebuilt container. A pass is: a `+cu130`
build with the torch version still `2.13.0`, a printed tensor, and **no**
compute-capability warning.

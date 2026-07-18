# Reference network architecture

The network design of the landmark 2017 self-play chess/shogi/Go system,
laid out as a text diagram — the reference point for the (much smaller)
Step 4 network. Chess-configuration shapes shown throughout; tensor shapes
are `channels × rows × columns`.

## Full pipeline

```
                         INPUT  119 × 8 × 8
      ┌─────────────────────────────────────────────────────┐
      │ piece one-hot planes, both sides, last 8 board      │
      │ states (12 piece planes + 2 repetition planes) × 8  │
      │ + constant planes broadcast across the board:       │
      │   side to move, castling rights (4), move count,    │
      │   no-progress (fifty-move) counter                  │
      └─────────────────────────────────────────────────────┘
                              │
                              ▼
      ┌─────────────────────────────────────────────────────┐
      │ STEM                                    ~0.3M params│
      │   3×3 conv, 256 filters → batchnorm → ReLU          │
      └─────────────────────────────────────────────────────┘
                              │  256 × 8 × 8
                              ▼
      ┌─────────────────────────────────────────────────────┐
      │ RESIDUAL TOWER                                      │
      │                                                     │
      │   ┌───────────────────────────────┐                 │
      │   │ residual block   ~1.2M params │  × 19           │
      │   │  (internals below)            │                 │
      │   └───────────────────────────────┘                 │
      │                                         ~22.4M total│
      └─────────────────────────────────────────────────────┘
                              │  256 × 8 × 8
              ┌───────────────┴────────────────┐
              ▼                                ▼
  ┌───────────────────────────┐   ┌────────────────────────────┐
  │ POLICY HEAD   ~0.7M params│   │ VALUE HEAD    ~0.02M params│
  │  conv, 256 filters        │   │  1×1 conv, 1 filter        │
  │  → batchnorm → ReLU       │   │  → batchnorm → ReLU        │
  │  → conv, 73 filters       │   │      │  1 × 8 × 8          │
  │                           │   │  → flatten (64)            │
  │                           │   │  → fully connected → 256   │
  │                           │   │  → ReLU                    │
  │                           │   │  → fully connected → 1     │
  │                           │   │  → tanh                    │
  └───────────────────────────┘   └────────────────────────────┘
              │                                │
              ▼                                ▼
     POLICY LOGITS  73 × 8 × 8        VALUE  scalar in [-1, 1]
     (= 4,672 move logits:
      plane = movement type,
      position = from-square)
```

Total: roughly **24M parameters**, nearly all of it in the shared trunk.
The heads are deliberately thin readouts of one common board representation.

## Inside one residual block

```
        x  ──────────────────────────────┐
        │                                │
        ▼                                │
   3×3 conv, 256 filters                 │
        │                                │
     batchnorm                           │  skip connection
        │                                │  (identity — no
       ReLU                              │   weights)
        │                                │
   3×3 conv, 256 filters                 │
        │                                │
     batchnorm                           │
        │                                │
        +  ◄─────────────────────────────┘
        │
       ReLU
        │
        ▼
     output      (same shape as x: 256 × 8 × 8)
```

The block computes a *correction* to its input rather than replacing it, and
gradients flow straight through the `+` — the property that makes a tower of
~40 conv layers trainable.

## Policy head as move planes

The 73 policy planes give every move a stable `(plane, row, col)` slot:

- 56 planes — "queen-like" moves: 8 directions × up to 7 squares of distance
- 8 planes — knight moves
- 9 planes — underpromotions (3 piece choices × 3 directions)

`(plane, row, col)` reads as "movement type X from square (row, col)" — the
same `from-square × movement-offset` layout as this repo's Step 3 action
space, kept image-shaped so the policy head can stay convolutional.

## Scaling knobs

Parameter count goes roughly as `blocks × filters²` (each block is two
`filters × filters × 3 × 3` convs), so width is the expensive dial:

| blocks × filters | trunk params | note                        |
| ---------------- | ------------ | --------------------------- |
| 19 × 256         | ~22.4M       | the reference configuration |
| 10 × 128         | ~3.0M        |                             |
| 6 × 96           | ~1.0M        |                             |
| 4 × 64           | ~0.3M        | workstation-friendly        |

Depth also sets the receptive field: each 3×3 conv extends a square's
"awareness" by one step in every direction, so a 12×12 board wants enough
conv layers (~11+, i.e. ~5+ blocks plus the stem) for corner-to-corner
influence to propagate at least once.

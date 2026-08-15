# The post-repin baseline

Companion to [story.md](story.md) and [implementation-plan.md](implementation-plan.md)
Step 7. The record itself is in [`baseline/`](baseline/): `timings.json` is the
artifact a later optimization gets compared against, `timings.txt` is the same
tree rendered, and the two `.ctfgame` files are the games that were actually
played.

Taken 2026-08-15 at commit `8ee2f7c`, with the standard recipe and its defaults
unchanged:

```bash
python -m capture_the_flag.timing_benchmark --record-dir doc/plan/00000045-repin-to-engine-v0.1.6/baseline
```

## What this is, and what it is not

**It is a new baseline, not a "after" to the July "before."** Two things moved
at once and either alone would break the comparison: the machine is different
hardware, and the search is a different algorithm — v0.1.6 replaces partial
expansion with evaluate-then-expand-all over a fleet. Story 29's advice to
compare call counts rather than seconds does not rescue a comparison across an
algorithm change, because the call counts are exactly what the algorithm decides.
Nothing below is quoted as a regression or an improvement against July.

**It is batch-of-one.** The recipe plays real games through `run_batch`, and
play-time search under v0.1.6 wraps its retained root into a one-slot fleet, so
every wave holds one position and a region's call count is also its position
count. That is what makes the tree below readable the way the old ones were —
see [story.md](story.md) on why a record taken from a *training* run, where the
fleet is `games_per_generation` wide, is not.

## The machine

| | |
| --- | --- |
| CPU | AMD Ryzen 7 8700F, 16 logical cores |
| Platform | Linux 6.18 (WSL2), glibc 2.36 |
| torch | 2.13.0+cu126, 8 compute threads, 16 interop threads |
| Device | CPU (`torch_device: "cpu"`, TF32 off) |
| Python / engine | 3.12.13 / `game-engine-core` 0.1.6 |

The `+cu126` build is worth noting: this host has an RTX 5060 Ti, which is
sm_120 and outside the compute capabilities that build ships kernels for, so
`torch.cuda.is_available()` is true and every kernel launch fails. Nothing here
touches the GPU, so the measurement is unaffected — but it is why the device
line reads `cpu` on a machine that has a card, and it is a prerequisite the
device story will have to resolve.

## What the instrumentation costs

```
timing off   10.84s, 10.25s, 11.58s   mean 10.89s   fastest 10.25s   spread 12.9%
timing on    11.36s, 10.38s, 11.62s   mean 11.12s   fastest 10.38s   spread 11.9%

overhead: +2.1% by mean, +1.3% by fastest run
machine noise (worst spread within an arm): 12.9%
```

Same reading as both July measurements: the two arms differ by less than either
arm's own spread, so this is an upper bound rather than a figure. WSL2 remains a
noisy place to measure wall clock.

The sharper bound is the one story 29 said to watch — region entries per second
of work:

| | 2026-07-24 | 2026-07-25 | 2026-08-15 |
| --- | --- | --- | --- |
| entries per second of work | ~1,970 | ~2,730 | **~3,021** |

34,939 entries in 11.57s. The trend is up but the conclusion is unchanged: this
is thousands per second against a per-entry cost of well under a microsecond, and
story 29's threshold for revisiting "timing on by default" was *millions*. The
rise is expected rather than alarming — a faster machine does the same work in
less time, which raises entries per second without adding any.

## Where the time goes

Full tree in [`baseline/timings.txt`](baseline/timings.txt). The shape:

| Region | Calls | Total | Mean | % of root |
| --- | ---: | ---: | ---: | ---: |
| `search` | 100 | 11.496s | 115.0ms | 99.4% |
| `evaluate-position` | 2,452 | 9.959s | 4.06ms | 86.1% |
| `network-forward` | 2,452 | 6.116s | 2.49ms | **52.9%** |
| `decode-policy` | 2,452 | 1.717s | 700.1us | 14.8% |
| `encode-position` | 2,452 | 1.364s | 556.4us | 11.8% |
| `network-mode-switch` | 2,452 | 634ms | 258.5us | 5.5% |
| `outcome` (under search) | 2,500 | 640ms | 255.9us | 5.5% |
| `legal-plies` (under search) | 2,452 | 459ms | 187.3us | 4.0% |
| `apply-ply` | 2,400 | 34ms | 14.3us | 0.3% |

**The report names 94.2% of the run.** Of the 5.8% left over, 3.5 points are
`search`'s own remainder — the pinned engine's tree walk, PUCT selection, fleet
bookkeeping and backpropagation, which this repository deliberately does not
instrument. That number is not comparable to July's 1.1 points: this is a play
workload rather than a training run, and the engine's internals are the part that
changed most at v0.1.6.

**Calls are exactly what batch-of-one predicts.** 2 games × 50 plies = 100
searches; 100 × 25 iterations = 2,500 possible evaluations, of which 2,452
happened — the other 48 iterations selected a terminal leaf, which the engine
never evaluates. Both games ended as draws by inactivity at 50 plies, as the seed
fixes them to.

## Findings, recorded and not acted on

Following story 29's rule: each names what was measured and what it does not
establish.

**1. The forward pass is over half the run, at batch size one — 6.1s, 52.9%.**
2,452 forwards of a single position each. This is the batch-1 regime: per-call
launch and dispatch overheads dominate arithmetic that is genuinely microseconds,
and a GPU would not help until the calls are batched. It is the clearest
statement of what the fleet is *for* — and the reason it says nothing yet is that
play-time search runs at width 1 by construction. What a wide fleet does to this
line is the seam story's headline measurement, not this one's.

**2. `network-mode-switch` survives the repin — 634ms, 5.5%.** Story 29 measured
this at 4.7% of a training run and diagnosed it: the shared evaluator calls
`model.eval()` unconditionally, `Module.train()` has no early-out, and a
93-submodule trunk pays 93 writes for a flag that already holds the value being
written. Still one per call. **But the call is now a wave**, so unlike July this
cost no longer scales with positions evaluated — at fleet width N it is paid once
for N positions instead of N times. That is a prediction this baseline cannot
test (it is width 1, where the two coincide) and the seam story can.

**3. Policy decoding is three roughly equal walks — 1.7s, 14.8%.** `legal-plies`
(206us), `build-policy-mask` (203us) and `read-ply-probabilities` (193us) are
within 7% of each other, while `map-ply-slots` (42us) and `policy-softmax`
(27.5us) are an order of magnitude cheaper. Two of the three expensive ones walk
the legal plies an element at a time. Nothing here is acted on, but if decoding is
ever attacked, it is those three or nothing.

**4. The cheapest instrumented region is still far above a region entry.**
`policy-softmax` at 27.5us matches July's ~27us almost exactly, on different
hardware — which is a coincidence worth not over-reading, but it does preserve
story 29's guardrail: the cheapest thing measured is still tens of times the cost
of measuring it, so no phase here has become too cheap to justify its region.

## Comparing against this later

The recipe's own instructions apply unchanged: run the same command, compare
region by region, check the environments match before believing a difference, and
compare call counts rather than seconds. One caution this baseline adds — **check
the fleet width too.** Two records taken at different widths are not comparable
region by region even on identical hardware, because the regions at the wave
boundary count waves. A record with `search-for-training` in it is a training
workload and is not this.

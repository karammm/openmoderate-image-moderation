# Benchmarks

openmoderate ships with a small, reproducible benchmark of **475 openly licensed photos from
Wikimedia Commons, each reviewed by eye**. The images are split in half: prompts and
thresholds were tuned on the *dev* half only, and the numbers below are for the held-out
*test* half (238 images), which tuning never saw.

```bash
python benchmark/run.py            # reproduces the table below
python benchmark/run.py --config my_policy.yaml --head my_head.omh   # measure your setup
```

## Results (v1.0, default policy)

--8<-- "benchmark/RESULTS.md:5:12"

**Recall** is the share of a category's images that were flagged with that category.
**Precision** counts only the safe images as negatives (each image has a single label, so
a riot photo that also shows a gun is not a `weapons` false positive). The full
per-group breakdown of false positives is in
[`benchmark/RESULTS.md`](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/RESULTS.md).

## Model presets (v1.1)

`Moderator(preset=...)`, `--preset` on the CLI and `OPENMODERATE_PRESET` for the server choose
a larger CLIP model. Measured on all 475 benchmark images:

| Preset | Model | Size | Recall (avg) | Safe images flagged | Cross-validated recall | CPU | Apple GPU |
|---|---|---:|---:|---:|---:|---:|---:|
| `fast` (default) | ViT-B/32 | ~600 MB | 77.5% | 6.5% | 73.5% | 10 ms | 6 ms |
| `balanced` | ViT-B/16 | ~600 MB | 77% | 4.7% | 79.5% | 32 ms | 16 ms |
| `accurate` | ViT-L/14 | ~1.7 GB | **82%** | **4.2%** | **82.4%** | 129 ms | 68 ms |

Per category, `accurate` scores: alcohol 87%, drugs 94%, hate symbols 73%, tobacco 72%,
violence 87%, weapons 80% recall (the only category where it is slightly below `fast`, at 84%).

How these were chosen:

- Each preset's calibration follows one rule: the highest recall at which at most ~5% of safe
  images are flagged. `fast` keeps its 1.0 calibration so existing scores don't change.
- With small sets, a single dev/test split proved unreliable for comparing models (ViT-L/14
  looked far better on dev than on test). The **cross-validated recall** column is the
  fairer comparison: each half is scored with the calibration chosen on the other half, then
  the two are averaged.
- Speeds are per image in batches, on an Apple M-series machine (CPU with 4 threads, or the
  built-in GPU via MPS). x86 servers and NVIDIA GPUs will differ; measure on your hardware.

Trained heads are tied to the model they were trained with: retrain with `--preset` if you
switch.

## Improvement over v0.5

Same test images, same model, old versus new default prompts:

| Category | v0.5 recall | v1.0 recall | v0.5 precision | v1.0 precision |
|---|---:|---:|---:|---:|
| `alcohol` | 53% | 84% | 91% | 100% |
| `drugs` | 15% | 85% | 67% | 82% |
| `hate_symbols` | 50% | 61% | 100% | 100% |
| `tobacco` | 44% | 59% | 92% | 89% |
| `violence` | 82% | 82% | 100% | 100% |
| `weapons` | 79% | 79% | 96% | 100% |
| Safe images flagged | 5% | 6% | | |

The gains come from describing each category more completely (cannabis, joints and bongs
for `drugs`; glasses of beer and wine and cocktails for `alcohol`) and from more safe
look-alikes (milk, juice, coffee, kitchen knives).

## How to read these numbers

- **The sets are small** (11–28 positives per category in the test half), so each number
  has an uncertainty of roughly ±10 percentage points. They show where the model is
  strong and weak, not a precise ranking.
- **Where it is weak:** `hate_symbols` misses small or partially visible flags and
  insignia; `tobacco` misses some cigarettes and confuses others with joints; dried herbs
  and spices are sometimes flagged as `drugs`.
- **The images skew easy and old.** Commons is rich in museum pieces, historical photos and
  well-lit product shots. Screenshots, memes, phone photos and video frames are harder.
- **Not benchmarked:** nudity, sexual content, suggestive content, gore and self-harm. The
  maintainers chose not to collect such images. Evaluate those categories on a sample of
  your own traffic with [`openmoderate evaluate`](guide/training.md) before relying on them.

How the set was built and licensed is described in
[`benchmark/README.md`](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/README.md).

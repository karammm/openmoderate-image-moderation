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

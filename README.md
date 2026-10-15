# openmoderate

[![CI](https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml/badge.svg)](https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/openmoderate?color=blue)](https://pypi.org/project/openmoderate/)
[![Python](https://img.shields.io/badge/python-3.9%20%E2%80%93%203.14-blue)](https://pypi.org/project/openmoderate/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://karammm.github.io/openmoderate-image-moderation/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fkarammm%2Fopenmoderate-blue)](https://github.com/karammm/openmoderate-image-moderation/pkgs/container/openmoderate)
[![License](https://img.shields.io/github/license/karammm/openmoderate-image-moderation)](https://github.com/karammm/openmoderate-image-moderation/blob/main/LICENSE)

**Open-source, self-hosted image and video content moderation for Python.** Detect nudity, sexual content, violence, gore, weapons, hate symbols, drugs, self-harm, alcohol and tobacco in uploaded images and videos — with one `pip install`, no cloud account, no per-image fees, and no ML experience needed.

Think of it as an open alternative to Amazon Rekognition's `DetectModerationLabels` that runs inside your own app. Under the hood it runs **CLIP, a deep-learning vision-language model**, entirely on your machine — no API calls, no data leaves your servers. Its accuracy is [measured on a public benchmark](#accuracy).

<p align="center">
  <img src="https://raw.githubusercontent.com/karammm/openmoderate-image-moderation/main/docs/assets/demo.svg" alt="Terminal demo: openmoderate scans a folder, flagging a pistol (weapons 100%), a riot (violence 99%) and a swastika (hate_symbols 100%) while a beach, a dog and a US flag pass as safe; then the REST server flags a cigarette photo as tobacco (0.96)." width="820">
</p>

```python
from openmoderate import Moderator

mod = Moderator()
result = mod.analyze("upload.jpg")

if not result.is_safe:
    print(result.violations)
    # [Label(name='weapons', confidence=0.9612, parent='violence', threshold=0.5)]
```

![How openmoderate works: upload, normalize, embed with CLIP, compare against category and safe prompts, score, and decide with your thresholds. Use it as a Python library, a CLI or a REST API. Detects 11 categories out of the box, plus your own.](https://raw.githubusercontent.com/karammm/openmoderate-image-moderation/main/docs/assets/how-it-works.svg)

[**Documentation**](https://karammm.github.io/openmoderate-image-moderation/) · [Benchmarks](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/RESULTS.md) · [Changelog](https://github.com/karammm/openmoderate-image-moderation/blob/main/CHANGELOG.md) · [Security](https://github.com/karammm/openmoderate-image-moderation/blob/main/SECURITY.md)

## Install

```bash
pip install openmoderate
```

Python 3.9+. The first call downloads the CLIP model weights (~600 MB) once; after that everything runs offline, on CPU, CUDA or Apple Silicon. Extras: `openmoderate[server]`, `[video]`, `[fastapi]`, `[flask]`, `[django]`. See the [install notes](https://karammm.github.io/openmoderate-image-moderation/#install) for CPU-only servers.

## How it works: the machine-learning model

openmoderate is built on **[OpenCLIP](https://github.com/mlfoundations/open_clip)**, an open implementation of CLIP: a deep-learning model with a Vision Transformer image encoder and a text encoder, trained on LAION-2B (about 2 billion image–text pairs). CLIP places images and sentences in the same vector space, so "how close is this photo to *a photo of a gun*?" becomes a number.

For every image:

1. **Embed the image.** Letterbox bars and padding are trimmed, then the Vision Transformer turns the image into a vector (an embedding).
2. **Embed the policy.** Each category is described by short text prompts ("a photo of a gun", "a nazi swastika flag"), alongside a pool of everyday *safe* prompts and category-specific look-alikes (kitchen knives, national flags, medicine). These are embedded once and cached.
3. **Compare.** Cosine similarity between the image vector and every prompt vector.
4. **Score.** For each category, the margin between its best-matching prompt and the best safe or look-alike prompt goes through a calibrated sigmoid, giving a 0–1 confidence.
5. **Decide.** A confidence at or above the category's threshold is a violation.

This is **zero-shot classification**: it needs no labelled training data, and a new category is a few lines of text. When you do have labelled images, `openmoderate train` adds **supervised learning** on top: a class-balanced logistic-regression head trained on frozen CLIP embeddings, which can add new labels or sharpen existing ones.

Three model sizes are available as presets:

| Preset | CLIP model | Parameters | Download | CPU, per image | Apple GPU, per image |
|---|---|---:|---:|---:|---:|
| `fast` (default) | ViT-B/32 | ~150 M | ~600 MB | 10 ms | 6 ms |
| `balanced` | ViT-B/16 | ~150 M | ~600 MB | 32 ms | 16 ms |
| `accurate` | ViT-L/14 | ~430 M | ~1.7 GB | 129 ms | 68 ms |

Speeds are batched, on an Apple M-series machine (4 CPU threads, or the built-in GPU); CUDA GPUs are used automatically when available.

## What you can do with it

**Pick the accuracy you need** — `Moderator(preset="accurate")` uses a larger model: 82% recall with 4.2% of safe images flagged, versus 77.5% / 6.5% for the default ([details below](#accuracy)).

**Tune the policy** — thresholds, categories and your own categories as plain text, no training data needed ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/python/)):

```python
mod = Moderator(thresholds={"weapons": 0.3}, exclude=["alcohol", "tobacco"])
mod = Moderator("policy.yaml")   # custom categories like "gambling" in YAML
```

**Scan from the command line** — folders, URLs and videos; `--fail-on-violation` for CI ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/cli/)):

```bash
openmoderate scan ./uploads
```

**Train on your own images** for better accuracy in your domain ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/training/)):

```bash
openmoderate train ./dataset -o my_head.omh      # dataset/<label>/*.jpg + dataset/safe/
```

**Moderate videos** with timestamped segments ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/video/)):

```python
Moderator().analyze_video("clip.mp4").segments   # weapons 0:03–0:06, violence 0:09–0:12
```

**Protect uploads in FastAPI, Flask or Django** with one line ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/integrations/)):

```python
async def avatar(file: ModeratedFile): ...                          # FastAPI
avatar = models.ImageField(validators=[ModerationValidator()])      # Django
```

**Call it over HTTP from any language** — REST server and Docker image ([guide](https://karammm.github.io/openmoderate-image-moderation/guide/server/)):

```bash
docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me ghcr.io/karammm/openmoderate
curl -H "X-API-Key: change-me" -F file=@upload.jpg localhost:8000/v1/moderate
```

## Accuracy

Accuracy is measured on a public benchmark of **475 openly licensed photos from Wikimedia Commons, each reviewed by eye** (about half of the candidates were removed as unclear or mislabelled). 215 of them are safe, including deliberate look-alikes such as kitchen knives, national flags, milk and medicine. Anyone can reproduce the numbers with `python benchmark/run.py --preset <name> --split all`.

**Recall** is the share of each category's images that get flagged; **safe images flagged** is the false-positive rate on the 215 safe photos.

| | `fast` (default) | `balanced` | `accurate` |
|---|---:|---:|---:|
| `alcohol` | 76% | 82% | **87%** |
| `drugs` | 85% | 83% | **94%** |
| `hate_symbols` | 65% | 65% | **73%** |
| `tobacco` | 68% | 67% | **72%** |
| `violence` | **87%** | 78% | **87%** |
| `weapons` | 84% | **88%** | 80% |
| **Average recall** | 77.5% | 77% | **82%** |
| **Safe images flagged** | 6.5% | 4.7% | **4.2%** |
| Cross-validated average recall | 73.5% | 79.5% | **82.4%** |

How these numbers were produced:

- **Calibration** follows one rule for every model: the highest recall at which at most ~5% of safe images are flagged (`fast` keeps its original 1.0 calibration).
- **Cross-validation.** The images are split into two halves. A single tuning/test split proved unreliable at this size, so the last row scores each half with the calibration chosen on the other half and averages the two. It is the fairest estimate of how each model generalises.
- **Precision is high.** On the default model's held-out half, precision is 100% for alcohol, hate symbols, violence and weapons, and 82–89% for drugs and tobacco ([full results](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/RESULTS.md)).

Limits to keep in mind:

- The sets are small (23–56 images per category), so treat each number as roughly ±10 points.
- **Nudity, sexual content, gore and self-harm are not benchmarked**: the maintainers chose not to collect such images. Evaluate them on your own data with `openmoderate evaluate`.
- Commons skews towards clear, well-lit photos; screenshots, memes and phone photos are harder.
- Zero-shot moderation is strong on clear-cut cases and will miss subtle ones. For high-stakes decisions, send borderline scores to human review.

[Benchmark method and licensing](https://karammm.github.io/openmoderate-image-moderation/benchmarks/) · [How it works and its limits](https://karammm.github.io/openmoderate-image-moderation/guide/concepts/)

## Contributing

Contributions are welcome — better prompts, new categories, benchmark images and bug reports especially. See [CONTRIBUTING.md](https://github.com/karammm/openmoderate-image-moderation/blob/main/CONTRIBUTING.md). Report security issues privately ([SECURITY.md](https://github.com/karammm/openmoderate-image-moderation/blob/main/SECURITY.md)).

## Responsible use

openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by protected characteristics. Moderation models make mistakes; give users a way to appeal automated decisions.

## License

[Apache 2.0](https://github.com/karammm/openmoderate-image-moderation/blob/main/LICENSE). Benchmark images keep their own licences (see [`benchmark/manifest.csv`](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/manifest.csv)).

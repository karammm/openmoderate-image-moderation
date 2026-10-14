# openmoderate

[![CI](https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml/badge.svg)](https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/openmoderate?color=blue)](https://pypi.org/project/openmoderate/)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/openmoderate/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://karammm.github.io/openmoderate-image-moderation/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Fkarammm%2Fopenmoderate-blue)](https://github.com/karammm/openmoderate-image-moderation/pkgs/container/openmoderate)
[![License](https://img.shields.io/github/license/karammm/openmoderate-image-moderation)](LICENSE)

**Open-source, self-hosted image and video content moderation for Python.** Detect nudity, sexual content, violence, gore, weapons, hate symbols, drugs, self-harm, alcohol and tobacco in uploaded images and videos — with one `pip install`, no cloud account, no per-image fees, and no ML experience needed.

Think of it as an open alternative to Amazon Rekognition's `DetectModerationLabels` that runs inside your own app.

<p align="center">
  <img src="docs/assets/demo.svg" alt="Terminal demo: openmoderate scans a folder, flagging a pistol (weapons 100%), a riot (violence 99%) and a swastika (hate_symbols 100%) while a beach, a dog and a US flag pass as safe; then the REST server flags a cigarette photo as tobacco (0.96)." width="820">
</p>

```python
from openmoderate import Moderator

mod = Moderator()
result = mod.analyze("upload.jpg")

if not result.is_safe:
    print(result.violations)
    # [Label(name='weapons', confidence=0.9612, parent='violence', threshold=0.5)]
```

![How openmoderate works: upload, normalize, embed with CLIP, compare against category and safe prompts, score, and decide with your thresholds. Use it as a Python library, a CLI or a REST API. Detects 11 categories out of the box, plus your own.](docs/assets/how-it-works.svg)

[**Documentation**](https://karammm.github.io/openmoderate-image-moderation/) · [Benchmarks](benchmark/RESULTS.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## Install

```bash
pip install openmoderate
```

Python 3.9+. The first call downloads the CLIP model weights (~600 MB) once; after that everything runs offline, on CPU, CUDA or Apple Silicon. Extras: `openmoderate[server]`, `[video]`, `[fastapi]`, `[flask]`, `[django]`. See the [install notes](https://karammm.github.io/openmoderate-image-moderation/#install) for CPU-only servers.

## What you can do with it

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

Measured on a held-out set of hand-reviewed, openly licensed photos ([full results and method](https://karammm.github.io/openmoderate-image-moderation/benchmarks/), reproducible with `python benchmark/run.py`):

| Category | Recall | Precision |
|---|---:|---:|
| `drugs` | 85% | 82% |
| `alcohol` | 84% | 100% |
| `violence` | 82% | 100% |
| `weapons` | 79% | 100% |
| `hate_symbols` | 61% | 100% |
| `tobacco` | 59% | 89% |

6% of safe images (including look-alikes such as kitchen knives, milk and medicine) were flagged. Sets are small, so read these as ±10 points. Nudity, sexual content, gore and self-harm are **not** benchmarked by the maintainers — evaluate them on your own data.

Zero-shot moderation is good at clear-cut cases and will miss subtle ones. Evaluate on a sample of your own traffic, adjust thresholds, and send borderline scores to human review for high-stakes decisions. [How it works and its limits](https://karammm.github.io/openmoderate-image-moderation/guide/concepts/).

## Contributing

Contributions are welcome — better prompts, new categories, benchmark images and bug reports especially. See [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues privately ([SECURITY.md](SECURITY.md)).

## Responsible use

openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by protected characteristics. Moderation models make mistakes; give users a way to appeal automated decisions.

## License

[Apache 2.0](LICENSE). Benchmark images keep their own licences (see [`benchmark/manifest.csv`](benchmark/manifest.csv)).

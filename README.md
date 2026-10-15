<p align="center">
  <a href="https://karammm.github.io/openmoderate-image-moderation/">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/karammm/openmoderate-image-moderation/main/docs/assets/logo-dark.svg">
      <img src="https://raw.githubusercontent.com/karammm/openmoderate-image-moderation/main/docs/assets/logo-light.svg" alt="openmoderate" width="360">
    </picture>
  </a>
</p>

<p align="center">
  <strong>See every upload. Keep only what's safe.</strong><br>
  Open-source, self-hosted moderation for images and video: nudity, violence, weapons, hate symbols, drugs and more.
</p>

<p align="center">
  <a href="https://pypi.org/project/openmoderate/"><img src="https://img.shields.io/pypi/v/openmoderate?label=pypi&color=0969da" alt="PyPI version"></a>
  <a href="https://pypi.org/project/openmoderate/"><img src="https://img.shields.io/badge/python-3.9_%E2%80%93_3.14-0969da" alt="Python 3.9 to 3.14"></a>
  <a href="https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml"><img src="https://github.com/karammm/openmoderate-image-moderation/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/karammm/openmoderate-image-moderation/pkgs/container/openmoderate"><img src="https://img.shields.io/badge/docker-ghcr.io-0969da" alt="Docker image"></a>
  <a href="https://karammm.github.io/openmoderate-image-moderation/benchmarks/"><img src="https://img.shields.io/badge/benchmark-public_%26_reproducible-0969da" alt="Public benchmark"></a>
  <a href="https://github.com/karammm/openmoderate-image-moderation/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="Apache 2.0 license"></a>
</p>

<p align="center">
  <a href="https://karammm.github.io/openmoderate-image-moderation/"><b>Documentation</b></a> ·
  <a href="https://karammm.github.io/openmoderate-image-moderation/benchmarks/"><b>Benchmarks</b></a> ·
  <a href="https://github.com/karammm/openmoderate-image-moderation/discussions"><b>Discussions</b></a> ·
  <a href="https://github.com/karammm/openmoderate-image-moderation/blob/main/CHANGELOG.md"><b>Changelog</b></a> ·
  <a href="https://karammm.github.io/openmoderate-image-moderation/reference/"><b>API reference</b></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/karammm/openmoderate-image-moderation/main/docs/assets/demo.svg" width="820"
    alt="Terminal demo: openmoderate scans a folder, flagging a pistol (weapons 100%), a riot (violence 99%) and a swastika (hate_symbols 100%) while a beach, a dog and a US flag pass as safe; then the REST server flags a cigarette photo as tobacco (0.96).">
  <br>
  <sub>Every result shown is real output on openly licensed photos.</sub>
</p>

---

## Quick start

```bash
pip install openmoderate
```

```python
from openmoderate import Moderator

mod = Moderator()                      # or Moderator(preset="accurate")
result = mod.analyze("upload.jpg")     # path, URL, bytes, file upload or PIL image

result.is_safe        # False
result.violations     # [Label(name='weapons', confidence=0.96, parent='violence', threshold=0.5)]
```

Or from the terminal:

```bash
openmoderate scan ./uploads            # images and videos, recursively
```

## Why openmoderate

- **An open alternative to cloud moderation APIs.** Comparable to AWS Rekognition's `DetectModerationLabels`, but
  it runs inside your app: no cloud account, no per-image fees, and no image ever leaves your servers.
- **Real machine learning, no ML expertise needed.** A CLIP deep-learning model does zero-shot classification, so it
  works out of the box. Fine-tune it on your own labelled images when you need more.
- **Measured, not claimed.** Accuracy comes from a public benchmark of 475 hand-reviewed photos with a held-out half
  and cross-validation, and the limits are published next to the numbers.
- **Your policy, in plain text.** Change thresholds, switch categories off, or add new ones like *gambling* with a few
  words of YAML. No training data required.
- **Images and video.** Videos get timestamped segments ("weapons at 0:03–0:06"), with an early stop for fast
  rejection.
- **Drops into your stack.** One line protects uploads in FastAPI, Flask or Django; a REST API and Docker image
  serve every other language.
- **Hardened for untrusted input.** SSRF-safe URL fetching, size and decoding limits, pickle-free model files, and
  confidence scores hidden from end users by default.
- **Choose speed or accuracy.** Three model sizes, from 6 ms per image to the most accurate.

## Install

| You want to… | Install |
| --- | --- |
| Moderate images from Python or the CLI | `pip install openmoderate` |
| Moderate videos too | `pip install "openmoderate[video]"` |
| Protect uploads in FastAPI, Flask or Django | `pip install "openmoderate[fastapi]"` · `[flask]` · `[django]` |
| Run the REST API server | `pip install "openmoderate[server]"` |
| Use Docker, from any language | `docker run -p 8000:8000 ghcr.io/karammm/openmoderate` |

Python 3.9–3.14. The model weights (~600 MB) download once on first use; after that everything runs offline, on CPU,
NVIDIA GPUs or Apple Silicon. On CPU-only servers, see the
[install notes](https://karammm.github.io/openmoderate-image-moderation/#install) to save ~2 GB.

## Usage

<details open>
<summary><b>Python API and policies</b></summary>

```python
from openmoderate import Moderator

mod = Moderator(thresholds={"weapons": 0.3}, exclude=["alcohol", "tobacco"])
results = mod.analyze_batch(["a.jpg", "b.jpg", "c.jpg"])     # faster for many images
```

Keep the policy in YAML, including your own categories:

```yaml
# policy.yaml  →  Moderator("policy.yaml")
preset: accurate
thresholds: {weapons: 0.3}
disabled: [alcohol, tobacco]
custom_categories:
  - name: gambling
    prompts: ["a casino slot machine", "people gambling at a poker table"]
    negatives: ["people playing a board game"]   # benign look-alikes
```

[Python guide →](https://karammm.github.io/openmoderate-image-moderation/guide/python/)

</details>

<details>
<summary><b>FastAPI, Flask and Django</b></summary>

```python
# FastAPI: violating images get a 422 before your endpoint runs
@app.post("/avatar")
async def avatar(file: ModeratedFile): ...

# Flask
@app.post("/avatar")
@moderate_uploads("avatar")
def avatar(): ...

# Django: works in models, forms, the admin and DRF serializers
avatar = models.ImageField(validators=[ModerationValidator()])
```

The upload is rewound after the check, so you save it as usual. All integrations share one loaded model.
[Integrations guide →](https://karammm.github.io/openmoderate-image-moderation/guide/integrations/)

</details>

<details>
<summary><b>Videos</b></summary>

```python
result = Moderator().analyze_video("clip.mp4", fps=1, stop_on_violation=True)
result.segments   # [VideoSegment(name='weapons', start=3.0, end=6.0, max_confidence=0.99, frames=3)]
```

[Video guide →](https://karammm.github.io/openmoderate-image-moderation/guide/video/)

</details>

<details>
<summary><b>REST API and Docker</b></summary>

```bash
docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me ghcr.io/karammm/openmoderate
curl -H "X-API-Key: change-me" -F file=@upload.jpg localhost:8000/v1/moderate
```

Endpoints for single images, batches, base64, URLs (off by default) and videos, with interactive docs at `/docs`.
[Server guide →](https://karammm.github.io/openmoderate-image-moderation/guide/server/)

</details>

<details>
<summary><b>Command line and CI</b></summary>

```bash
openmoderate scan ./uploads --json                 # one JSON object per file
openmoderate scan ./uploads --fail-on-violation    # exit code 1 if anything is flagged
openmoderate scan clip.mp4 --fps 2 --preset accurate
```

[CLI guide →](https://karammm.github.io/openmoderate-image-moderation/guide/cli/)

</details>

<details>
<summary><b>Train on your own images</b></summary>

```bash
openmoderate train ./dataset -o my_head.omh        # dataset/<label>/*.jpg + dataset/safe/
openmoderate evaluate ./holdout --head my_head.omh
```

```python
mod = Moderator(head="my_head.omh")
```

[Training guide →](https://karammm.github.io/openmoderate-image-moderation/guide/training/)

</details>

## How it works

```
trim borders → embed image (CLIP) → compare with category prompts → calibrated score → your threshold
```

openmoderate is built on [OpenCLIP](https://github.com/mlfoundations/open_clip), an open implementation of CLIP: a
deep-learning model with a Vision Transformer image encoder and a text encoder, trained on LAION-2B (about 2 billion
image–text pairs). CLIP places images and sentences in the same vector space, so each category is described in plain
words ("a photo of a gun", "a nazi swastika flag"). An image is flagged when it matches a category's prompts clearly
better than everyday *safe* prompts and known look-alikes such as kitchen knives, national flags and medicine.

This is **zero-shot classification**: no training data is needed, and a new category is a few lines of text. With
labelled images, `openmoderate train` adds **supervised learning** on top: a class-balanced logistic-regression head
on frozen CLIP embeddings.

| Preset | CLIP model | Parameters | Download | CPU, per image | Apple GPU, per image |
| --- | --- | ---: | ---: | ---: | ---: |
| `fast` (default) | ViT-B/32 | ~150 M | ~600 MB | 10 ms | 6 ms |
| `balanced` | ViT-B/16 | ~150 M | ~600 MB | 32 ms | 16 ms |
| `accurate` | ViT-L/14 | ~430 M | ~1.7 GB | 129 ms | 68 ms |

[How it works, in depth →](https://karammm.github.io/openmoderate-image-moderation/guide/concepts/)

## Accuracy

Measured on **475 openly licensed photos from Wikimedia Commons, each reviewed by eye**, of which 215 are safe,
including deliberate look-alikes. Reproduce it with `python benchmark/run.py --preset <name> --split all`.

| Recall per category | `fast` (default) | `balanced` | `accurate` |
| --- | ---: | ---: | ---: |
| Alcohol | 76% | 82% | **87%** |
| Drugs | 85% | 83% | **94%** |
| Hate symbols | 65% | 65% | **73%** |
| Tobacco | 68% | 67% | **72%** |
| Violence | **87%** | 78% | **87%** |
| Weapons | 84% | **88%** | 80% |
| **Average recall** | 77.5% | 77% | **82%** |
| **Safe images flagged** | 6.5% | 4.7% | **4.2%** |
| Cross-validated average recall | 73.5% | 79.5% | **82.4%** |

Every model is calibrated with one rule: the highest recall with at most ~5% of safe images flagged. Because a single
tuning/test split proved unreliable at this size, the last row scores each half of the images with the calibration
chosen on the other half; it is the fairest estimate of real-world performance. Precision on the default model's
held-out half is 100% for alcohol, hate symbols, violence and weapons, and 82–89% for drugs and tobacco.
[Method, licences and full results →](https://karammm.github.io/openmoderate-image-moderation/benchmarks/)

> [!IMPORTANT]
> The categories have 23–56 images each, so read every number as roughly ±10 points. **Nudity, sexual content, gore
> and self-harm are not benchmarked**: the maintainers chose not to collect such images, so evaluate them on your own
> data with `openmoderate evaluate`. Zero-shot moderation is strong on clear-cut cases and will miss subtle ones; send
> borderline scores to human review for high-stakes decisions.

## Quality

Every push is checked in CI with:

- Unit and integration tests on Python 3.9, 3.10, 3.11, 3.12, 3.13 and 3.14, plus a test against the real model.
- Lint, formatting and type checks (`ruff`, `mypy`); the package ships type information (`py.typed`).
- The Docker image built and smoke-tested end to end, moderating a real image and a real video inside the container.
- A strict docs build, so broken links and docstrings fail the build.

Releases are automatic: when a version bump passes CI on `main`, it is tagged and published to PyPI (through trusted
publishing, with no stored tokens), GitHub Releases and the GitHub container registry.

## Community

- **Questions and ideas:** [GitHub Discussions](https://github.com/karammm/openmoderate-image-moderation/discussions)
- **False positives, missed content, bugs:** [open an issue](https://github.com/karammm/openmoderate-image-moderation/issues/new/choose).
  Please describe harmful images in words and never attach them.
- **Contributing:** see [CONTRIBUTING.md](https://github.com/karammm/openmoderate-image-moderation/blob/main/CONTRIBUTING.md)
  for setup, tests, the benchmark and releases. Better prompts and benchmark images are especially welcome.
- **Security:** please report vulnerabilities [privately](https://github.com/karammm/openmoderate-image-moderation/security/advisories/new),
  as described in [SECURITY.md](https://github.com/karammm/openmoderate-image-moderation/blob/main/SECURITY.md).
- **Code of conduct:** [CODE_OF_CONDUCT.md](https://github.com/karammm/openmoderate-image-moderation/blob/main/CODE_OF_CONDUCT.md)
- **Sister project:** [SafeType.js](https://github.com/karammm/safetype) moderates text as people type.

## Responsible use

openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by
protected characteristics. Moderation models make mistakes, so give users a way to appeal automated decisions.

## License

[Apache 2.0](https://github.com/karammm/openmoderate-image-moderation/blob/main/LICENSE) © openmoderate contributors.
Benchmark images keep their own licences (see
[`benchmark/manifest.csv`](https://github.com/karammm/openmoderate-image-moderation/blob/main/benchmark/manifest.csv)).

# openmoderate

**Open-source, self-hosted image content moderation for Python.** Detect nudity, sexual content, violence, gore, weapons, hate symbols, drugs, self-harm, alcohol and tobacco in uploaded images — with one `pip install`, no cloud account, no per-image fees, and no ML experience needed.

Think of it as an open alternative to Amazon Rekognition's `DetectModerationLabels` that runs inside your own app.

```python
from openmoderate import Moderator

mod = Moderator()
result = mod.analyze("upload.jpg")

if not result.is_safe:
    print(result.violations)
    # [Label(name='weapons', confidence=0.9612, parent='violence', threshold=0.5)]
```

> **Status: alpha (v0.1).** The Python API is usable today. The CLI, custom training, REST server and framework middleware are coming in the next releases — see the [roadmap](#roadmap).

## Install

```bash
pip install openmoderate
```

Requires Python 3.9+. The first call downloads the CLIP model weights (~600 MB) and caches them; after that everything runs offline. CPU works fine; CUDA and Apple Silicon (MPS) are used automatically when available.

## How it works

openmoderate uses [OpenCLIP](https://github.com/mlfoundations/open_clip), a vision-language model that understands images and text in the same embedding space. Each moderation category is described by a few natural-language prompts (e.g. *"a photo of a gun"*). An image is flagged for a category when it matches that category's prompts clearly better than a pool of ordinary "safe" prompts (portraits, food, landscapes, national flags, logos, kitchen knives...).

Because categories are just text, you can **add your own categories without any training data** — and when you do have data, a fine-tuned head (v0.2) sharpens accuracy for your use case.

## Usage

### Inputs

`analyze()` accepts a file path, `pathlib.Path`, URL, raw `bytes`, a file-like object (e.g. a Django/Flask upload) or a `PIL.Image`:

```python
mod.analyze("photo.png")
mod.analyze("https://example.com/photo.jpg")
mod.analyze(request.files["avatar"])        # Flask
mod.analyze(uploaded_file.read())           # bytes
results = mod.analyze_batch(["a.jpg", "b.jpg", "c.jpg"])   # faster for many images
```

### Results

```python
result.is_safe           # bool
result.violations        # labels that crossed their threshold
result.labels            # every category with its confidence, highest first
result.score("weapons")  # 0.9612
result.to_dict()         # JSON-serialisable
```

### Default categories

| Category | Parent | Default threshold |
|---|---|---|
| `nudity` | explicit | 0.50 |
| `sexual_activity` | explicit | 0.50 |
| `suggestive` | suggestive | 0.60 |
| `violence` | violence | 0.50 |
| `gore` | violence | 0.45 |
| `weapons` | violence | 0.50 |
| `hate_symbols` | hate | 0.50 |
| `drugs` | drugs | 0.50 |
| `self_harm` | self_harm | 0.45 |
| `alcohol` | substances | 0.60 |
| `tobacco` | substances | 0.60 |

### Tuning your policy

```python
# Stricter on weapons, ignore alcohol and tobacco
mod = Moderator(thresholds={"weapons": 0.3}, exclude=["alcohol", "tobacco"])

# Only check for explicit content
mod = Moderator(categories=["nudity", "sexual_activity"])
```

Or keep the policy in a YAML file:

```yaml
# policy.yaml
thresholds:
  weapons: 0.3
  suggestive: 0.8
disabled: [alcohol, tobacco]
custom_categories:
  - name: gambling
    prompts: ["a casino slot machine", "people gambling at a poker table"]
    negatives: ["people playing a board game"]   # benign look-alikes
    threshold: 0.5
```

```python
mod = Moderator("policy.yaml")
```

`negatives` are category-specific contrast prompts: things that look similar but should not count for *this* category (for example, the built-in `drugs` category treats cigarettes as a negative, because they belong to `tobacco`).

### Configuration via environment

| Variable | Purpose |
|---|---|
| `OPENMODERATE_CACHE_DIR` | Where model weights are cached |
| `OPENMODERATE_MODEL` / `OPENMODERATE_PRETRAINED` | Swap the OpenCLIP model (default `ViT-B-32` / `laion2b_s34b_b79k`) |
| `OPENMODERATE_MAX_BYTES` | Reject uploads larger than this (default 25 MB) |

## Accuracy and limitations

Be honest with yourself about what zero-shot moderation can do:

- It is **good at clear-cut cases** (a handgun, a swastika, a street fight, someone smoking) and at rejecting common look-alikes (national flags, kitchen knives, medicine).
- It **will miss subtle cases** and some objects (e.g. a plain glass of beer scores low on `alcohol`), and can be fooled by adversarial images.
- Thresholds were tuned on a small hand-labelled set of public-domain images. The explicit-content categories could not be validated on real explicit images by the maintainers — **evaluate on a sample of your own traffic before relying on it**, and adjust thresholds.
- For high-stakes moderation, use openmoderate as a first-pass filter and send borderline scores to human review.

Fine-tuning on your own labelled data (v0.2) is the recommended way to get production-grade accuracy for your domain.

## Roadmap

| Version | Scope |
|---|---|
| **v0.1** | Core zero-shot engine + Python API ✅ |
| v0.2 | `openmoderate` CLI (`scan`, `train`, `evaluate`) + fine-tuning on your own data |
| v0.3 | REST API server (`openmoderate serve`) + Docker image |
| v0.4 | Drop-in middleware for FastAPI, Flask and Django |
| v0.5 | Video moderation (frame sampling, timestamped violations) |
| v1.0 | Stable API, docs site, public benchmarks |

## Contributing

Contributions are welcome — better prompts, new categories, benchmark datasets and bug reports especially. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by protected characteristics. Moderation models make mistakes; give users a way to appeal automated decisions.

## License

[Apache 2.0](LICENSE)

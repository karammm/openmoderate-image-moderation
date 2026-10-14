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

> **Status: alpha (v0.3).** The Python API, the `openmoderate` CLI, training on your own data and the REST API server are usable today. Framework middleware and video are coming next — see the [roadmap](#roadmap).

## Install

```bash
pip install openmoderate
```

Requires Python 3.9+. The first call downloads the CLIP model weights (~600 MB) and caches them; after that everything runs offline. CPU works fine; CUDA and Apple Silicon (MPS) are used automatically when available.

## How it works

openmoderate uses [OpenCLIP](https://github.com/mlfoundations/open_clip), a vision-language model that understands images and text in the same embedding space. Each moderation category is described by a few natural-language prompts (e.g. *"a photo of a gun"*). An image is flagged for a category when it matches that category's prompts clearly better than a pool of ordinary "safe" prompts (portraits, food, landscapes, national flags, logos, kitchen knives...).

Because categories are just text, you can **add your own categories without any training data** — and when you do have data, a [trained head](#train-on-your-own-data) sharpens accuracy for your use case.

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

## Command line

```bash
openmoderate scan ./uploads                      # files, folders (recursive) or URLs
openmoderate scan ./uploads --json               # one JSON object per image
openmoderate scan ./uploads --fail-on-violation  # exit code 1 if anything is flagged (CI, cron)
openmoderate scan img.jpg -t weapons=0.3 --exclude alcohol tobacco
openmoderate categories                          # list categories and thresholds
openmoderate download                            # pre-fetch model weights for offline use
```

Exit codes for `scan`: `0` success, `1` something was flagged (only with `--fail-on-violation`), `2` some files could not be read.

## Train on your own data

Zero-shot works out of the box, but a head trained on *your* images is more accurate for your domain, and lets you add labels that are hard to describe in words.

**1. Arrange images in folders.** One folder per label, plus `safe/` for acceptable images:

```
dataset/
├── weapons/        # images that should be flagged as "weapons"
├── counterfeit/    # a brand-new label of your own
└── safe/           # a broad sample of your normal, acceptable traffic
```

An image that belongs to several labels can be copied into several folders.

**2. Train** (CPU is fine; a few hundred images takes about a minute):

```bash
openmoderate train ./dataset -o my_head.omh
```

This prints precision and recall on a held-out split, then saves a head trained on all the images.

**3. Use it:**

```python
mod = Moderator(head="my_head.omh")
```

```bash
openmoderate scan ./uploads --head my_head.omh
```

Labels that exist in both the head and the zero-shot categories (like `weapons` above) use the trained score by default. Pass `head_weight=0.5` (or `--head-weight 0.5`) to blend the two. New labels (like `counterfeit`) are added to the results.

**4. Evaluate** on a separate labelled folder that was not used for training:

```bash
openmoderate evaluate ./holdout --head my_head.omh
openmoderate evaluate ./holdout                 # measure the zero-shot defaults on your data
```

> **The `safe/` folder matters most.** The head learns what is *not* a violation from it. In our tests, a `dog` head trained with only cats and city photos in `safe/` scored 100% on held-out validation, yet flagged 6 of 20 unrelated photos (people, a meeting, a boxing match) as dogs. After adding 24 varied everyday photos to `safe/`, it flagged none. Fill `safe/` with a broad, representative sample of the images your users actually upload, and evaluate on images from outside the training set.

Heads are saved as `.omh` files: a NumPy archive with no pickle, so loading a head from someone else cannot run code.

## REST API server

Use openmoderate from any language over HTTP.

```bash
pip install "openmoderate[server]"
OPENMODERATE_API_KEY=change-me openmoderate serve --host 0.0.0.0 --port 8000
```

Or with Docker (model weights are baked into the image, so it runs offline):

```bash
docker build -t openmoderate .
docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me openmoderate
```

Interactive API docs are served at `http://localhost:8000/docs`.

| Endpoint | Body | Returns |
|---|---|---|
| `GET /health` | – | `{"status": "ok", "model_loaded": true}` (no API key needed) |
| `GET /v1/categories` | – | labels, parents and thresholds |
| `POST /v1/moderate` | multipart field `file` | one result |
| `POST /v1/moderate/batch` | multipart field `files` (repeat it) | `{"results": [...]}`; unreadable files get an `error` entry |
| `POST /v1/moderate/json` | `{"image_base64": "..."}` or `{"url": "..."}` | one result |

```bash
curl -H "X-API-Key: change-me" -F file=@upload.jpg http://localhost:8000/v1/moderate
```

```json
{
  "source": "upload.jpg",
  "is_safe": false,
  "violations": [{"name": "weapons", "confidence": 0.996, "parent": "violence", "threshold": 0.5}],
  "labels": [...]
}
```

```javascript
// Node.js
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("upload.jpg")]), "upload.jpg");
const res = await fetch("http://localhost:8000/v1/moderate", {
  method: "POST", headers: { "X-API-Key": "change-me" }, body: form,
});
const { is_safe, violations } = await res.json();
```

Server settings (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| `OPENMODERATE_API_KEY` | unset | Require this value in the `X-API-Key` header. **Set it whenever the port is reachable by others.** |
| `OPENMODERATE_ALLOW_URLS` | `false` | Allow `{"url": ...}` requests (see the security note below) |
| `OPENMODERATE_CONFIG` / `OPENMODERATE_HEAD` | unset | Policy YAML and trained head to load (also `--config` / `--head`) |
| `OPENMODERATE_MAX_BATCH` | `16` | Max files per batch request |
| `OPENMODERATE_MAX_BYTES` | 25 MB | Max size per image |
| `OPENMODERATE_PRELOAD` | `true` | Load the model at startup rather than on the first request |

**URL fetching is off by default.** A server that downloads any URL it is given can be tricked into reaching internal services (cloud metadata endpoints, admin panels). When you enable it, openmoderate only allows http(s), refuses private, loopback and link-local addresses, and re-checks every redirect. If untrusted callers can use the API, also route outbound traffic through an egress proxy.

Performance: a single-image request took 15–25 ms end to end on an Apple M-series laptop once the model was warm. CPU-only servers will be slower, so measure on your own hardware before sizing. Requests are processed one at a time per worker (PyTorch already uses all cores for each image). Use `--workers N` to run more processes; each loads its own copy of the model (~600 MB RAM).

## Accuracy and limitations

Be honest with yourself about what zero-shot moderation can do:

- It is **good at clear-cut cases** (a handgun, a swastika, a street fight, someone smoking) and at rejecting common look-alikes (national flags, kitchen knives, medicine).
- It **will miss subtle cases** and some objects (e.g. a plain glass of beer scores low on `alcohol`), and can be fooled by adversarial images.
- Thresholds were tuned on a small hand-labelled set of public-domain images. The explicit-content categories could not be validated on real explicit images by the maintainers — **evaluate on a sample of your own traffic before relying on it**, and adjust thresholds.
- For high-stakes moderation, use openmoderate as a first-pass filter and send borderline scores to human review.

[Training a head on your own labelled data](#train-on-your-own-data) is the recommended way to get production-grade accuracy for your domain.

## Roadmap

| Version | Scope |
|---|---|
| **v0.1** | Core zero-shot engine + Python API ✅ |
| **v0.2** | `openmoderate` CLI (`scan`, `train`, `evaluate`) + training on your own data ✅ |
| **v0.3** | REST API server (`openmoderate serve`) + Docker image ✅ |
| v0.4 | Drop-in middleware for FastAPI, Flask and Django |
| v0.5 | Video moderation (frame sampling, timestamped violations) |
| v1.0 | Stable API, docs site, public benchmarks |

## Contributing

Contributions are welcome — better prompts, new categories, benchmark datasets and bug reports especially. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by protected characteristics. Moderation models make mistakes; give users a way to appeal automated decisions.

## License

[Apache 2.0](LICENSE)

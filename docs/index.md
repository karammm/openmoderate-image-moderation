# openmoderate

**Open-source, self-hosted image and video content moderation for Python.** Detect nudity, sexual content, violence, gore, weapons, hate symbols, drugs, self-harm, alcohol and tobacco in uploaded images and videos — with one `pip install`, no cloud account, no per-image fees, and no ML experience needed.

Think of it as an open alternative to Amazon Rekognition's `DetectModerationLabels` that runs inside your own app.

![Terminal demo: openmoderate scans a folder, flagging a pistol, a riot and a swastika while a beach, a dog and a US flag pass as safe; then the REST server flags a cigarette photo as tobacco.](assets/demo.svg)

## Install

```bash
pip install openmoderate
```

Requires Python 3.9+. The first call downloads the CLIP model weights (~600 MB) and caches them; after that everything runs offline. CPU works fine; CUDA and Apple Silicon (MPS) are used automatically when available.

On a CPU-only Linux server you can save ~2 GB by installing the CPU build of PyTorch first. Install `torch` and `torchvision` **together** from the same index, otherwise their versions won't match:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install openmoderate
```

Optional extras: `openmoderate[server]` (REST API), `[video]`, `[fastapi]`, `[flask]`, `[django]`.

## Quick start

```python
from openmoderate import Moderator

mod = Moderator()
result = mod.analyze("upload.jpg")

if not result.is_safe:
    print(result.violations)
    # [Label(name='weapons', confidence=0.9612, parent='violence', threshold=0.5)]
```

![How openmoderate works](assets/how-it-works.svg)

## Where to go next

| I want to… | Read |
|---|---|
| Understand how scoring works and what to expect | [How it works](guide/concepts.md) |
| Call it from Python and tune the policy | [Python API](guide/python.md) |
| Scan folders from a terminal or CI | [Command line](guide/cli.md) |
| Improve accuracy with my own images | [Train on your own data](guide/training.md) |
| Moderate videos | [Videos](guide/video.md) |
| Protect uploads in FastAPI, Flask or Django | [Web framework integrations](guide/integrations.md) |
| Call it over HTTP from another language | [REST API server](guide/server.md) |
| See measured accuracy | [Benchmarks](benchmarks.md) |

## Versioning

openmoderate follows [semantic versioning](https://semver.org/) from 1.0: everything importable from the top-level `openmoderate` package, the integration modules, the CLI flags, the REST endpoints and the `.omh` head format are stable within a major version. Default prompts, thresholds and the scores they produce may be tuned in minor releases to improve accuracy; such changes are always listed in the [changelog](changelog.md). Pin the minor version if you need bit-identical scores.

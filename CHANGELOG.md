# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-10-14

### Added
- Framework integrations under `openmoderate.integrations`:
  - FastAPI: `ModeratedFile` / `ModeratedFiles` and `moderated()` / `moderated_files()`
    dependencies, with moderation off the event loop.
  - Flask: `@moderate_uploads(...)` decorator and an `OpenModerate` extension that can check
    every request.
  - Django: `ModerationValidator` (models, forms, admin, DRF; migration-safe) and
    `ModerationMiddleware` for URL prefixes, configured via `settings.OPENMODERATE`.
- One shared model per process; per-endpoint policies reuse it instead of loading another copy.
- Uploads are rewound after checking so applications can save them normally.
- Error responses hide confidence scores by default (`include_scores=True` to show them).
- Extras: `openmoderate[fastapi]`, `[flask]`, `[django]`; runnable example apps for each.
- README infographic (`docs/assets/how-it-works.svg`) and animated terminal demo
  (`docs/assets/demo.svg`), both following GitHub's light/dark theme. Regenerate with
  `python scripts/make_readme_graphics.py`.

### Changed
- The test suite's fake engine uses exactly orthogonal text vectors, making multi-label
  assertions deterministic.

## [0.3.0] - 2026-10-14

### Added
- REST API server (`pip install "openmoderate[server]"`, `openmoderate serve`), built on FastAPI:
  `GET /health`, `GET /v1/categories`, `POST /v1/moderate` (multipart), `POST /v1/moderate/batch`
  (multipart, per-file errors) and `POST /v1/moderate/json` (base64 or URL).
- Optional API-key authentication via `OPENMODERATE_API_KEY` (constant-time comparison).
- URL fetching, off by default (`OPENMODERATE_ALLOW_URLS`), with SSRF protection: http(s) only,
  no private, loopback or link-local addresses, every redirect re-validated, size and time limits.
- Upload size and batch limits, model preloading at startup, and a warning when serving on a public
  interface without an API key.
- Dockerfile (CPU torch, non-root user, model weights baked in, healthcheck) and a CI job that
  builds and smoke-tests the image.
- CI also runs on `release/**` branches, checks that the model stack imports, and reports
  failures as annotations.

### Fixed
- Docker image and CI now install `torch` and `torchvision` from the same CPU index (a mismatch
  broke `import open_clip`).

## [0.2.0] - 2026-10-14

### Added
- `openmoderate` command-line tool with `scan`, `train`, `evaluate`, `categories` and `download` commands.
- `scan` supports files, recursive folders and URLs, JSON-lines output, policy flags and `--fail-on-violation` for CI.
- Training on your own data: folder datasets (`dataset/<label>/`, `safe/`), a class-balanced linear head on frozen CLIP embeddings, held-out precision/recall/F1, then a refit on all data.
- `Moderator(head=..., head_weight=...)` adds trained labels and blends them with zero-shot categories.
- `.omh` head format (NumPy archive plus JSON metadata, no pickle), with a check that the head's model matches the moderator's.
- `Moderator.label_specs` and `Moderator.thresholds` properties.
- `train` warns when the `safe/` folder is too small to teach the head what normal traffic looks like.

## [0.1.0] - 2026-10-14

### Added
- `Moderator` with zero-shot image moderation powered by OpenCLIP (`ViT-B-32`, LAION-2B).
- 11 default categories: nudity, sexual_activity, suggestive, violence, gore, weapons, hate_symbols, drugs, self_harm, alcohol, tobacco.
- Calibrated per-category scores with configurable thresholds, plus category-specific `negatives` (benign look-alikes).
- Policy configuration from kwargs, dict or YAML, including custom categories.
- Image loading from paths, URLs, bytes, file objects and PIL images, with EXIF rotation, transparency flattening and size limits.
- `analyze_batch()` for efficient multi-image scoring.

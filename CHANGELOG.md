# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.2] - 2026-10-15

### Changed
- Redesigned README: logo for light and dark themes, quick start, "Why openmoderate", an install
  table, collapsible usage examples for every interface, the machine-learning model, the full
  accuracy table, quality checks and community links. It renders the same on GitHub and PyPI.
- No code changes: scores and behaviour are identical to 1.1.1.

## [1.1.1] - 2026-10-15

### Changed
- README explains the machine-learning model (CLIP, the zero-shot scoring pipeline, supervised
  fine-tuning, model sizes and speeds) and shows the full accuracy results: per-category recall
  and false-positive rate for every preset, cross-validated recall, method and limits.
- Commit history is attributed to the project owner only.
- No code changes: scores and behaviour are identical to 1.1.0.

## [1.1.0] - 2026-10-14

### Added
- Model presets: `Moderator(preset="fast" | "balanced" | "accurate")`, `--preset` on every CLI
  command, `preset:` in policy files, `OPENMODERATE_PRESET` for the server and integrations, and
  a `docker build --build-arg OPENMODERATE_PRESET=...` option. `accurate` (CLIP ViT-L/14) reaches
  82% average recall with 4.2% of safe images flagged on the benchmark, versus 77% / 6.5% for
  `fast`; `balanced` (ViT-B/16) matches `fast`'s recall with 4.7% flagged. Calibrations follow a
  single rule (best recall with at most ~5% of safe images flagged) and were compared with 2-fold
  cross-validation.
- `PRESETS` and `ModerationConfig.from_preset()` / `ModerationConfig.default()`.
- `benchmark/run.py --preset`.

### Unchanged
- The default (`fast`) model, calibration and scores are identical to 1.0.x; existing trained
  heads keep working.

## [1.0.2] - 2026-10-14

### Added
- Python 3.13 and 3.14 are tested in CI and listed as supported.
- Unit tests for image loading (`openmoderate.io`): input types, transparency handling, size limits and file discovery.

## [1.0.1] - 2026-10-14

First release on PyPI: `pip install openmoderate`.

### Added
- Docker image published to `ghcr.io/karammm/openmoderate` on every release, smoke-tested
  before it is pushed.
- Release pages now start with copy-paste install commands and link to the docs,
  benchmarks and the full diff.
- README badges, `CITATION.cff`, `CODE_OF_CONDUCT.md`, Dependabot updates and a social
  preview card.

### Changed
- GitHub Actions updated to their current major versions.
- Releases publish to PyPI through trusted publishing on every version tag.

## [1.0.0] - 2026-10-14

First stable release. The public API (everything importable from `openmoderate`, the
integration modules, CLI flags, REST endpoints and the `.omh` format) now follows semantic
versioning; default prompts and thresholds may still be tuned in minor releases.

### Added
- Public, reproducible benchmark (`benchmark/`): 475 hand-reviewed, openly licensed
  Wikimedia Commons photos across weapons, hate symbols, alcohol, tobacco, drugs, violence,
  safe images and look-alikes, with a dev/test split. `python benchmark/run.py` reproduces
  the published numbers.
- Documentation site (MkDocs) with guides, benchmarks and an API reference generated from
  the docstrings, deployed to GitHub Pages.
- Release automation: pushing a `vX.Y.Z` tag builds the package, creates the GitHub
  release from the changelog and (once enabled) publishes to PyPI.
- Type information (`py.typed`) and `mypy` in CI.
- Top-level exports: `LabelSpec`, `LinearHead`, `ImageLoadError`, `VideoLoadError`,
  `VideoModerationResult`, `VideoSegment`, `SAFE_PROMPTS`.
- `SECURITY.md`, issue templates (including a misclassification report that asks people
  not to attach harmful images) and a pull-request template.

### Changed
- More complete default prompts, measured on the held-out test half: `drugs` recall 15% →
  85%, `alcohol` 53% → 84%, `tobacco` 44% → 59%, `hate_symbols` 50% → 61%, with the safe
  false-positive rate at 6% (was 5%). New safe look-alikes: milk, juice, coffee; kitchen
  knives are now a `weapons` negative.
- `integrations.configure()` takes the moderator as a positional-only argument.
- The README is now an overview; detailed guides moved to the docs site.

## [0.5.0] - 2026-10-14

### Added
- Video moderation (`pip install "openmoderate[video]"`): `Moderator.analyze_video()` samples
  frames, scores them in batches and returns timestamped `segments` per violated label, with
  `fps`, `min_frames`, `stop_on_violation`, `max_duration` and `keep_frame_scores` options.
- `openmoderate scan` handles video files (`--fps`, `--min-frames`, `--max-duration`).
- REST endpoint `POST /v1/moderate/video`, streamed to disk with size and duration limits
  (`OPENMODERATE_MAX_VIDEO_BYTES`, `OPENMODERATE_MAX_VIDEO_SECONDS`). Docker image includes
  video support.
- Decoding limits enforced while decoding (frame size, decoded frames, duration), not taken
  from the file's metadata.
- Border trimming (`trim_borders`, on by default): letterbox bars and uniform padding are
  cropped before scoring, for images, video frames, training and evaluation alike.

### Changed
- Border trimming changes some scores. On our test set it removed a false `sexual_activity`
  detection on letterboxed video and turned a missed `alcohol` detection (a glass of wine on
  a plain background, 0.54) into a hit (0.78). Set `trim_borders: false` to keep the old
  behaviour.

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

# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

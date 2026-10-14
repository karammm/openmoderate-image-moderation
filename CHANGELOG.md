# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-14

### Added
- `Moderator` with zero-shot image moderation powered by OpenCLIP (`ViT-B-32`, LAION-2B).
- 11 default categories: nudity, sexual_activity, suggestive, violence, gore, weapons, hate_symbols, drugs, self_harm, alcohol, tobacco.
- Calibrated per-category scores with configurable thresholds, plus category-specific `negatives` (benign look-alikes).
- Policy configuration from kwargs, dict or YAML, including custom categories.
- Image loading from paths, URLs, bytes, file objects and PIL images, with EXIF rotation, transparency flattening and size limits.
- `analyze_batch()` for efficient multi-image scoring.

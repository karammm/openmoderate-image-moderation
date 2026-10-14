# Contributing to openmoderate

Thanks for helping make open moderation better!

## Development setup

```bash
git clone https://github.com/karammm/openmoderate-image-moderation.git
cd openmoderate-image-moderation
python -m venv .venv && source .venv/bin/activate   # Python 3.9+
pip install -e ".[dev]"
```

## Running checks

```bash
ruff check src tests      # lint
ruff format src tests     # format
pytest                    # fast unit tests (uses a fake engine, no model download)
pytest -m slow            # smoke test against the real CLIP model (~600 MB download)
```

## Guidelines

- Keep pull requests focused; add tests for behaviour changes.
- **Never commit explicit, violent or otherwise harmful images** to the repository. Unit tests use synthetic images and a fake engine. If you improve prompts or thresholds, describe your evaluation set in the PR (source, size, licence) instead of committing it.
- Prompt and threshold changes should include before/after numbers on the images you evaluated.
- Update `CHANGELOG.md` under "Unreleased".

## Releasing (maintainers)

1. Bump `__version__` in `src/openmoderate/__init__.py` and move "Unreleased" notes in `CHANGELOG.md` under the new version.
2. Commit, then `git tag vX.Y.Z && git push origin main --tags`.
3. Create a GitHub release for the tag — the `release` workflow builds and publishes to PyPI.

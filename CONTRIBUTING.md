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

1. Bump `__version__` in `src/openmoderate/__init__.py` and move the "Unreleased" notes in
   `CHANGELOG.md` under a new `## [X.Y.Z] - YYYY-MM-DD` heading.
2. Merge to `main`.

That's all. When CI passes on a commit whose version has no tag yet, the `Release`
workflow tags it `vX.Y.Z`, builds the package, creates the GitHub release (install
commands, the changelog section and links, with the wheel and sdist attached), publishes
to PyPI, and smoke-tests and publishes the Docker image to `ghcr.io/karammm/openmoderate`
as `X.Y.Z`, `X.Y` and `latest`. If CI fails, nothing is released. Pushing a `vX.Y.Z` tag
by hand runs the same pipeline.

### One-time setup

**PyPI publishing** uses [trusted publishing](https://docs.pypi.org/trusted-publishers/):
the `openmoderate` project on PyPI trusts the `release.yml` workflow of this repository
(environment `pypi`), so no API token is stored anywhere. To move the project, update the
publisher under the project's *Settings → Publishing* on PyPI.

**Docs site:** in the GitHub repo, *Settings → Pages → Build and deployment → Source*,
choose **GitHub Actions**, then add the repository variable `DOCS_DEPLOY` = `true`. The
`Docs` workflow then deploys on every push to `main` (re-run it once to publish now).

**Social preview:** upload `docs/assets/social-preview.png` under *Settings → General →
Social preview* (GitHub has no API for this). Regenerate it with
`python scripts/make_readme_graphics.py` and a headless browser screenshot of the SVG.

## Benchmark

`python benchmark/run.py` measures accuracy on openly licensed Wikimedia Commons images
(see [`benchmark/README.md`](benchmark/README.md)). Run it before and after any change to
prompts, thresholds or scoring, and include both tables in your pull request.

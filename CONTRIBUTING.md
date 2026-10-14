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
2. Merge to `main` once CI is green.
3. Tag and push: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.

The `Release` workflow then checks the tag matches `__version__`, builds the package,
creates the GitHub release with the changelog section as notes (attaching the wheel and
sdist), and backfills release pages for any older tags that lack one.

### One-time setup

**PyPI publishing** (until this is done, releases go to GitHub only):

1. Create an account on [pypi.org](https://pypi.org/account/register/) and enable 2FA.
2. Go to *Your account → Publishing → Add a new pending publisher* and enter:
   PyPI project name `openmoderate`, owner `karammm`, repository
   `openmoderate-image-moderation`, workflow `release.yml`, environment `pypi`.
3. In the GitHub repo, *Settings → Secrets and variables → Actions → Variables*, add
   `PYPI_PUBLISH` = `true`.
4. Publish by re-running the `Release` workflow for the latest tag, or with the next tag.

**Docs site:** in the GitHub repo, *Settings → Pages → Build and deployment → Source*,
choose **GitHub Actions**, then add the repository variable `DOCS_DEPLOY` = `true`. The
`Docs` workflow then deploys on every push to `main` (re-run it once to publish now).

## Benchmark

`python benchmark/run.py` measures accuracy on openly licensed Wikimedia Commons images
(see [`benchmark/README.md`](benchmark/README.md)). Run it before and after any change to
prompts, thresholds or scoring, and include both tables in your pull request.

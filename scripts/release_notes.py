"""Compose GitHub release notes: install instructions, the CHANGELOG section and links.

python scripts/release_notes.py v1.0.0 [--previous v0.5.0]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changelog_section import CHANGELOG, section  # noqa: E402

REPO = "https://github.com/karammm/openmoderate-image-moderation"
DOCS = "https://karammm.github.io/openmoderate-image-moderation"
IMAGE = "ghcr.io/karammm/openmoderate"


def previous_tag(tag: str) -> str | None:
    """The version tag released just before ``tag`` (by version order), if any."""
    try:
        tags = subprocess.run(
            ["git", "tag", "--list", "v*", "--sort=version:refname"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None
    earlier = tags[: tags.index(tag)] if tag in tags else tags
    return earlier[-1] if earlier else None


def notes(tag: str, previous: str | None, changelog: str) -> str:
    version = tag.lstrip("v")
    body = section(tag, changelog).strip()
    compare = (
        f"[`{previous}...{tag}`]({REPO}/compare/{previous}...{tag})"
        if previous
        else f"[all commits]({REPO}/commits/{tag})"
    )
    footer = " · ".join(
        [
            f"📖 [Documentation]({DOCS}/)",
            f"📊 [Benchmarks]({DOCS}/benchmarks/)",
            f"🔒 [Security policy]({REPO}/blob/main/SECURITY.md)",
            f"Full diff: {compare}",
        ]
    )
    return f"""## Install

```bash
pip install openmoderate=={version}                 # Python library + CLI
pip install "openmoderate[server,video]=={version}"   # + REST server and video
docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me {IMAGE}:{version}
```

## What's changed

{body}

---

{footer}
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag")
    parser.add_argument("--previous", help="Previous tag (default: detected from git)")
    args = parser.parse_args()
    text = CHANGELOG.read_text(encoding="utf-8")
    sys.stdout.write(notes(args.tag, args.previous or previous_tag(args.tag), text))

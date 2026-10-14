"""Print the CHANGELOG.md section for one version, for use as GitHub release notes.

python scripts/changelog_section.py v1.0.0
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def section(version: str, text: str) -> str:
    version = version.lstrip("v")
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*$", re.MULTILINE)
    match = heading.search(text)
    if not match:
        raise SystemExit(f"No CHANGELOG entry for {version}")
    nxt = re.compile(r"^## \[", re.MULTILINE).search(text, match.end())
    body = text[match.end() : nxt.start() if nxt else len(text)].strip()
    return body + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    sys.stdout.write(section(sys.argv[1], CHANGELOG.read_text(encoding="utf-8")))

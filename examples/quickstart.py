"""Scan a file, folder or URL and print the verdict for each image.

python examples/quickstart.py path/to/image_or_folder
"""

import sys

from openmoderate import Moderator
from openmoderate.io import iter_image_files


def main(target: str) -> None:
    mod = Moderator()
    sources = [target] if target.startswith("http") else iter_image_files(target)
    for result in mod.analyze_batch(sources):
        verdict = "SAFE" if result.is_safe else "FLAGGED"
        details = ", ".join(f"{v.name} ({v.confidence:.0%})" for v in result.violations)
        print(f"{verdict:8} {result.source}  {details}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")

"""Folder datasets: ``root/<label>/*.jpg``.

Images in a folder named ``safe`` (configurable) are negatives for every label. An image
may belong to several labels by appearing in several folders; duplicates are matched by
file content, so copying the same file into ``weapons/`` and ``violence/`` makes it a
positive for both.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from openmoderate.engine.base import Engine
from openmoderate.io import IMAGE_EXTENSIONS, load_image, trim_borders

DEFAULT_SAFE_LABEL = "safe"


@dataclass
class FolderDataset:
    paths: list[Path]
    labels: list[str]  # violation labels, excluding the safe label
    targets: np.ndarray  # (n_images, n_labels) of 0/1

    @classmethod
    def from_folder(cls, root: str | Path, safe_label: str = DEFAULT_SAFE_LABEL) -> FolderDataset:
        root = Path(root)
        if not root.is_dir():
            raise FileNotFoundError(f"Dataset folder not found: {root}")
        folders = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
        labels = [f.name for f in folders if f.name != safe_label]
        if not labels:
            raise ValueError(
                f"{root} needs at least one label folder besides '{safe_label}/', "
                "e.g. weapons/ and safe/"
            )

        by_digest: dict[str, int] = {}
        paths: list[Path] = []
        rows: list[np.ndarray] = []
        for folder in folders:
            for path in sorted(folder.rglob("*")):
                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
                digest = hashlib.sha1(path.read_bytes()).hexdigest()
                if digest not in by_digest:
                    by_digest[digest] = len(paths)
                    paths.append(path)
                    rows.append(np.zeros(len(labels), dtype=np.float32))
                if folder.name != safe_label:
                    rows[by_digest[digest]][labels.index(folder.name)] = 1.0

        if not paths:
            raise ValueError(f"No images found under {root}")
        return cls(paths=paths, labels=labels, targets=np.stack(rows))

    def __len__(self) -> int:
        return len(self.paths)

    def summary(self) -> dict[str, int]:
        counts = {label: int(self.targets[:, i].sum()) for i, label in enumerate(self.labels)}
        counts["(no label)"] = int((self.targets.sum(axis=1) == 0).sum())
        return counts

    def embed(
        self,
        engine: Engine,
        batch_size: int = 32,
        verbose: bool = False,
        trim: bool = True,
    ) -> np.ndarray:
        """Encode every image with ``engine``. Unreadable images raise immediately.

        ``trim`` must match the moderator's ``trim_borders`` setting so a head is trained on
        the same view of the images it will score.
        """
        out = []
        for i in range(0, len(self.paths), batch_size):
            batch = [load_image(p) for p in self.paths[i : i + batch_size]]
            if trim:
                batch = [trim_borders(im) for im in batch]
            out.append(engine.encode_images(batch))
            if verbose:
                done = min(i + batch_size, len(self.paths))
                print(f"\rEmbedding images: {done}/{len(self.paths)}", end="", file=sys.stderr)
        if verbose:
            print(file=sys.stderr)
        return np.concatenate(out, axis=0)

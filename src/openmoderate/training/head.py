"""A trained linear classification head on top of frozen CLIP image embeddings.

Heads are stored as ``.omh`` files: a NumPy ``.npz`` archive holding the weights plus a
JSON metadata blob. No pickle is involved, so loading a head from an untrusted source
cannot execute code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

FORMAT_VERSION = 1


@dataclass
class LinearHead:
    """One-vs-rest logistic regression: ``sigmoid(embeddings @ weights.T + bias)``."""

    labels: list[str]
    weights: np.ndarray  # (n_labels, dim)
    bias: np.ndarray  # (n_labels,)
    thresholds: dict[str, float] = field(default_factory=dict)
    parents: dict[str, str | None] = field(default_factory=dict)
    model_name: str | None = None
    pretrained: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.weights = np.asarray(self.weights, dtype=np.float32)
        self.bias = np.asarray(self.bias, dtype=np.float32)
        if self.weights.shape != (len(self.labels), self.weights.shape[-1]):
            raise ValueError("weights must have shape (n_labels, dim)")
        if self.bias.shape != (len(self.labels),):
            raise ValueError("bias must have shape (n_labels,)")

    @property
    def dim(self) -> int:
        return int(self.weights.shape[1])

    def predict(self, embeddings: np.ndarray) -> np.ndarray:
        """Probabilities of shape ``(n_images, n_labels)``."""
        z = embeddings.astype(np.float32) @ self.weights.T + self.bias
        return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        meta = {
            "format_version": FORMAT_VERSION,
            "labels": self.labels,
            "thresholds": self.thresholds,
            "parents": self.parents,
            "model_name": self.model_name,
            "pretrained": self.pretrained,
            "metrics": self.metrics,
        }
        with open(path, "wb") as fh:
            np.savez(fh, weights=self.weights, bias=self.bias, meta=np.array(json.dumps(meta)))
        return path

    @classmethod
    def load(cls, path: str | Path) -> LinearHead:
        with np.load(path, allow_pickle=False) as data:
            meta = json.loads(str(data["meta"]))
            if meta.get("format_version", 0) > FORMAT_VERSION:
                raise ValueError(
                    f"{path} was written by a newer openmoderate; please upgrade the package"
                )
            return cls(
                labels=list(meta["labels"]),
                weights=data["weights"],
                bias=data["bias"],
                thresholds={k: float(v) for k, v in meta.get("thresholds", {}).items()},
                parents=meta.get("parents", {}),
                model_name=meta.get("model_name"),
                pretrained=meta.get("pretrained"),
                metrics=meta.get("metrics", {}),
            )

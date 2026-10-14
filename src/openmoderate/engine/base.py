"""Engine interface: anything that maps images and texts into a shared embedding space."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from PIL import Image


@runtime_checkable
class Engine(Protocol):
    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        """Return L2-normalised embeddings of shape ``(len(images), dim)``."""
        ...

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        """Return L2-normalised embeddings of shape ``(len(texts), dim)``."""
        ...

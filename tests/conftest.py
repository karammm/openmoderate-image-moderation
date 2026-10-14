from __future__ import annotations

import hashlib

import numpy as np
import pytest
from PIL import Image

DIM = 512


def _vec(text: str) -> np.ndarray:
    seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "little")
    v = np.random.default_rng(seed).standard_normal(DIM)
    return v / np.linalg.norm(v)


class FakeEngine:
    """Deterministic stand-in for CLIP.

    Every text gets a pseudo-random unit vector. An image's embedding is the vector of the
    prompt registered for its solid colour, so tests can say "a red image looks like a gun".
    """

    def __init__(self, color_to_prompt: dict[tuple[int, int, int], str] | None = None):
        self.color_to_prompt = color_to_prompt or {}
        self.text_calls = 0

    def encode_texts(self, texts):
        self.text_calls += 1
        return np.stack([_vec(t) for t in texts])

    def encode_images(self, images):
        out = []
        for im in images:
            color = im.getpixel((0, 0))
            out.append(_vec(self.color_to_prompt.get(color, "unrelated image")))
        return np.stack(out)


def solid(color, size=(32, 32)) -> Image.Image:
    return Image.new("RGB", size, color)


@pytest.fixture
def fake_engine():
    return FakeEngine(
        {
            (255, 0, 0): "a photo of a gun",
            (0, 255, 0): "a photo of a landscape or nature scene",
            (0, 0, 255): "a nazi swastika flag",
        }
    )

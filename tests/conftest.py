from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

DIM = 512
# The first dimensions are reserved for ColorEngine's colour features.
_RESERVED = 8
_TEXT_INDEX: dict[str, int] = {}


def _vec(text: str) -> np.ndarray:
    """A one-hot vector per distinct text.

    Exactly orthogonal vectors keep scores deterministic: unrelated content has
    similarity 0, so no category can win by random overlap at CLIP's x100 logit scale.
    """
    if text not in _TEXT_INDEX:
        _TEXT_INDEX[text] = _RESERVED + len(_TEXT_INDEX)
        if _TEXT_INDEX[text] >= DIM:
            raise RuntimeError("FakeEngine ran out of dimensions; raise DIM")
    v = np.zeros(DIM)
    v[_TEXT_INDEX[text]] = 1.0
    return v


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


class ColorEngine(FakeEngine):
    """Image embedding = normalised mean RGB colour (padded), so colours are learnable."""

    def encode_images(self, images):
        out = []
        for im in images:
            v = np.zeros(DIM)
            v[:3] = np.asarray(im, dtype=float).reshape(-1, 3).mean(axis=0) / 255.0
            v[3] = 0.2
            out.append(v / np.linalg.norm(v))
        return np.stack(out)


def make_dataset(root, n=12, seed=0):
    """root/weapons (reddish), root/drugs (bluish), root/safe (greenish)."""
    rng = np.random.default_rng(seed)
    bases = {"weapons": (220, 30, 30), "drugs": (30, 30, 220), "safe": (30, 200, 30)}
    for label, base in bases.items():
        folder = root / label
        folder.mkdir(parents=True)
        for i in range(n):
            color = tuple(int(np.clip(c + rng.integers(-25, 25), 0, 255)) for c in base)
            solid(color).save(folder / f"{i}.png")
    return root


def png_bytes(color) -> bytes:
    import io

    buf = io.BytesIO()
    solid(color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def shared_fake(fake_engine):
    """Point every framework integration at a Moderator backed by the fake engine."""
    from openmoderate import Moderator
    from openmoderate.integrations import configure

    configure(Moderator(engine=fake_engine))
    yield fake_engine
    configure()


class NearestColorEngine(FakeEngine):
    """Like FakeEngine, but matches an image's mean colour to the nearest registered colour.

    Lossy video codecs shift colours slightly, so exact pixel lookup would miss.
    """

    def encode_images(self, images):
        out = []
        for im in images:
            mean = np.asarray(im, dtype=float).reshape(-1, 3).mean(axis=0)
            best, best_dist = "unrelated image", 60.0
            for color, prompt in self.color_to_prompt.items():
                dist = float(np.linalg.norm(mean - np.array(color)))
                if dist < best_dist:
                    best, best_dist = prompt, dist
            out.append(_vec(best))
        return np.stack(out)


RED_GUN = {(255, 0, 0): "a photo of a gun", (0, 255, 0): "a photo of a landscape or nature scene"}


def make_video(path, segments, fps=10, size=(64, 48)):
    """Write a video made of solid-colour stretches: segments = [((r, g, b), seconds), ...]."""
    cv2 = pytest.importorskip("cv2")
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for (r, g, b), seconds in segments:
        frame = np.full((size[1], size[0], 3), (b, g, r), np.uint8)  # OpenCV is BGR
        for _ in range(round(seconds * fps)):
            writer.write(frame)
    writer.release()
    return path

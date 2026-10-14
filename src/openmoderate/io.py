"""Load images from the many shapes an upload can take."""

from __future__ import annotations

import io
import os
import urllib.request
from pathlib import Path
from typing import IO, Union

import numpy as np
from PIL import Image, ImageOps

ImageInput = Union[str, os.PathLike, bytes, bytearray, IO[bytes], Image.Image]

MAX_BYTES = int(os.getenv("OPENMODERATE_MAX_BYTES", 25 * 1024 * 1024))
# Guard against decompression bombs while still allowing large photos.
Image.MAX_IMAGE_PIXELS = int(os.getenv("OPENMODERATE_MAX_PIXELS", 90_000_000))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


class ImageLoadError(ValueError):
    pass


def _read_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "openmoderate"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - caller-supplied URL
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ImageLoadError(f"Image at {url} exceeds {MAX_BYTES} bytes")
    return data


def load_image(source: ImageInput) -> Image.Image:
    """Return an RGB :class:`PIL.Image.Image` from a path, URL, bytes, file object or PIL image."""
    try:
        if isinstance(source, Image.Image):
            img = source
        elif isinstance(source, (bytes, bytearray)):
            if len(source) > MAX_BYTES:
                raise ImageLoadError(f"Image exceeds {MAX_BYTES} bytes")
            img = Image.open(io.BytesIO(bytes(source)))
        elif isinstance(source, str) and source.startswith(("http://", "https://")):
            img = Image.open(io.BytesIO(_read_url(source)))
        elif isinstance(source, (str, os.PathLike)):
            path = Path(source)
            if path.stat().st_size > MAX_BYTES:
                raise ImageLoadError(f"{path} exceeds {MAX_BYTES} bytes")
            img = Image.open(path)
        elif hasattr(source, "read"):
            data = source.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ImageLoadError(f"Image exceeds {MAX_BYTES} bytes")
            img = Image.open(io.BytesIO(data))
        else:
            raise ImageLoadError(f"Unsupported image input type: {type(source).__name__}")

        img.load()
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            if img.mode in ("RGBA", "LA", "P"):
                # Composite transparency onto white so hidden content can't hide in alpha.
                rgba = img.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                img = background
            else:
                img = img.convert("RGB")
        return img
    except ImageLoadError:
        raise
    except Exception as exc:  # PIL raises many exception types
        raise ImageLoadError(f"Could not load image: {exc}") from exc


def trim_borders(img: Image.Image, tolerance: int = 20, min_content: float = 0.2) -> Image.Image:
    """Crop uniform borders (letterbox/pillarbox bars, padding) around the content.

    Bars change what CLIP "sees": on our test video, black letterbox bars pushed a pistol
    frame's ``sexual_activity`` score from 0.01 to 0.65. The background colour is taken
    from the corners; nothing is cropped if the content would be under ``min_content`` of
    the frame (e.g. a mostly uniform image), so this can only zoom in on real content.
    """
    gray = np.asarray(img.convert("L"), dtype=np.int16)
    h, w = gray.shape
    if h < 8 or w < 8:
        return img
    background = np.median([gray[0, 0], gray[0, -1], gray[-1, 0], gray[-1, -1]])
    content = np.abs(gray - background) > tolerance
    rows = np.flatnonzero(content.mean(axis=1) > 0.02)
    cols = np.flatnonzero(content.mean(axis=0) > 0.02)
    if not len(rows) or not len(cols):
        return img
    left, top, right, bottom = cols[0], rows[0], cols[-1] + 1, rows[-1] + 1
    if (right - left) * (bottom - top) < min_content * w * h:
        return img
    if (left, top, right, bottom) == (0, 0, w, h):
        return img
    return img.crop((int(left), int(top), int(right), int(bottom)))


def describe_source(source: ImageInput) -> str | None:
    if isinstance(source, (str, os.PathLike)):
        return str(source)
    name = getattr(source, "name", None) or getattr(source, "filename", None)
    return str(name) if name else None


def iter_image_files(root: str | os.PathLike) -> list[Path]:
    root = Path(root)
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)

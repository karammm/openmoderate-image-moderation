import io

import pytest
from PIL import Image

from openmoderate import io as omio
from openmoderate.io import (
    ImageLoadError,
    describe_source,
    iter_image_files,
    load_image,
)


def _png_bytes(mode="RGB", color=(10, 20, 30), size=(8, 8)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_load_image_from_bytes_path_and_file_object(tmp_path):
    data = _png_bytes()
    path = tmp_path / "a.png"
    path.write_bytes(data)
    for source in (data, bytearray(data), path, str(path), io.BytesIO(data)):
        img = load_image(source)
        assert img.mode == "RGB"
        assert img.size == (8, 8)


def test_load_image_composites_transparency_onto_white():
    img = load_image(_png_bytes("RGBA", (0, 0, 0, 0)))
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_load_image_converts_grayscale_to_rgb():
    assert load_image(_png_bytes("L", 100)).mode == "RGB"


def test_load_image_rejects_garbage_and_unsupported_types():
    with pytest.raises(ImageLoadError):
        load_image(b"not an image")
    with pytest.raises(ImageLoadError, match="Unsupported"):
        load_image(12345)  # type: ignore[arg-type]


def test_load_image_rejects_missing_file(tmp_path):
    with pytest.raises(ImageLoadError):
        load_image(tmp_path / "missing.png")


def test_load_image_enforces_size_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(omio, "MAX_BYTES", 10)
    data = _png_bytes()
    path = tmp_path / "big.png"
    path.write_bytes(data)
    for source in (data, path, io.BytesIO(data)):
        with pytest.raises(ImageLoadError, match="exceeds"):
            load_image(source)


def test_describe_source(tmp_path):
    assert describe_source("x.png") == "x.png"
    assert describe_source(tmp_path / "x.png") == str(tmp_path / "x.png")
    assert describe_source(b"raw") is None
    named = io.BytesIO(b"")
    named.name = "upload.jpg"  # type: ignore[attr-defined]
    assert describe_source(named) == "upload.jpg"


def test_iter_image_files(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "b.JPG").write_bytes(b"")
    (tmp_path / "sub" / "a.png").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("x")
    names = [p.name for p in iter_image_files(tmp_path)]
    assert names == ["b.JPG", "a.png"]
    single = tmp_path / "notes.txt"
    assert iter_image_files(single) == [single]


def test_trim_borders_leaves_tiny_uniform_and_borderless_images_alone():
    tiny = Image.new("RGB", (6, 6), (0, 0, 0))
    assert omio.trim_borders(tiny) is tiny
    uniform = Image.new("RGB", (40, 40), (0, 0, 0))
    assert omio.trim_borders(uniform) is uniform
    noisy = Image.effect_noise((40, 40), 80).convert("RGB")
    assert omio.trim_borders(noisy).size == (40, 40)


def test_trim_borders_keeps_image_when_content_is_too_small():
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    img.paste((255, 255, 255), (45, 45, 55, 55))
    assert omio.trim_borders(img) is img


def test_load_image_applies_exif_orientation():
    img = Image.new("RGB", (8, 4), (10, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise to display
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    assert load_image(buf.getvalue()).size == (4, 8)


def test_load_image_from_url_and_url_size_limit(monkeypatch):
    data = _png_bytes()

    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()

    monkeypatch.setattr(omio.urllib.request, "urlopen", lambda req, timeout: _Response(data))
    assert load_image("https://example.com/a.png").size == (8, 8)
    monkeypatch.setattr(omio, "MAX_BYTES", 10)
    with pytest.raises(ImageLoadError, match="exceeds"):
        load_image("https://example.com/a.png")

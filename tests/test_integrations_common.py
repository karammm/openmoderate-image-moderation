import io

import pytest
from conftest import png_bytes

from openmoderate.integrations import (
    ImageRejected,
    UnreadableUpload,
    UploadTooLarge,
    check_image,
    get_moderator,
)
from openmoderate.integrations._common import error_payload, read_upload

RED, GREEN = (255, 0, 0), (0, 255, 0)


def test_check_image(shared_fake):
    assert check_image(png_bytes(GREEN)).is_safe
    with pytest.raises(ImageRejected) as info:
        check_image(png_bytes(RED), field="avatar")
    assert info.value.field == "avatar"
    assert [v.name for v in info.value.result.violations] == ["weapons"]


def test_unreadable_policy(shared_fake):
    with pytest.raises(UnreadableUpload):
        check_image(b"%PDF-1.7 ...")
    assert check_image(b"%PDF-1.7 ...", on_unreadable="allow") is None
    with pytest.raises(UnreadableUpload):
        check_image(b"")


def test_policy_variants_share_the_engine(shared_fake):
    base = get_moderator()
    lenient = get_moderator(thresholds={"weapons": 1.0})
    assert lenient is not base
    assert lenient.engine is base.engine
    assert get_moderator(thresholds={"weapons": 1.0}) is lenient  # cached
    assert check_image(png_bytes(RED), moderator=lenient).is_safe


def test_read_upload_rewinds_and_limits():
    stream = io.BytesIO(b"x" * 50)
    stream.seek(10)
    assert read_upload(stream, "f") == b"x" * 40
    assert stream.tell() == 10
    with pytest.raises(UploadTooLarge):
        read_upload(io.BytesIO(b"x" * 11), "f", max_bytes=10)


def test_error_payload_hides_scores_by_default(shared_fake):
    with pytest.raises(ImageRejected) as info:
        check_image(png_bytes(RED), field="f")
    assert error_payload(info.value)["violations"] == ["weapons"]
    detailed = error_payload(info.value, include_scores=True)["violations"][0]
    assert detailed["name"] == "weapons" and 0 < detailed["confidence"] < 1


def test_read_upload_without_seekable_method():
    """SpooledTemporaryFile has no .seekable() before Python 3.11 (Flask uploads use it)."""

    class LegacyStream(io.BytesIO):
        seekable = property(lambda self: (_ for _ in ()).throw(AttributeError("seekable")))

    stream = LegacyStream(b"abc")
    assert read_upload(stream, "f") == b"abc"
    assert stream.read() == b"abc"  # rewound

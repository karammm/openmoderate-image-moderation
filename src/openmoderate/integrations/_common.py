"""Shared plumbing for the framework integrations.

All integrations share one embedding engine per process, because the CLIP model is large
(~600 MB). Different policies (thresholds, categories) get their own lightweight
`Moderator` on top of that shared engine.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import IO, Any, Literal

from openmoderate.io import MAX_BYTES, ImageLoadError
from openmoderate.moderator import Moderator
from openmoderate.result import ModerationResult

OnUnreadable = Literal["reject", "allow"]


class ModerationError(Exception):
    """Base class for upload moderation failures."""

    def __init__(self, field: str | None, message: str) -> None:
        super().__init__(message)
        self.field = field


class ImageRejected(ModerationError):
    """The upload is an image that violates the moderation policy."""

    def __init__(self, field: str | None, result: ModerationResult) -> None:
        names = ", ".join(v.name for v in result.violations)
        super().__init__(field, f"Image rejected by content moderation ({names})")
        self.result = result


class UnreadableUpload(ModerationError):
    """The upload could not be decoded as an image."""


class UploadTooLarge(ModerationError):
    """The upload exceeds the size limit."""


_lock = threading.Lock()
_base_kwargs: dict[str, Any] = {}
_base: Moderator | None = None
_derived: dict[tuple, Moderator] = {}


def configure(moderator: Moderator | None = None, /, **kwargs: Any) -> None:
    """Set the moderator the integrations use.

    Pass a ready `Moderator`, or keyword arguments for one (``config``, ``head``,
    ``thresholds``, ``device``, ...), which is then created lazily on first use. Call this
    once at startup; calling it again replaces the shared moderator.
    """
    global _base, _base_kwargs
    with _lock:
        _base = moderator
        _base_kwargs = dict(kwargs)
        _derived.clear()


def is_configured() -> bool:
    return _base is not None or bool(_base_kwargs)


def get_moderator(
    thresholds: Mapping[str, float] | None = None,
    categories: list[str] | None = None,
    exclude: list[str] | None = None,
) -> Moderator:
    """Return the shared moderator, or a variant with a different policy.

    Variants reuse the shared moderator's engine, so they cost no extra model memory.
    """
    global _base
    if _base is None:
        with _lock:
            if _base is None:
                _base = Moderator(**_base_kwargs)
    if not (thresholds or categories or exclude):
        return _base

    key = (
        tuple(sorted((thresholds or {}).items())),
        tuple(categories or ()),
        tuple(exclude or ()),
    )
    if key not in _derived:
        with _lock:
            if key not in _derived:
                _derived[key] = Moderator(
                    _base.config,
                    thresholds=thresholds,
                    categories=categories,
                    exclude=exclude,
                    head=_base.head,
                    head_weight=_base.head_weight,
                    engine=_base.engine,
                )
    return _derived[key]


def read_upload(stream: IO[bytes], field: str | None, max_bytes: int = MAX_BYTES) -> bytes:
    """Read an upload stream and rewind it, so the application can still save the file."""
    # Don't rely on .seekable(): tempfile.SpooledTemporaryFile (used by Werkzeug for Flask
    # uploads) only gained it in Python 3.11.
    try:
        start: int | None = stream.tell()
    except (AttributeError, OSError, ValueError):
        start = None
    data = stream.read(max_bytes + 1)
    if start is not None:
        stream.seek(start)
    if len(data) > max_bytes:
        raise UploadTooLarge(field, f"Upload exceeds {max_bytes} bytes")
    return data


def check_image(
    data: bytes,
    *,
    field: str | None = None,
    moderator: Moderator | None = None,
    on_unreadable: OnUnreadable = "reject",
) -> ModerationResult | None:
    """Moderate raw image bytes.

    Returns the result for a safe image, ``None`` for an unreadable file that is allowed
    through, and raises `ImageRejected` / `UnreadableUpload` otherwise.
    """
    if on_unreadable not in ("reject", "allow"):
        raise ValueError("on_unreadable must be 'reject' or 'allow'")
    mod = moderator or get_moderator()
    if not data:
        if on_unreadable == "allow":
            return None
        raise UnreadableUpload(field, "Upload is empty")
    try:
        result = mod.analyze(data)
    except ImageLoadError as exc:
        if on_unreadable == "allow":
            return None
        raise UnreadableUpload(field, "Upload is not a readable image") from exc
    result.source = field
    if not result.is_safe:
        raise ImageRejected(field, result)
    return result


def error_payload(exc: ModerationError, include_scores: bool = False) -> dict[str, Any]:
    """JSON body for a rejected upload.

    Scores are hidden by default: exposing exact confidences helps an attacker tweak an
    image until it slips under the threshold.
    """
    if isinstance(exc, ImageRejected):
        violations: list[Any] = [
            {"name": v.name, "confidence": v.confidence} if include_scores else v.name
            for v in exc.result.violations
        ]
        return {
            "error": "image_rejected",
            "field": exc.field,
            "violations": violations,
            "detail": str(exc),
        }
    code = "upload_too_large" if isinstance(exc, UploadTooLarge) else "unreadable_image"
    return {"error": code, "field": exc.field, "detail": str(exc)}


def status_for(exc: ModerationError, rejected_status: int) -> int:
    return 413 if isinstance(exc, UploadTooLarge) else rejected_status

"""Django integration: a field validator and a middleware.

Validator (works in model fields, forms, the admin and Django REST Framework serializers):

```python
from openmoderate.integrations.django import ModerationValidator

class Profile(models.Model):
    avatar = models.ImageField(validators=[ModerationValidator()])
    banner = models.ImageField(validators=[ModerationValidator(thresholds={"suggestive": 0.4})])
```

Middleware (moderates every uploaded file under the configured URL prefixes):

```python
MIDDLEWARE = [..., "openmoderate.integrations.django.ModerationMiddleware"]
```

Settings, all optional:

```python
OPENMODERATE = {
    "CONFIG": BASE_DIR / "policy.yaml",   # policy YAML
    "HEAD": BASE_DIR / "my_head.omh",     # trained head
    "PRESET": "accurate",                 # fast (default), balanced or accurate
    "DEVICE": "auto",
    "PATHS": ["/uploads/", "/api/"],      # middleware only; default: every path
    "ON_UNREADABLE": "allow",            # middleware: non-image files pass through
    "STATUS_CODE": 422,
    "INCLUDE_SCORES": False,
}
```

"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.deconstruct import deconstructible

from openmoderate.integrations._common import (
    ImageRejected,
    ModerationError,
    OnUnreadable,
    UploadTooLarge,
    check_image,
    configure,
    error_payload,
    get_moderator,
    is_configured,
    read_upload,
    status_for,
)
from openmoderate.io import MAX_BYTES

__all__ = ["ModerationMiddleware", "ModerationValidator", "configure"]


def _settings() -> dict[str, Any]:
    return dict(getattr(settings, "OPENMODERATE", {}) or {})


def _ensure_configured() -> None:
    """Configure the shared moderator from ``settings.OPENMODERATE`` on first use."""
    if is_configured():
        return
    opts = _settings()
    kwargs: dict[str, Any] = {}
    if opts.get("CONFIG"):
        kwargs["config"] = str(opts["CONFIG"])
    if opts.get("HEAD"):
        kwargs["head"] = str(opts["HEAD"])
    if opts.get("DEVICE"):
        kwargs["device"] = opts["DEVICE"]
    if opts.get("PRESET") and not opts.get("CONFIG"):
        kwargs["preset"] = opts["PRESET"]
    configure(**kwargs)


def _stream(value: Any):
    # Form validation passes an UploadedFile; model validation passes a FieldFile.
    return getattr(value, "file", None) or value


@deconstructible
class ModerationValidator:
    """Reject images that violate the moderation policy.

    Policy overrides apply to this field only and reuse the shared model, so they cost no
    extra memory.

    Args:
        thresholds: Per-category threshold overrides, e.g. ``{"suggestive": 0.4}``.
        categories: Only check these categories.
        exclude: Skip these categories.
        on_unreadable: ``"reject"`` (default) or ``"allow"`` files that are not images.
        message: Error shown to the user; ``%(violations)s`` is replaced with the names.
        max_bytes: Reject files larger than this.
    """

    message = "This image was rejected by content moderation (%(violations)s)."
    code = "image_rejected"

    def __init__(
        self,
        thresholds: Mapping[str, float] | None = None,
        categories: list[str] | None = None,
        exclude: list[str] | None = None,
        on_unreadable: OnUnreadable = "reject",
        message: str | None = None,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self.thresholds = dict(thresholds) if thresholds else None
        self.categories = list(categories) if categories else None
        self.exclude = list(exclude) if exclude else None
        self.on_unreadable = on_unreadable
        if message is not None:
            self.message = message
        self.max_bytes = max_bytes

    def __call__(self, value: Any) -> None:
        if not value:
            return
        _ensure_configured()
        mod = get_moderator(self.thresholds, self.categories, self.exclude)
        try:
            data = read_upload(_stream(value), None, self.max_bytes)
            check_image(data, moderator=mod, on_unreadable=self.on_unreadable)
        except ImageRejected as exc:
            names = ", ".join(v.name for v in exc.result.violations)
            raise ValidationError(
                self.message, code=self.code, params={"violations": names}
            ) from exc
        except UploadTooLarge as exc:
            raise ValidationError(str(exc), code="file_too_large") from exc
        except ModerationError as exc:
            raise ValidationError(str(exc), code="invalid_image") from exc

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModerationValidator) and (
            self.thresholds,
            self.categories,
            self.exclude,
            self.on_unreadable,
            self.message,
            self.max_bytes,
        ) == (
            other.thresholds,
            other.categories,
            other.exclude,
            other.on_unreadable,
            other.message,
            other.max_bytes,
        )


class ModerationMiddleware:
    """Moderate every uploaded file on matching paths; reject with a JSON error."""

    def __init__(self, get_response) -> None:
        self.get_response = get_response
        opts = _settings()
        self.paths = tuple(opts.get("PATHS") or ("/",))
        self.on_unreadable: OnUnreadable = opts.get("ON_UNREADABLE", "allow")
        self.status_code = int(opts.get("STATUS_CODE", 422))
        self.include_scores = bool(opts.get("INCLUDE_SCORES", False))
        self.max_bytes = int(opts.get("MAX_BYTES", MAX_BYTES))

    def __call__(self, request):
        if request.method == "POST" and request.path.startswith(self.paths) and request.FILES:
            _ensure_configured()
            try:
                for name in request.FILES:
                    for upload in request.FILES.getlist(name):
                        data = read_upload(upload, name, self.max_bytes)
                        check_image(
                            data,
                            field=name,
                            moderator=get_moderator(),
                            on_unreadable=self.on_unreadable,
                        )
            except ModerationError as exc:
                return JsonResponse(
                    error_payload(exc, self.include_scores),
                    status=status_for(exc, self.status_code),
                )
        return self.get_response(request)

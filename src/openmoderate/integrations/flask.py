"""Flask integration: reject violating image uploads.

Per view, with a decorator::

    from openmoderate.integrations.flask import moderate_uploads

    @app.post("/avatar")
    @moderate_uploads("avatar")              # or no args: every file in the request
    def avatar():
        request.files["avatar"].save(...)    # only safe images get here

Or for every request, with the extension::

    from openmoderate.integrations.flask import OpenModerate

    OpenModerate(app, check_all_requests=True)

Violating images get a JSON ``422`` response (``413`` if too large).
"""

from __future__ import annotations

import functools
from collections.abc import Iterable, Mapping
from typing import Any, Callable

from flask import Flask, jsonify, request

from openmoderate.integrations._common import (
    ModerationError,
    OnUnreadable,
    check_image,
    configure,
    error_payload,
    get_moderator,
    read_upload,
    status_for,
)
from openmoderate.io import MAX_BYTES
from openmoderate.moderator import Moderator

__all__ = ["OpenModerate", "configure", "moderate_uploads"]


def _check_request_files(
    fields: Iterable[str] | None,
    moderator: Moderator | None,
    on_unreadable: OnUnreadable,
    max_bytes: int,
) -> None:
    names = list(fields) if fields is not None else list(request.files.keys())
    for name in names:
        for storage in request.files.getlist(name):
            if not storage.filename:
                continue  # empty file input: nothing uploaded, the view decides if required
            data = read_upload(storage.stream, name, max_bytes)
            check_image(data, field=name, moderator=moderator, on_unreadable=on_unreadable)


def _error_response(exc: ModerationError, status_code: int, include_scores: bool):
    response = jsonify(error_payload(exc, include_scores))
    response.status_code = status_for(exc, status_code)
    return response


def moderate_uploads(
    *fields: str,
    moderator: Moderator | None = None,
    thresholds: Mapping[str, float] | None = None,
    categories: list[str] | None = None,
    exclude: list[str] | None = None,
    on_unreadable: OnUnreadable = "reject",
    status_code: int = 422,
    include_scores: bool = False,
    max_bytes: int = MAX_BYTES,
) -> Callable:
    """Decorate a view so the named file fields (default: all of them) are moderated first."""

    def decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            mod = moderator or get_moderator(thresholds, categories, exclude)
            try:
                _check_request_files(fields or None, mod, on_unreadable, max_bytes)
            except ModerationError as exc:
                return _error_response(exc, status_code, include_scores)
            return view(*args, **kwargs)

        return wrapper

    return decorator


class OpenModerate:
    """Flask extension.

    Args:
        app: The Flask app (or call :meth:`init_app` later).
        moderator: A ready :class:`Moderator`; otherwise one is built lazily from the
            ``OPENMODERATE_CONFIG`` / ``OPENMODERATE_HEAD`` app config keys.
        check_all_requests: Moderate every uploaded file on every request.
        on_unreadable: What to do with uploads that are not images. Defaults to
            ``"allow"`` here, since a blanket check also sees PDFs, CSVs and so on.
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        moderator: Moderator | None = None,
        check_all_requests: bool = False,
        on_unreadable: OnUnreadable = "allow",
        status_code: int = 422,
        include_scores: bool = False,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self.moderator = moderator
        self.check_all_requests = check_all_requests
        self.on_unreadable = on_unreadable
        self.status_code = status_code
        self.include_scores = include_scores
        self.max_bytes = max_bytes
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if self.moderator is not None:
            configure(self.moderator)
        elif app.config.get("OPENMODERATE_CONFIG") or app.config.get("OPENMODERATE_HEAD"):
            configure(
                config=app.config.get("OPENMODERATE_CONFIG"),
                head=app.config.get("OPENMODERATE_HEAD"),
            )
        app.extensions["openmoderate"] = self
        if self.check_all_requests:
            app.before_request(self._before_request)

    def _before_request(self):
        if not request.files:
            return None
        try:
            _check_request_files(None, None, self.on_unreadable, self.max_bytes)
        except ModerationError as exc:
            return _error_response(exc, self.status_code, self.include_scores)
        return None

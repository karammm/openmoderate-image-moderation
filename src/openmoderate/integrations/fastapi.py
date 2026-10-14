"""FastAPI integration: reject violating image uploads before your endpoint runs.

```python
from fastapi import FastAPI, UploadFile
from openmoderate.integrations.fastapi import ModeratedFile, moderated

app = FastAPI()

@app.post("/avatar")
async def avatar(file: ModeratedFile):          # form field "file"
    ...                                          # only safe images get here

@app.post("/photos")
async def photos(photo: UploadFile = moderated("photo", thresholds={"weapons": 0.3})):
    ...
```

Violating images get a ``422`` response (``413`` if too large) and the endpoint never runs.
Moderation runs in a worker thread, so it does not block the event loop.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from openmoderate.integrations._common import (
    ModerationError,
    OnUnreadable,
    UploadTooLarge,
    check_image,
    configure,
    error_payload,
    get_moderator,
    status_for,
)
from openmoderate.io import MAX_BYTES
from openmoderate.moderator import Moderator

__all__ = ["ModeratedFile", "ModeratedFiles", "configure", "moderated", "moderated_files"]


async def _check(
    upload: UploadFile,
    field: str,
    moderator: Moderator | None,
    policy: dict[str, Any],
    on_unreadable: OnUnreadable,
    status_code: int,
    include_scores: bool,
    max_bytes: int,
) -> None:
    data = await upload.read(max_bytes + 1)
    await upload.seek(0)
    try:
        if len(data) > max_bytes:
            raise UploadTooLarge(field, f"Upload exceeds {max_bytes} bytes")
        mod = moderator or get_moderator(**policy)
        await run_in_threadpool(
            check_image, data, field=field, moderator=mod, on_unreadable=on_unreadable
        )
    except ModerationError as exc:
        raise HTTPException(
            status_code=status_for(exc, status_code), detail=error_payload(exc, include_scores)
        ) from exc


def _make_dependency(field: str, many: bool, check_kwargs: dict[str, Any]):
    annotation: Any = Annotated[list[UploadFile], File()] if many else Annotated[UploadFile, File()]

    async def dependency(**kwargs: Any):
        value = kwargs[field]
        for upload in value if many else [value]:
            await _check(upload, field, **check_kwargs)
        return value

    # FastAPI reads the signature to know which form field to parse.
    dependency.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [inspect.Parameter(field, inspect.Parameter.KEYWORD_ONLY, annotation=annotation)]
    )
    return dependency


def _build(
    field: str,
    many: bool,
    *,
    moderator: Moderator | None,
    thresholds: Mapping[str, float] | None,
    categories: list[str] | None,
    exclude: list[str] | None,
    on_unreadable: OnUnreadable,
    status_code: int,
    include_scores: bool,
    max_bytes: int,
) -> Any:
    check_kwargs = {
        "moderator": moderator,
        "policy": {"thresholds": thresholds, "categories": categories, "exclude": exclude},
        "on_unreadable": on_unreadable,
        "status_code": status_code,
        "include_scores": include_scores,
        "max_bytes": max_bytes,
    }
    return Depends(_make_dependency(field, many, check_kwargs))


def moderated(
    field: str = "file",
    *,
    moderator: Moderator | None = None,
    thresholds: Mapping[str, float] | None = None,
    categories: list[str] | None = None,
    exclude: list[str] | None = None,
    on_unreadable: OnUnreadable = "reject",
    status_code: int = 422,
    include_scores: bool = False,
    max_bytes: int = MAX_BYTES,
) -> Any:
    """A ``Depends(...)`` that parses form field ``field`` and moderates it.

    Use as a default value: ``file: UploadFile = moderated("file")``.
    """
    return _build(
        field,
        False,
        moderator=moderator,
        thresholds=thresholds,
        categories=categories,
        exclude=exclude,
        on_unreadable=on_unreadable,
        status_code=status_code,
        include_scores=include_scores,
        max_bytes=max_bytes,
    )


def moderated_files(
    field: str = "files",
    *,
    moderator: Moderator | None = None,
    thresholds: Mapping[str, float] | None = None,
    categories: list[str] | None = None,
    exclude: list[str] | None = None,
    on_unreadable: OnUnreadable = "reject",
    status_code: int = 422,
    include_scores: bool = False,
    max_bytes: int = MAX_BYTES,
) -> Any:
    """Like `moderated` for a repeated field (``list[UploadFile]``); every file must pass."""
    return _build(
        field,
        True,
        moderator=moderator,
        thresholds=thresholds,
        categories=categories,
        exclude=exclude,
        on_unreadable=on_unreadable,
        status_code=status_code,
        include_scores=include_scores,
        max_bytes=max_bytes,
    )


#: ``file: ModeratedFile`` — moderated upload from the form field named ``file``.
ModeratedFile = Annotated[UploadFile, moderated("file")]
#: ``files: ModeratedFiles`` — every upload in the repeated form field ``files``.
ModeratedFiles = Annotated[list[UploadFile], moderated_files("files")]

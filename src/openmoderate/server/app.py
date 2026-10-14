"""REST API for openmoderate.

Run with ``openmoderate serve`` or ``uvicorn openmoderate.server.app:app``.

Endpoints:

* ``GET  /health``               liveness and readiness
* ``GET  /v1/categories``        labels, parents and thresholds
* ``POST /v1/moderate``          multipart upload, field ``file``
* ``POST /v1/moderate/batch``    multipart upload, field ``files`` (repeatable)
* ``POST /v1/moderate/json``     JSON ``{"image_base64": ...}`` or ``{"url": ...}``

Configuration comes from environment variables (see :class:`ServerSettings`).
"""

from __future__ import annotations

import base64
import binascii
import hmac
import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated, Optional

from openmoderate import __version__
from openmoderate.io import MAX_BYTES, ImageLoadError
from openmoderate.moderator import Moderator

try:
    from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "The openmoderate server needs extra dependencies: pip install 'openmoderate[server]'"
    ) from exc

from openmoderate.server.fetch import UnsafeURLError, fetch_image_bytes


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class ServerSettings:
    #: Require this key in the ``X-API-Key`` header. Unset = no auth (bind to localhost!).
    api_key: str | None = field(default_factory=lambda: os.getenv("OPENMODERATE_API_KEY") or None)
    #: Allow ``{"url": ...}`` requests. Off by default because of SSRF risk.
    allow_urls: bool = field(default_factory=lambda: _env_bool("OPENMODERATE_ALLOW_URLS", False))
    max_batch: int = field(default_factory=lambda: int(os.getenv("OPENMODERATE_MAX_BATCH", "16")))
    max_bytes: int = MAX_BYTES
    config_path: str | None = field(default_factory=lambda: os.getenv("OPENMODERATE_CONFIG"))
    head_path: str | None = field(default_factory=lambda: os.getenv("OPENMODERATE_HEAD"))
    #: Load the model at startup instead of on the first request.
    preload: bool = field(default_factory=lambda: _env_bool("OPENMODERATE_PRELOAD", True))
    device: str = field(default_factory=lambda: os.getenv("OPENMODERATE_DEVICE", "auto"))


class JsonImageRequest(BaseModel):
    # Optional[...] rather than ``str | None``: pydantic evaluates these at runtime (3.9).
    image_base64: Optional[str] = None  # noqa: UP045
    url: Optional[str] = None  # noqa: UP045


def create_app(
    moderator: Moderator | None = None, settings: ServerSettings | None = None
) -> FastAPI:
    settings = settings or ServerSettings()
    state: dict[str, Moderator] = {}
    # Torch already parallelises one forward pass across cores; serialising requests avoids
    # thread oversubscription and keeps memory flat.
    lock = threading.Lock()

    def get_moderator() -> Moderator:
        if "mod" not in state:
            with lock:
                if "mod" not in state:
                    state["mod"] = moderator or Moderator(
                        settings.config_path, head=settings.head_path, device=settings.device
                    )
        return state["mod"]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.preload:
            mod = get_moderator()
            mod._text_embeddings()  # loads the model and embeds the prompts once
        yield

    app = FastAPI(
        title="openmoderate",
        version=__version__,
        description="Open-source image content moderation.",
        lifespan=lifespan,
    )

    def require_key(request: Request) -> None:
        if settings.api_key is None:
            return
        given = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(given.encode(), settings.api_key.encode()):
            raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key header")

    def analyze(images: list[bytes], names: list[str | None]) -> list[dict]:
        mod = get_moderator()
        with lock:
            results = mod.analyze_batch(images)
        out = []
        for res, name in zip(results, names):
            res.source = name
            out.append(res.to_dict())
        return out

    def read_upload(upload: UploadFile) -> bytes:
        data = upload.file.read(settings.max_bytes + 1)
        if len(data) > settings.max_bytes:
            raise HTTPException(
                413, f"{upload.filename or 'file'} exceeds {settings.max_bytes} bytes"
            )
        if not data:
            raise HTTPException(422, f"{upload.filename or 'file'} is empty")
        return data

    @app.exception_handler(ImageLoadError)
    async def _bad_image(request: Request, exc: ImageLoadError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "model_loaded": "mod" in state}

    @app.get("/v1/categories", dependencies=[Depends(require_key)])
    def categories() -> dict:
        mod = get_moderator()
        return {
            "categories": [
                {"name": s.name, "parent": s.parent, "threshold": s.threshold}
                for s in mod.label_specs
            ]
        }

    @app.post("/v1/moderate", dependencies=[Depends(require_key)])
    def moderate(file: Annotated[UploadFile, File()]) -> dict:
        return analyze([read_upload(file)], [file.filename])[0]

    @app.post("/v1/moderate/batch", dependencies=[Depends(require_key)])
    def moderate_batch(files: Annotated[list[UploadFile], File()]) -> dict:
        if len(files) > settings.max_batch:
            raise HTTPException(413, f"At most {settings.max_batch} files per request")
        try:
            results = analyze([read_upload(f) for f in files], [f.filename for f in files])
        except ImageLoadError:
            # Report per-file errors instead of failing the whole batch.
            results = []
            for f in files:
                f.file.seek(0)
                try:
                    results.append(analyze([read_upload(f)], [f.filename])[0])
                except ImageLoadError as exc:
                    results.append({"source": f.filename, "error": str(exc)})
        return {"results": results}

    @app.post("/v1/moderate/json", dependencies=[Depends(require_key)])
    def moderate_json(body: JsonImageRequest) -> dict:
        if (body.image_base64 is None) == (body.url is None):
            raise HTTPException(422, "Provide exactly one of 'image_base64' or 'url'")
        if body.url is not None:
            if not settings.allow_urls:
                raise HTTPException(
                    403, "URL fetching is disabled on this server (OPENMODERATE_ALLOW_URLS)"
                )
            try:
                data = fetch_image_bytes(body.url, settings.max_bytes)
            except UnsafeURLError as exc:
                raise HTTPException(422, str(exc)) from exc
            return analyze([data], [body.url])[0]
        if len(body.image_base64) > settings.max_bytes * 4 // 3 + 4:
            raise HTTPException(413, f"Image exceeds {settings.max_bytes} bytes")
        try:
            data = base64.b64decode(body.image_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(422, "image_base64 is not valid base64") from exc
        return analyze([data], [None])[0]

    return app


def __getattr__(name: str):
    # ``uvicorn openmoderate.server.app:app`` builds the app lazily from the environment.
    if name == "app":
        return create_app()
    raise AttributeError(name)

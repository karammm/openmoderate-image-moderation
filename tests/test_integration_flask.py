import io

import pytest
from conftest import png_bytes

pytest.importorskip("flask")
from flask import Flask, request  # noqa: E402

from openmoderate.integrations.flask import OpenModerate, moderate_uploads  # noqa: E402

RED, GREEN = (255, 0, 0), (0, 255, 0)


def upload(color_or_bytes, name="x.png"):
    data = color_or_bytes if isinstance(color_or_bytes, bytes) else png_bytes(color_or_bytes)
    return (io.BytesIO(data), name)


@pytest.fixture
def app(shared_fake):
    app = Flask(__name__)

    @app.post("/avatar")
    @moderate_uploads("avatar")
    def avatar():
        return {"size": len(request.files["avatar"].read())}

    @app.post("/any")
    @moderate_uploads()
    def any_files():
        return {"fields": sorted(request.files)}

    @app.post("/lenient")
    @moderate_uploads("photo", thresholds={"weapons": 1.0})
    def lenient():
        return {"ok": True}

    return app


def test_decorator_allows_safe_and_rewinds(app):
    data = png_bytes(GREEN)
    r = app.test_client().post("/avatar", data={"avatar": (io.BytesIO(data), "ok.png")})
    assert r.status_code == 200 and r.json == {"size": len(data)}


def test_decorator_rejects(app):
    r = app.test_client().post("/avatar", data={"avatar": upload(RED)})
    assert r.status_code == 422
    assert r.json["error"] == "image_rejected" and r.json["violations"] == ["weapons"]


def test_decorator_checks_all_fields(app):
    c = app.test_client()
    r = c.post("/any", data={"a": upload(GREEN), "b": upload(RED)})
    assert r.status_code == 422 and r.json["field"] == "b"
    assert c.post("/any", data={"a": upload(GREEN)}).json == {"fields": ["a"]}


def test_decorator_policy_and_unreadable(app):
    c = app.test_client()
    assert c.post("/lenient", data={"photo": upload(RED)}).status_code == 200
    r = c.post("/avatar", data={"avatar": upload(b"%PDF", "x.pdf")})
    assert r.status_code == 422 and r.json["error"] == "unreadable_image"


def test_empty_file_input_is_skipped(app):
    r = app.test_client().post("/any", data={"a": (io.BytesIO(b""), "")})
    assert r.status_code == 200


def test_extension_checks_every_request(shared_fake):
    app = Flask(__name__)
    OpenModerate(app, check_all_requests=True)

    @app.post("/docs")
    def docs():
        return {"ok": True}

    c = app.test_client()
    assert c.post("/docs", data={"f": upload(RED)}).status_code == 422
    assert c.post("/docs", data={"f": upload(GREEN)}).status_code == 200
    # Non-image files pass through a blanket check by default.
    assert c.post("/docs", data={"f": upload(b"%PDF", "a.pdf")}).status_code == 200
    assert app.extensions["openmoderate"].check_all_requests

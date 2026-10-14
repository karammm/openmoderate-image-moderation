import base64
import io

import pytest
from conftest import solid

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from openmoderate import Moderator  # noqa: E402
from openmoderate.server import fetch  # noqa: E402
from openmoderate.server.app import ServerSettings, create_app  # noqa: E402

RED, GREEN = (255, 0, 0), (0, 255, 0)


def png(color) -> bytes:
    buf = io.BytesIO()
    solid(color).save(buf, format="PNG")
    return buf.getvalue()


def client(fake_engine, **settings) -> TestClient:
    settings.setdefault("preload", False)
    app = create_app(Moderator(engine=fake_engine), ServerSettings(**settings))
    return TestClient(app)


def test_health_and_categories(fake_engine):
    c = client(fake_engine)
    assert c.get("/health").json()["status"] == "ok"
    names = [x["name"] for x in c.get("/v1/categories").json()["categories"]]
    assert "weapons" in names


def test_moderate_upload(fake_engine):
    c = client(fake_engine)
    r = c.post("/v1/moderate", files={"file": ("gun.png", png(RED), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["is_safe"] is False
    assert body["source"] == "gun.png"
    assert body["violations"][0]["name"] == "weapons"


def test_bad_and_empty_upload(fake_engine):
    c = client(fake_engine)
    assert c.post("/v1/moderate", files={"file": ("x.jpg", b"nope")}).status_code == 422
    assert c.post("/v1/moderate", files={"file": ("x.jpg", b"")}).status_code == 422
    assert c.post("/v1/moderate").status_code == 422


def test_upload_too_large(fake_engine):
    c = client(fake_engine, max_bytes=100)
    r = c.post("/v1/moderate", files={"file": ("big.png", png(RED))})
    assert r.status_code == 413


def test_batch_with_partial_failure(fake_engine):
    c = client(fake_engine)
    files = [
        ("files", ("a.png", png(RED))),
        ("files", ("b.png", png(GREEN))),
        ("files", ("c.jpg", b"broken")),
    ]
    results = c.post("/v1/moderate/batch", files=files).json()["results"]
    assert [r.get("is_safe") for r in results] == [False, True, None]
    assert "error" in results[2]


def test_batch_limit(fake_engine):
    c = client(fake_engine, max_batch=1)
    files = [("files", ("a.png", png(RED))), ("files", ("b.png", png(RED)))]
    assert c.post("/v1/moderate/batch", files=files).status_code == 413


def test_json_base64(fake_engine):
    c = client(fake_engine)
    r = c.post("/v1/moderate/json", json={"image_base64": base64.b64encode(png(RED)).decode()})
    assert r.json()["is_safe"] is False
    assert c.post("/v1/moderate/json", json={"image_base64": "!!!"}).status_code == 422
    assert c.post("/v1/moderate/json", json={}).status_code == 422


def test_urls_disabled_by_default(fake_engine):
    c = client(fake_engine)
    r = c.post("/v1/moderate/json", json={"url": "https://example.com/a.jpg"})
    assert r.status_code == 403


def test_url_fetch_when_enabled(fake_engine, monkeypatch):
    monkeypatch.setattr(
        "openmoderate.server.app.fetch_image_bytes", lambda url, max_bytes: png(RED)
    )
    c = client(fake_engine, allow_urls=True)
    r = c.post("/v1/moderate/json", json={"url": "https://example.com/a.jpg"})
    assert r.status_code == 200 and r.json()["is_safe"] is False


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a.jpg",
        "http://localhost/a.jpg",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/a.jpg",
        "http://[::1]/a.jpg",
        "http://[::ffff:127.0.0.1]/a.jpg",
        "file:///etc/passwd",
        "ftp://example.com/a.jpg",
        "http://user:pw@example.com/a.jpg",
    ],
)
def test_ssrf_blocked(url):
    with pytest.raises(fetch.UnsafeURLError):
        fetch.validate_url(url)


def test_ssrf_blocked_through_api(fake_engine):
    c = client(fake_engine, allow_urls=True)
    r = c.post("/v1/moderate/json", json={"url": "http://169.254.169.254/latest/meta-data"})
    assert r.status_code == 422


def test_api_key(fake_engine):
    c = client(fake_engine, api_key="s3cret")
    assert c.get("/health").status_code == 200  # health stays open for load balancers
    assert c.get("/v1/categories").status_code == 401
    assert c.get("/v1/categories", headers={"X-API-Key": "wrong"}).status_code == 401
    assert c.get("/v1/categories", headers={"X-API-Key": "s3cret"}).status_code == 200


def test_preload_loads_model(fake_engine):
    app = create_app(Moderator(engine=fake_engine), ServerSettings(preload=True))
    with TestClient(app) as c:
        assert c.get("/health").json()["model_loaded"] is True
    assert fake_engine.text_calls == 1

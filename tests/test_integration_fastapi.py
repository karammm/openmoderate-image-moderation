import pytest
from conftest import png_bytes

pytest.importorskip("fastapi")
from fastapi import FastAPI, UploadFile  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from openmoderate.integrations.fastapi import (  # noqa: E402
    ModeratedFile,
    ModeratedFiles,
    moderated,
)

RED, GREEN = (255, 0, 0), (0, 255, 0)


@pytest.fixture
def client(shared_fake):
    app = FastAPI()

    @app.post("/avatar")
    async def avatar(file: ModeratedFile):
        return {"size": len(await file.read()), "name": file.filename}

    @app.post("/lenient")
    async def lenient(photo: UploadFile = moderated("photo", thresholds={"weapons": 1.0})):  # noqa: B008
        return {"size": len(await photo.read())}

    @app.post("/many")
    async def many(files: ModeratedFiles):
        return {"count": len(files)}

    @app.post("/scores")
    async def scores(file: UploadFile = moderated(include_scores=True, max_bytes=10_000)):  # noqa: B008
        return {}

    return TestClient(app)


def test_safe_upload_reaches_endpoint_intact(client):
    data = png_bytes(GREEN)
    r = client.post("/avatar", files={"file": ("ok.png", data)})
    assert r.status_code == 200
    assert r.json() == {"size": len(data), "name": "ok.png"}


def test_violating_upload_rejected(client):
    r = client.post("/avatar", files={"file": ("gun.png", png_bytes(RED))})
    assert r.status_code == 422
    assert r.json()["detail"] == {
        "error": "image_rejected",
        "field": "file",
        "violations": ["weapons"],
        "detail": "Image rejected by content moderation (weapons)",
    }


def test_unreadable_and_missing(client):
    r = client.post("/avatar", files={"file": ("x.pdf", b"%PDF")})
    assert r.status_code == 422 and r.json()["detail"]["error"] == "unreadable_image"
    assert client.post("/avatar").status_code == 422  # field required


def test_per_endpoint_policy(client):
    assert client.post("/lenient", files={"photo": ("g.png", png_bytes(RED))}).status_code == 200


def test_multiple_files_all_checked(client):
    ok = [("files", ("a.png", png_bytes(GREEN))), ("files", ("b.png", png_bytes(GREEN)))]
    assert client.post("/many", files=ok).json() == {"count": 2}
    bad = ok + [("files", ("c.png", png_bytes(RED)))]
    assert client.post("/many", files=bad).status_code == 422


def test_scores_and_size_limit(client):
    r = client.post("/scores", files={"file": ("g.png", png_bytes(RED))})
    assert r.json()["detail"]["violations"][0]["name"] == "weapons"
    assert "confidence" in r.json()["detail"]["violations"][0]
    big = client.post("/scores", files={"file": ("big.png", b"0" * 10_001)})
    assert big.status_code == 413

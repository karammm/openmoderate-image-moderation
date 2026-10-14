"""FastAPI app that rejects violating uploads.

    pip install "openmoderate[fastapi]" uvicorn
    uvicorn examples.fastapi_app:app
    curl -F file=@photo.jpg localhost:8000/avatar
"""

from pathlib import Path

from fastapi import FastAPI, UploadFile

from openmoderate.integrations.fastapi import ModeratedFile, moderated

UPLOADS = Path("uploads")
UPLOADS.mkdir(exist_ok=True)

app = FastAPI()


@app.post("/avatar")
async def avatar(file: ModeratedFile):
    # Only images that passed moderation get here, and the file is rewound for you.
    (UPLOADS / Path(file.filename or "upload").name).write_bytes(await file.read())
    return {"saved": file.filename}


@app.post("/listing-photo")
async def listing_photo(
    photo: UploadFile = moderated("photo", thresholds={"weapons": 0.3}, exclude=["alcohol"]),  # noqa: B008
):
    # A stricter policy for this endpoint: lower weapons threshold, alcohol allowed.
    return {"ok": photo.filename}

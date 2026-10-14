"""Flask app that rejects violating uploads.

    pip install "openmoderate[flask]"
    flask --app examples/flask_app.py run
    curl -F avatar=@photo.jpg localhost:5000/avatar
"""

from pathlib import Path

from flask import Flask, request
from werkzeug.utils import secure_filename

from openmoderate.integrations.flask import moderate_uploads

UPLOADS = Path("uploads")
UPLOADS.mkdir(exist_ok=True)

app = Flask(__name__)


@app.post("/avatar")
@moderate_uploads("avatar")
def avatar():
    # Only images that passed moderation get here.
    f = request.files["avatar"]
    f.save(UPLOADS / secure_filename(f.filename or "upload"))
    return {"saved": f.filename}

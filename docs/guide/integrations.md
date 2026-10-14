# Web framework integrations

Add one line and violating images are rejected before your code runs. The file is rewound after the check, so you can save it as usual. All integrations in a process share one loaded model (~600 MB), even when endpoints use different policies.

## FastAPI

```bash
pip install "openmoderate[fastapi]"
```

```python
from fastapi import FastAPI, UploadFile
from openmoderate.integrations.fastapi import ModeratedFile, moderated

app = FastAPI()

@app.post("/avatar")
async def avatar(file: ModeratedFile):        # form field "file"
    ...                                        # only safe images reach this line

@app.post("/listing")
async def listing(photo: UploadFile = moderated("photo", thresholds={"weapons": 0.3})):
    ...                                        # a stricter policy for this endpoint
```

Use `ModeratedFiles` / `moderated_files("field")` for multi-file fields. Moderation runs in a worker thread, so the event loop isn't blocked. A rejected upload gets `422` with `{"detail": {"error": "image_rejected", "field": "file", "violations": ["weapons"], ...}}`.

## Flask

```bash
pip install "openmoderate[flask]"
```

```python
from openmoderate.integrations.flask import OpenModerate, moderate_uploads

@app.post("/avatar")
@moderate_uploads("avatar")        # no arguments = every file in the request
def avatar():
    request.files["avatar"].save(...)

# Or check every upload on every request:
OpenModerate(app, check_all_requests=True)
```

## Django

```bash
pip install "openmoderate[django]"
```

```python
from openmoderate.integrations.django import ModerationValidator

class Profile(models.Model):
    avatar = models.ImageField(validators=[ModerationValidator()])
    banner = models.ImageField(validators=[ModerationValidator(thresholds={"suggestive": 0.4})])
```

The validator works in model forms, the admin and Django REST Framework model serializers, and is safe to use in migrations. Users see "This image was rejected by content moderation (weapons)." To guard whole URL prefixes instead, add the middleware:

```python
MIDDLEWARE = [..., "openmoderate.integrations.django.ModerationMiddleware"]
OPENMODERATE = {
    "PATHS": ["/uploads/", "/api/"],   # default: every path
    "CONFIG": BASE_DIR / "policy.yaml",
    "HEAD": BASE_DIR / "my_head.omh",
}
```

## Behaviour common to all integrations

| | Explicit (dependency, decorator, validator) | Blanket (Flask extension, Django middleware) |
|---|---|---|
| Violating image | rejected, `422` | rejected, `422` |
| Larger than 25 MB | rejected, `413` | rejected, `413` |
| Not an image (PDF, CSV…) | rejected (`on_unreadable="reject"`) | passed through (`on_unreadable="allow"`) |
| Empty file input | skipped (the view decides whether it's required) | skipped |

Error responses list the violated category names but **not the confidence scores**, because exact scores help an attacker tweak an image until it passes. Pass `include_scores=True` if you need them. To share a custom moderator across everything, call `openmoderate.integrations.configure(Moderator(...))` at startup.

Runnable examples: [`examples/fastapi_app.py`](https://github.com/karammm/openmoderate-image-moderation/blob/main/examples/fastapi_app.py), [`examples/flask_app.py`](https://github.com/karammm/openmoderate-image-moderation/blob/main/examples/flask_app.py), [`examples/django_app.py`](https://github.com/karammm/openmoderate-image-moderation/blob/main/examples/django_app.py).

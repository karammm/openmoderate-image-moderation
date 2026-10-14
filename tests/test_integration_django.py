import pytest
from conftest import png_bytes

django = pytest.importorskip("django")
from django.conf import settings  # noqa: E402

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test",
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
        MIDDLEWARE=["openmoderate.integrations.django.ModerationMiddleware"],
        OPENMODERATE={"PATHS": ["/guarded/"]},
        DATABASES={},
    )
    django.setup()

from django import forms  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.http import JsonResponse  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import path  # noqa: E402

from openmoderate.integrations.django import ModerationValidator  # noqa: E402

RED, GREEN = (255, 0, 0), (0, 255, 0)


def size_view(request):
    return JsonResponse({"size": len(request.FILES["file"].read())})


urlpatterns = [path("guarded/upload", size_view), path("open/upload", size_view)]


class AvatarForm(forms.Form):
    avatar = forms.ImageField(validators=[ModerationValidator()])
    banner = forms.ImageField(
        required=False, validators=[ModerationValidator(thresholds={"weapons": 1.0})]
    )


def form_with(**files):
    return AvatarForm(
        data={}, files={k: SimpleUploadedFile(f"{k}.png", v) for k, v in files.items()}
    )


def test_validator_accepts_safe_image(shared_fake):
    assert form_with(avatar=png_bytes(GREEN)).is_valid()


def test_validator_rejects_with_message(shared_fake):
    form = form_with(avatar=png_bytes(RED))
    assert not form.is_valid()
    err = form.errors.as_data()["avatar"][0]
    assert err.code == "image_rejected"
    assert "weapons" in form.errors["avatar"][0]


def test_validator_per_field_policy(shared_fake):
    assert form_with(avatar=png_bytes(GREEN), banner=png_bytes(RED)).is_valid()


def test_validator_is_migration_safe():
    v = ModerationValidator(thresholds={"weapons": 0.3}, exclude=["alcohol"])
    path_, args, kwargs = v.deconstruct()
    assert path_ == "openmoderate.integrations.django.ModerationValidator"
    assert ModerationValidator(*args, **kwargs) == v
    assert v != ModerationValidator()


def test_middleware_guards_configured_paths(shared_fake):
    c = Client()
    bad = SimpleUploadedFile("gun.png", png_bytes(RED))
    r = c.post("/guarded/upload", {"file": bad})
    assert r.status_code == 422 and r.json()["violations"] == ["weapons"]

    data = png_bytes(GREEN)
    ok = c.post("/guarded/upload", {"file": SimpleUploadedFile("ok.png", data)})
    assert ok.status_code == 200 and ok.json() == {"size": len(data)}  # rewound

    other = c.post("/open/upload", {"file": SimpleUploadedFile("gun.png", png_bytes(RED))})
    assert other.status_code == 200  # outside PATHS

    pdf = c.post("/guarded/upload", {"file": SimpleUploadedFile("a.pdf", b"%PDF")})
    assert pdf.status_code == 200  # non-images pass the blanket middleware by default

"""A single-file Django project showing the validator and the middleware.

    pip install "openmoderate[django]"
    python examples/django_app.py runserver
    curl -F avatar=@photo.jpg localhost:8000/avatar      # form + ModerationValidator
    curl -F file=@photo.jpg localhost:8000/uploads/any   # ModerationMiddleware

In a real project, put ``ModerationValidator()`` on your model's ImageField and add the
middleware to ``MIDDLEWARE`` in settings.py.
"""

import sys

from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY="example-only",
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=["*"],
    MIDDLEWARE=["openmoderate.integrations.django.ModerationMiddleware"],
    OPENMODERATE={"PATHS": ["/uploads/"]},
)

from django import forms  # noqa: E402
from django.http import JsonResponse  # noqa: E402
from django.urls import path  # noqa: E402
from django.views.decorators.csrf import csrf_exempt  # noqa: E402

from openmoderate.integrations.django import ModerationValidator  # noqa: E402


class AvatarForm(forms.Form):
    avatar = forms.ImageField(validators=[ModerationValidator()])


@csrf_exempt
def avatar(request):
    form = AvatarForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)
    return JsonResponse({"saved": form.cleaned_data["avatar"].name})


@csrf_exempt
def any_upload(request):
    # The middleware already moderated every file under /uploads/.
    return JsonResponse({"files": list(request.FILES)})


urlpatterns = [path("avatar", avatar), path("uploads/any", any_upload)]

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

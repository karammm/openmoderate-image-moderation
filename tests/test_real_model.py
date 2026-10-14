"""Smoke test against the real CLIP model. Run with: pytest -m slow"""

import pytest
from PIL import Image, ImageDraw

from openmoderate import Moderator


@pytest.mark.slow
def test_real_model_runs_and_plain_image_is_safe():
    img = Image.new("RGB", (224, 224), (120, 180, 220))
    ImageDraw.Draw(img).ellipse((60, 60, 160, 160), fill=(255, 220, 0))
    res = Moderator().analyze(img)
    assert res.is_safe, res.to_dict()

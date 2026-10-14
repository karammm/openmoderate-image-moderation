import io

import pytest
from conftest import solid

from openmoderate import ModerationConfig, Moderator
from openmoderate.io import ImageLoadError


def test_flags_weapon(fake_engine):
    res = Moderator(engine=fake_engine).analyze(solid((255, 0, 0)))
    assert not res.is_safe
    assert res.violations[0].name == "weapons"
    assert res.violations[0].parent == "violence"


def test_safe_image(fake_engine):
    res = Moderator(engine=fake_engine).analyze(solid((0, 255, 0)))
    assert res.is_safe
    assert len(res.labels) == len(Moderator(engine=fake_engine).category_names)
    assert all(0.0 <= label.confidence <= 1.0 for label in res.labels)


def test_threshold_override_and_exclude(fake_engine):
    strict = Moderator(engine=fake_engine, thresholds={"weapons": 1.0})
    assert "weapons" not in [v.name for v in strict.analyze(solid((255, 0, 0))).violations]

    no_weapons = Moderator(engine=fake_engine, exclude=["weapons"])
    assert "weapons" not in no_weapons.category_names


def test_only_categories(fake_engine):
    mod = Moderator(engine=fake_engine, categories=["hate_symbols"])
    assert mod.category_names == ["hate_symbols"]
    assert not mod.analyze(solid((0, 0, 255))).is_safe


def test_unknown_category_raises(fake_engine):
    with pytest.raises(KeyError):
        Moderator(engine=fake_engine, thresholds={"nope": 0.1})


def test_batch_and_text_cache(fake_engine):
    mod = Moderator(engine=fake_engine)
    results = mod.analyze_batch([solid((255, 0, 0)), solid((0, 255, 0))])
    mod.analyze(solid((0, 0, 255)))
    assert [r.is_safe for r in results] == [False, True]
    assert fake_engine.text_calls == 1


def test_input_types(fake_engine, tmp_path):
    mod = Moderator(engine=fake_engine)
    img = solid((255, 0, 0))
    path = tmp_path / "x.png"
    img.save(path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    for src in (str(path), path, buf.getvalue(), io.BytesIO(buf.getvalue())):
        assert not mod.analyze(src).is_safe
    assert mod.analyze(str(path)).source == str(path)


def test_rgba_is_flattened(fake_engine):
    rgba = solid((255, 0, 0)).convert("RGBA")
    assert not Moderator(engine=fake_engine).analyze(rgba).is_safe


def test_bad_input(fake_engine):
    with pytest.raises(ImageLoadError):
        Moderator(engine=fake_engine).analyze(b"not an image")


def test_custom_category_from_dict(fake_engine):
    cfg = ModerationConfig.from_dict(
        {
            "enabled": ["weapons", "logos"],
            "custom_categories": [{"name": "logos", "prompts": ["a competitor logo"]}],
        }
    )
    assert Moderator(cfg, engine=fake_engine).category_names == ["weapons", "logos"]


def test_yaml_config(fake_engine, tmp_path):
    p = tmp_path / "policy.yaml"
    p.write_text("thresholds:\n  weapons: 0.99\ndisabled: [alcohol, tobacco]\n")
    mod = Moderator(str(p), engine=fake_engine)
    assert "alcohol" not in mod.category_names
    assert (
        mod.config.categories[[c.name for c in mod.config.categories].index("weapons")].threshold
        == 0.99
    )


def test_to_dict(fake_engine):
    d = Moderator(engine=fake_engine).analyze(solid((255, 0, 0))).to_dict()
    assert d["is_safe"] is False
    assert d["violations"][0]["name"] == "weapons"


def test_category_negatives_suppress_lookalikes():
    from conftest import FakeEngine

    engine = FakeEngine({(9, 9, 9): "a competitor logo"})
    base = {"enabled": ["logos"]}
    cat = {"name": "logos", "prompts": ["a competitor logo"]}
    flagged = Moderator({**base, "custom_categories": [cat]}, engine=engine)
    assert not flagged.analyze(solid((9, 9, 9))).is_safe

    cat_with_neg = {**cat, "negatives": ["a competitor logo"]}
    suppressed = Moderator({**base, "custom_categories": [cat_with_neg]}, engine=engine)
    assert suppressed.analyze(solid((9, 9, 9))).is_safe

import pytest

from openmoderate import PRESETS, ModerationConfig, Moderator


def test_presets_define_model_and_calibration():
    assert set(PRESETS) == {"fast", "balanced", "accurate"}
    fast = ModerationConfig.from_preset("fast")
    # "fast" must stay identical to the plain default so existing scores don't change.
    default = ModerationConfig()
    assert (fast.model_name, fast.pretrained, fast.margin_bias) == (
        default.model_name,
        default.pretrained,
        default.margin_bias,
    )
    accurate = ModerationConfig.from_preset("accurate")
    assert accurate.model_name == "ViT-L-14" and accurate.margin_bias == 3.0
    with pytest.raises(ValueError, match="balanced"):
        ModerationConfig.from_preset("ultra")


def test_moderator_preset(fake_engine):
    mod = Moderator(preset="balanced", engine=fake_engine)
    assert mod.config.model_name == "ViT-B-16"
    with pytest.raises(ValueError, match="either config or preset"):
        Moderator({"thresholds": {"weapons": 0.3}}, preset="accurate", engine=fake_engine)


def test_preset_in_policy_file_with_overrides(fake_engine):
    mod = Moderator({"preset": "accurate", "thresholds": {"weapons": 0.3}}, engine=fake_engine)
    assert mod.config.model_name == "ViT-L-14"
    assert mod.thresholds["weapons"] == 0.3
    custom = Moderator({"preset": "accurate", "model": "ViT-H-14"}, engine=fake_engine)
    assert custom.config.model_name == "ViT-H-14"


def test_preset_from_environment(monkeypatch, fake_engine):
    monkeypatch.setenv("OPENMODERATE_PRESET", "accurate")
    assert Moderator(engine=fake_engine).config.model_name == "ViT-L-14"
    # A policy file without its own preset also follows the environment.
    assert Moderator({"disabled": ["alcohol"]}, engine=fake_engine).config.model_name == "ViT-L-14"


def test_head_must_match_preset_model(tmp_path, fake_engine):
    import numpy as np

    from openmoderate import LinearHead

    head = LinearHead(["x"], np.zeros((1, 4)), np.zeros(1), model_name="ViT-B-32")
    with pytest.raises(ValueError, match="ViT-B-32"):
        Moderator(preset="accurate", head=head, engine=fake_engine)


def test_cli_preset_flag(capsys):
    from openmoderate.cli import build_parser, main

    args = build_parser().parse_args(["scan", "x.jpg", "--preset", "accurate"])
    assert args.preset == "accurate"
    main(["categories", "--preset", "accurate"])
    assert "weapons" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["scan", "x.jpg", "--preset", "accurate", "--config", "p.yaml"])

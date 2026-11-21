import json

import pytest
from conftest import ColorEngine, make_dataset, solid

import openmoderate.engine.clip_engine as clip_engine
from openmoderate.cli import main


@pytest.fixture(autouse=True)
def fake_clip(monkeypatch):
    monkeypatch.setattr(clip_engine, "ClipEngine", lambda *a, **k: ColorEngine())


def test_train_then_scan_and_evaluate(tmp_path, capsys):
    data = make_dataset(tmp_path / "data")
    head = tmp_path / "h.omh"
    assert main(["train", str(data), "-o", str(head), "--epochs", "200"]) == 0
    assert head.exists()

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    solid((220, 30, 30)).save(uploads / "bad.png")
    solid((30, 200, 30)).save(uploads / "ok.png")
    (uploads / "broken.jpg").write_bytes(b"nope")
    capsys.readouterr()

    code = main(["scan", str(uploads), "--head", str(head), "--json", "--only", "weapons", "drugs"])
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    by_name = {line["source"].split("/")[-1]: line for line in lines}
    assert by_name["bad.png"]["is_safe"] is False
    assert by_name["ok.png"]["is_safe"] is True
    assert "error" in by_name["broken.jpg"]
    assert code == 2  # unreadable file

    (uploads / "broken.jpg").unlink()
    assert main(["scan", str(uploads), "--head", str(head), "--fail-on-violation"]) == 1

    assert main(["evaluate", str(data), "--head", str(head), "--json"]) == 0
    out = capsys.readouterr().out
    report = json.loads(out[out.index("{") :])
    assert report["labels"]["weapons"]["recall"] == 1.0
    assert report["any_violation"]["support"] == 24


def test_categories_lists_head_labels(tmp_path, capsys):
    data = make_dataset(tmp_path / "data")
    head = tmp_path / "h.omh"
    main(["train", str(data), "-o", str(head)])
    capsys.readouterr()
    main(["categories", "--head", str(head)])
    out = capsys.readouterr().out
    assert "zero-shot+trained" in out and "weapons" in out


def test_bad_threshold_arg(tmp_path):
    with pytest.raises(SystemExit):
        main(["scan", str(tmp_path), "-t", "weapons"])


def test_non_numeric_threshold_value(tmp_path):
    with pytest.raises(SystemExit, match="must be a number"):
        main(["scan", str(tmp_path), "-t", "weapons=high"])


def test_config_and_preset_are_exclusive(tmp_path):
    with pytest.raises(SystemExit, match="either --config or --preset"):
        main(["scan", str(tmp_path), "--config", "x.yaml", "--preset", "fast"])


def test_scan_empty_directory_warns_and_exits_zero(tmp_path, capsys):
    assert main(["scan", str(tmp_path)]) == 0
    err = capsys.readouterr().err
    assert "no images or videos found" in err
    assert "0 scanned, 0 flagged, 0 unreadable" in err


def test_scan_summary_counts_safe_images(tmp_path, capsys):
    solid((30, 200, 30)).save(tmp_path / "ok.png")
    assert main(["scan", str(tmp_path)]) == 0
    assert "1 scanned, 0 flagged, 0 unreadable" in capsys.readouterr().err


def test_scan_single_file_path(tmp_path, capsys):
    path = tmp_path / "one.png"
    solid((30, 200, 30)).save(path)
    assert main(["scan", str(path), "--json"]) == 0
    line = json.loads(capsys.readouterr().out.splitlines()[0])
    assert line["source"].endswith("one.png") and line["is_safe"] is True

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

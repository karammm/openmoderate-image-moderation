import json

import numpy as np
import pytest
from conftest import RED_GUN, NearestColorEngine, make_video

pytest.importorskip("cv2")

from openmoderate import Moderator  # noqa: E402
from openmoderate.cli import main  # noqa: E402
from openmoderate.video import VideoLoadError, build_segments  # noqa: E402

RED, GREEN = (255, 0, 0), (0, 255, 0)


@pytest.fixture
def mod():
    return Moderator(engine=NearestColorEngine(RED_GUN))


def test_timestamped_segment(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 2), (RED, 2), (GREEN, 2)])
    res = mod.analyze_video(video)
    assert not res.is_safe
    assert res.frames_analyzed == 6
    assert res.duration == pytest.approx(6.0, abs=0.15)
    (seg,) = res.segments
    assert seg.name == "weapons" and seg.parent == "violence"
    assert (seg.start, seg.end) == (pytest.approx(2.0, abs=0.15), pytest.approx(4.0, abs=0.15))
    assert seg.frames == 2
    assert [v.name for v in res.violations] == ["weapons"]
    assert res.to_dict()["segments"][0]["name"] == "weapons"


def test_safe_video_and_sampling_rate(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 3)])
    res = mod.analyze_video(video, fps=2)
    assert res.is_safe and res.frames_analyzed == 6


def test_min_frames_suppresses_blips(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 2), (RED, 0.5), (GREEN, 2)])
    assert not mod.analyze_video(video, fps=2).is_safe
    assert mod.analyze_video(video, fps=2, min_frames=2).is_safe


def test_stop_on_violation(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 1), (RED, 2), (GREEN, 20)])
    res = mod.analyze_video(video, stop_on_violation=True)
    assert not res.is_safe and res.stopped_early
    assert res.frames_analyzed < 10


def test_max_duration_truncates(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 6)])
    res = mod.analyze_video(video, max_duration=3)
    assert res.truncated and res.frames_analyzed <= 4


def test_bytes_and_file_input(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 1), (RED, 1)])
    data = video.read_bytes()
    assert not mod.analyze_video(data).is_safe
    with open(video, "rb") as fh:
        assert not mod.analyze_video(fh).is_safe


def test_unreadable_video(mod, tmp_path):
    with pytest.raises(VideoLoadError):
        mod.analyze_video(b"definitely not a video")
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"\x00" * 100)
    with pytest.raises(VideoLoadError):
        mod.analyze_video(bad)


def test_frame_scores_optional(mod, tmp_path):
    video = make_video(tmp_path / "v.mp4", [(GREEN, 2)])
    assert mod.analyze_video(video).to_dict().get("frames") is None
    frames = mod.analyze_video(video, keep_frame_scores=True).to_dict()["frames"]
    assert len(frames) == 2 and "weapons" in frames[0]["scores"]


def test_build_segments_merges_single_missed_sample():
    times = np.arange(8, dtype=float)
    flagged = np.array([0, 1, 1, 0, 1, 0, 0, 1], dtype=float)[:, None]
    segs = build_segments(times, flagged, ["x"], [None], [0.5], 1.0, 8.0)
    # Samples 1-2 and 4 merge across the one-sample gap; sample 7 is separate.
    assert [(s.start, s.end, s.frames) for s in segs] == [(1.0, 5.0, 3), (7.0, 8.0, 1)]


def test_cli_scans_videos(tmp_path, capsys, monkeypatch):
    import openmoderate.engine.clip_engine as clip_engine

    monkeypatch.setattr(clip_engine, "ClipEngine", lambda *a, **k: NearestColorEngine(RED_GUN))
    folder = tmp_path / "media"
    folder.mkdir()
    make_video(folder / "bad.mp4", [(GREEN, 1), (RED, 2)])
    make_video(folder / "ok.mp4", [(GREEN, 2)])
    assert main(["scan", str(folder), "--fail-on-violation"]) == 1
    out = capsys.readouterr().out
    assert "FLAGGED" in out and "weapons" in out and "0:01.0-0:03" in out

    main(["scan", str(folder / "bad.mp4"), "--json"])
    line = json.loads(capsys.readouterr().out.strip())
    assert line["segments"][0]["name"] == "weapons"

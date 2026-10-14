"""Video moderation: sample frames, score them, and report timestamped violation segments.

Requires ``pip install "openmoderate[video]"`` (OpenCV).

Decoding untrusted video exercises a large native codebase (FFmpeg via OpenCV), so this
module enforces limits while decoding, not just from the file's metadata, which an
attacker controls: maximum duration, frame size and number of decoded frames.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Union

import numpy as np
from PIL import Image

from openmoderate.result import Label

if TYPE_CHECKING:
    from openmoderate.moderator import Moderator

VideoInput = Union[str, os.PathLike, bytes, bytearray, IO[bytes]]

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm", ".mpg", ".mpeg", ".wmv"}

MAX_VIDEO_BYTES = int(os.getenv("OPENMODERATE_MAX_VIDEO_BYTES", 500 * 1024 * 1024))
MAX_DIMENSION = 8192
# Upper bound on frames decoded (not just sampled), so a file claiming an absurd frame rate
# cannot make us decode forever.
MAX_DECODED_FRAMES = 500_000


class VideoLoadError(ValueError):
    pass


def _cv2():
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise ImportError('Video support needs OpenCV: pip install "openmoderate[video]"') from exc
    return cv2


def is_video_path(path: str | os.PathLike) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


@contextmanager
def _as_path(video: VideoInput) -> Iterator[str]:
    """OpenCV only reads from paths, so spill bytes and file objects to a temp file."""
    if isinstance(video, (str, os.PathLike)):
        yield str(video)
        return
    if isinstance(video, (bytes, bytearray)):
        data = bytes(video)
    elif hasattr(video, "read"):
        data = video.read(MAX_VIDEO_BYTES + 1)
    else:
        raise VideoLoadError(f"Unsupported video input type: {type(video).__name__}")
    if len(data) > MAX_VIDEO_BYTES:
        raise VideoLoadError(f"Video exceeds {MAX_VIDEO_BYTES} bytes")
    suffix = Path(getattr(video, "name", "") or "").suffix or ".mp4"
    fd, tmp = tempfile.mkstemp(suffix=suffix, prefix="openmoderate-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        yield tmp
    finally:
        os.unlink(tmp)


@dataclass
class VideoInfo:
    duration: float  # seconds actually decoded (or until the duration limit)
    native_fps: float | None
    width: int
    height: int
    truncated: bool = False  # stopped at max_duration


def iter_frames(
    path: str,
    fps: float = 1.0,
    max_frames: int | None = None,
    max_duration: float | None = None,
    info: VideoInfo | None = None,
) -> Iterator[tuple[float, Image.Image]]:
    """Yield ``(timestamp_seconds, RGB image)`` sampled at roughly ``fps`` frames per second.

    The first frame is always included. Fills ``info`` (if given) as decoding proceeds.
    """
    if fps <= 0:
        raise ValueError("fps must be positive")
    cv2 = _cv2()
    cap = cv2.VideoCapture(path)
    try:
        if not cap.isOpened():
            raise VideoLoadError("Could not open video (unsupported or corrupt file)")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise VideoLoadError(f"Video frames are too large ({width}x{height})")
        native = cap.get(cv2.CAP_PROP_FPS) or 0.0
        native_fps = native if 0 < native <= 1000 else None
        if info is not None:
            info.native_fps, info.width, info.height = native_fps, width, height

        interval = 1.0 / fps
        frame_duration = 1.0 / native_fps if native_fps else 0.0
        next_t, decoded, emitted, t = 0.0, 0, 0, 0.0
        while decoded < MAX_DECODED_FRAMES:
            if not cap.grab():
                break
            t = decoded / native_fps if native_fps else cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            decoded += 1
            if max_duration is not None and t > max_duration:
                if info is not None:
                    info.truncated = True
                break
            if info is not None:
                info.duration = t + frame_duration
            if t + 1e-6 < next_t:
                continue
            ok, frame = cap.retrieve()
            if not ok or frame is None:
                continue
            yield t, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            emitted += 1
            while next_t <= t + 1e-6:
                next_t += interval
            if max_frames is not None and emitted >= max_frames:
                break
        if decoded == 0:
            raise VideoLoadError("Video contains no decodable frames")
    finally:
        cap.release()


@dataclass(frozen=True)
class VideoSegment:
    """A stretch of video where one label stayed above its threshold."""

    name: str
    start: float
    end: float
    max_confidence: float
    frames: int
    parent: str | None = None


@dataclass
class VideoModerationResult:
    source: str | None
    duration: float
    sample_fps: float
    frames_analyzed: int
    labels: list[Label] = field(default_factory=list)  # peak confidence per label
    segments: list[VideoSegment] = field(default_factory=list)
    truncated: bool = False
    stopped_early: bool = False
    frame_scores: list[dict[str, Any]] | None = None

    @property
    def is_safe(self) -> bool:
        return not self.segments

    @property
    def violations(self) -> list[Label]:
        flagged = {s.name for s in self.segments}
        return [label for label in self.labels if label.name in flagged]

    def to_dict(self) -> dict[str, Any]:
        out = {
            "source": self.source,
            "is_safe": self.is_safe,
            "duration": round(self.duration, 3),
            "sample_fps": self.sample_fps,
            "frames_analyzed": self.frames_analyzed,
            "truncated": self.truncated,
            "stopped_early": self.stopped_early,
            "segments": [asdict(s) for s in self.segments],
            "violations": [asdict(v) for v in self.violations],
            "labels": [asdict(label) for label in self.labels],
        }
        if self.frame_scores is not None:
            out["frames"] = self.frame_scores
        return out

    def __repr__(self) -> str:
        segs = ", ".join(f"{s.name}@{s.start:.1f}-{s.end:.1f}s" for s in self.segments)
        return f"VideoModerationResult(is_safe={self.is_safe}, segments=[{segs}])"


def build_segments(
    times: np.ndarray,
    scores: np.ndarray,
    names: list[str],
    parents: list[str | None],
    thresholds: list[float],
    interval: float,
    duration: float,
    min_frames: int = 1,
) -> list[VideoSegment]:
    """Merge consecutive flagged samples (allowing one missed sample) into segments."""
    segments: list[VideoSegment] = []
    max_gap = 2 * interval + 1e-6
    for j, name in enumerate(names):
        flagged = np.where(scores[:, j] >= thresholds[j])[0]
        if not len(flagged):
            continue
        groups: list[list[int]] = [[int(flagged[0])]]
        for i in flagged[1:]:
            if times[i] - times[groups[-1][-1]] <= max_gap:
                groups[-1].append(int(i))
            else:
                groups.append([int(i)])
        for g in groups:
            if len(g) < min_frames:
                continue
            start = float(times[g[0]])
            end = float(min(times[g[-1]] + interval, max(duration, times[g[-1]])))
            segments.append(
                VideoSegment(
                    name=name,
                    start=round(start, 3),
                    end=round(end, 3),
                    max_confidence=round(float(scores[g, j].max()), 4),
                    frames=len(g),
                    parent=parents[j],
                )
            )
    segments.sort(key=lambda s: (s.start, s.name))
    return segments


def analyze_video(
    moderator: Moderator,
    video: VideoInput,
    *,
    fps: float = 1.0,
    max_frames: int | None = None,
    max_duration: float | None = None,
    min_frames: int = 1,
    stop_on_violation: bool = False,
    batch_size: int = 16,
    keep_frame_scores: bool = False,
) -> VideoModerationResult:
    """Implementation of :meth:`openmoderate.Moderator.analyze_video`."""
    specs = moderator.label_specs
    names = [s.name for s in specs]
    parents = [s.parent for s in specs]
    thresholds = [s.threshold for s in specs]
    interval = 1.0 / fps
    info = VideoInfo(duration=0.0, native_fps=None, width=0, height=0)
    times: list[float] = []
    rows: list[np.ndarray] = []

    def segments_so_far() -> list[VideoSegment]:
        matrix = np.stack(rows) if rows else np.zeros((0, len(names)))
        return build_segments(
            np.array(times),
            matrix,
            names,
            parents,
            thresholds,
            interval,
            info.duration,
            min_frames,
        )

    # With early stopping, score in small batches so a violation is caught sooner.
    step = min(batch_size, 4) if stop_on_violation else batch_size
    stopped = False
    source = str(video) if isinstance(video, (str, os.PathLike)) else getattr(video, "name", None)
    with _as_path(video) as path:
        batch_t: list[float] = []
        batch_im: list[Image.Image] = []
        frames = iter_frames(path, fps, max_frames, max_duration, info)
        while True:
            item = next(frames, None)
            if item is not None:
                batch_t.append(item[0])
                batch_im.append(item[1])
            if batch_im and (item is None or len(batch_im) >= step):
                times.extend(batch_t)
                rows.extend(moderator.score_images(batch_im))
                batch_t, batch_im = [], []
                if stop_on_violation and item is not None and segments_so_far():
                    stopped = True
                    frames.close()
                    break
            if item is None:
                break

    score_matrix = np.stack(rows) if rows else np.zeros((0, len(names)))
    segments = segments_so_far()
    peaks = score_matrix.max(axis=0) if len(rows) else np.zeros(len(names))
    labels = [
        Label(s.name, round(float(p), 4), parent=s.parent, threshold=s.threshold)
        for s, p in zip(specs, peaks)
    ]
    labels.sort(key=lambda label: label.confidence, reverse=True)
    frame_scores = None
    if keep_frame_scores:
        frame_scores = [
            {"time": round(float(t), 3), "scores": dict(zip(names, map(float, row)))}
            for t, row in zip(times, rows)
        ]
    return VideoModerationResult(
        source=source,
        duration=info.duration,
        sample_fps=fps,
        frames_analyzed=len(times),
        labels=labels,
        segments=segments,
        truncated=info.truncated,
        stopped_early=stopped,
        frame_scores=frame_scores,
    )

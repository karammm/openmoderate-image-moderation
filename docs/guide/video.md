# Videos

```bash
pip install "openmoderate[video]"
```

```python
result = Moderator().analyze_video("clip.mp4")      # path, bytes or file object
result.is_safe        # False
result.segments       # [VideoSegment(name='weapons', start=3.0, end=6.0, max_confidence=0.9949, frames=3)]
```

```bash
$ openmoderate scan ./media          # images and videos, recursively
FLAGGED  media/slideshow.mp4  [video 15.0s, 15 frames]
           0:03.0-0:06.0  weapons 99%
           0:09.0-0:12.0  violence 99%
```

openmoderate samples frames (1 per second by default), scores them in batches and merges consecutive flagged frames into timestamped segments. A single missed sample inside a segment doesn't split it.

| Option | Default | Purpose |
|---|---|---|
| `fps` | `1.0` | Frames sampled per second. Raise it to catch brief content, lower it for speed. |
| `min_frames` | `1` | Ignore segments shorter than N sampled frames (suppresses one-frame false positives). |
| `stop_on_violation` | `False` | Stop at the first violation: fast rejection for upload flows. |
| `max_duration` | none | Only analyse the first N seconds; `result.truncated` tells you if it stopped early. |
| `keep_frame_scores` | `False` | Include every sampled frame's scores in the result. |

The same options exist on the CLI (`--fps`, `--min-frames`, `--max-duration`) and on the REST endpoint `POST /v1/moderate/video` (multipart field `file`; query parameters `fps`, `min_frames`, `stop_on_violation`).

Things to know:

- **Content between samples is not seen.** At 1 fps, a half-second flash can be missed. Use a higher `fps` when that matters.
- **Video decoding runs FFmpeg (via OpenCV) on untrusted input.** openmoderate caps frame size, decoded frames and duration while decoding, rather than trusting the file's metadata. The server rejects videos over `OPENMODERATE_MAX_VIDEO_SECONDS` (default 600) or `OPENMODERATE_MAX_VIDEO_BYTES` (default 200 MB) with `413`, instead of returning a partially checked result. For hostile traffic, also run the server in a sandboxed container.
- The framework integrations (FastAPI, Flask, Django) moderate images; a video upload counts as "not an image" there. Call `analyze_video()` from your view for video uploads.

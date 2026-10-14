# REST API server

Use openmoderate from any language over HTTP.

```bash
pip install "openmoderate[server]"
OPENMODERATE_API_KEY=change-me openmoderate serve --host 0.0.0.0 --port 8000
```

Or with the published Docker image (CPU, model weights included, so it runs offline):

```bash
docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me ghcr.io/karammm/openmoderate:latest
```

Pin a version (`ghcr.io/karammm/openmoderate:1.0.0` or `:1.0`) in production. To build it yourself: `docker build -t openmoderate .` from a checkout.

Interactive API docs are served at `http://localhost:8000/docs`.

| Endpoint | Body | Returns |
|---|---|---|
| `GET /health` | – | `{"status": "ok", "model_loaded": true}` (no API key needed) |
| `GET /v1/categories` | – | labels, parents and thresholds |
| `POST /v1/moderate` | multipart field `file` | one result |
| `POST /v1/moderate/batch` | multipart field `files` (repeat it) | `{"results": [...]}`; unreadable files get an `error` entry |
| `POST /v1/moderate/json` | `{"image_base64": "..."}` or `{"url": "..."}` | one result |
| `POST /v1/moderate/video` | multipart field `file`; query `fps`, `min_frames`, `stop_on_violation` | timestamped `segments` |

```bash
curl -H "X-API-Key: change-me" -F file=@upload.jpg http://localhost:8000/v1/moderate
```

```json
{
  "source": "upload.jpg",
  "is_safe": false,
  "violations": [{"name": "weapons", "confidence": 0.996, "parent": "violence", "threshold": 0.5}],
  "labels": [...]
}
```

```javascript
// Node.js
const form = new FormData();
form.append("file", new Blob([fs.readFileSync("upload.jpg")]), "upload.jpg");
const res = await fetch("http://localhost:8000/v1/moderate", {
  method: "POST", headers: { "X-API-Key": "change-me" }, body: form,
});
const { is_safe, violations } = await res.json();
```

Server settings (environment variables):

| Variable | Default | Purpose |
|---|---|---|
| `OPENMODERATE_API_KEY` | unset | Require this value in the `X-API-Key` header. **Set it whenever the port is reachable by others.** |
| `OPENMODERATE_ALLOW_URLS` | `false` | Allow `{"url": ...}` requests (see the security note below) |
| `OPENMODERATE_CONFIG` / `OPENMODERATE_HEAD` | unset | Policy YAML and trained head to load (also `--config` / `--head`) |
| `OPENMODERATE_MAX_BATCH` | `16` | Max files per batch request |
| `OPENMODERATE_MAX_BYTES` | 25 MB | Max size per image |
| `OPENMODERATE_MAX_VIDEO_BYTES` / `OPENMODERATE_MAX_VIDEO_SECONDS` | 200 MB / 600 s | Video upload limits |
| `OPENMODERATE_PRELOAD` | `true` | Load the model at startup rather than on the first request |

**URL fetching is off by default.** A server that downloads any URL it is given can be tricked into reaching internal services (cloud metadata endpoints, admin panels). When you enable it, openmoderate only allows http(s), refuses private, loopback and link-local addresses, and re-checks every redirect. If untrusted callers can use the API, also route outbound traffic through an egress proxy.

Performance: a single-image request took 15–25 ms end to end on an Apple M-series laptop once the model was warm. CPU-only servers will be slower, so measure on your own hardware before sizing. Requests are processed one at a time per worker (PyTorch already uses all cores for each image). Use `--workers N` to run more processes; each loads its own copy of the model (~600 MB RAM).

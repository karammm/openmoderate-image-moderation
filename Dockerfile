# openmoderate REST server (CPU).
#
#   docker build -t openmoderate .
#   docker run -p 8000:8000 -e OPENMODERATE_API_KEY=change-me openmoderate
#
# Model weights are downloaded at build time, so containers start fast and run offline.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENMODERATE_CACHE_DIR=/models \
    HF_HOME=/models/hf

WORKDIR /app

# CPU-only torch keeps the image ~4x smaller than the default CUDA build. torch and
# torchvision must come from the same index, or their versions mismatch at import time.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install ".[server]"

RUN useradd --create-home --uid 1000 app && mkdir -p /models && chown app /models
USER app
RUN openmoderate download

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["openmoderate", "serve", "--host", "0.0.0.0", "--port", "8000"]

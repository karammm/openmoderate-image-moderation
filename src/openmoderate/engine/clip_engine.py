"""OpenCLIP-backed engine. Weights are downloaded once and cached locally."""

from __future__ import annotations

import threading
from typing import Any

import numpy as np
from PIL import Image


def _resolve_device(device: str) -> str:
    import torch

    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ClipEngine:
    def __init__(
        self,
        model_name: str = "ViT-B-32",
        pretrained: str = "laion2b_s34b_b79k",
        device: str = "auto",
        cache_dir: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name
        self.pretrained = pretrained
        self.device = _resolve_device(device)
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        # Loaded lazily on first use (open_clip has no type hints).
        self._model: Any = None
        self._preprocess: Any = None
        self._tokenizer: Any = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            import open_clip

            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=self.pretrained, cache_dir=self.cache_dir
            )
            model.eval().to(self.device)
            self._tokenizer = open_clip.get_tokenizer(self.model_name)
            self._preprocess = preprocess
            self._model = model

    def encode_images(self, images: list[Image.Image]) -> np.ndarray:
        import torch

        self._ensure_loaded()
        out = []
        with torch.inference_mode():
            for i in range(0, len(images), self.batch_size):
                batch = torch.stack(
                    [self._preprocess(im) for im in images[i : i + self.batch_size]]
                )
                feats = self._model.encode_image(batch.to(self.device))
                feats = feats / feats.norm(dim=-1, keepdim=True)
                out.append(feats.float().cpu().numpy())
        return np.concatenate(out, axis=0)

    def encode_texts(self, texts: list[str]) -> np.ndarray:
        import torch

        self._ensure_loaded()
        with torch.inference_mode():
            tokens = self._tokenizer(texts).to(self.device)
            feats = self._model.encode_text(tokens)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.float().cpu().numpy()

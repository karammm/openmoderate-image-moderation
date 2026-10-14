"""The main entry point: :class:`Moderator`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import NamedTuple

import numpy as np

from openmoderate.config import ModerationConfig
from openmoderate.engine.base import Engine
from openmoderate.io import ImageInput, describe_source, load_image
from openmoderate.result import Label, ModerationResult


class _TextIndex(NamedTuple):
    embeddings: np.ndarray
    positives: list[np.ndarray]
    negatives: list[np.ndarray]
    safe: np.ndarray


class Moderator:
    """Detect policy-violating content in images.

    Example::

        from openmoderate import Moderator

        mod = Moderator()
        result = mod.analyze("upload.jpg")
        if not result.is_safe:
            print(result.violations)

    Args:
        config: A :class:`ModerationConfig`, a dict, or a path to a YAML file.
        thresholds: Per-category threshold overrides, e.g. ``{"weapons": 0.4}``.
        categories: Only check these categories.
        exclude: Skip these categories.
        engine: Custom embedding engine (defaults to OpenCLIP, loaded lazily).
        device: ``"auto"``, ``"cpu"``, ``"cuda"`` or ``"mps"``.
    """

    def __init__(
        self,
        config: ModerationConfig | Mapping | str | Path | None = None,
        *,
        thresholds: Mapping[str, float] | None = None,
        categories: list[str] | None = None,
        exclude: list[str] | None = None,
        engine: Engine | None = None,
        device: str = "auto",
    ) -> None:
        if config is None:
            config = ModerationConfig()
        elif isinstance(config, (str, Path)):
            config = ModerationConfig.from_yaml(config)
        elif isinstance(config, Mapping):
            config = ModerationConfig.from_dict(config)
        self.config = config.with_overrides(thresholds, categories, exclude)

        if engine is None:
            from openmoderate.engine.clip_engine import ClipEngine

            engine = ClipEngine(
                self.config.model_name,
                self.config.pretrained,
                device=device,
                cache_dir=self.config.cache_dir,
            )
        self.engine = engine
        self._text_cache: _TextIndex | None = None

    @property
    def category_names(self) -> list[str]:
        return [c.name for c in self.config.categories]

    def _text_embeddings(self) -> _TextIndex:
        """Embed all prompts once and remember which rows belong to which category."""
        if self._text_cache is None:
            texts: list[str] = []

            def add(prompts: tuple[str, ...]) -> np.ndarray:
                start = len(texts)
                texts.extend(prompts)
                return np.arange(start, len(texts))

            positives = [add(c.prompts) for c in self.config.categories]
            negatives = [add(c.negatives) for c in self.config.categories]
            safe_idx = add(self.config.safe_prompts)
            self._text_cache = _TextIndex(
                self.engine.encode_texts(texts), positives, negatives, safe_idx
            )
        return self._text_cache

    def score_embeddings(self, image_embeddings: np.ndarray) -> np.ndarray:
        """Zero-shot category scores in ``[0, 1)``, shape ``(n_images, n_categories)``.

        For each category we take the margin between the image's best-matching category
        prompt and its best-matching safe prompt (in CLIP logit units), then map it through
        a calibrated sigmoid. Categories are scored independently, so an image can be both
        ``weapons`` and ``violence``.
        """
        index = self._text_embeddings()
        logits = self.config.logit_scale * image_embeddings @ index.embeddings.T
        safe_best = logits[:, index.safe].max(axis=1)
        scores = np.empty((len(image_embeddings), len(index.positives)), dtype=np.float64)
        for j, (pos, neg) in enumerate(zip(index.positives, index.negatives)):
            contrast = safe_best
            if len(neg):
                contrast = np.maximum(contrast, logits[:, neg].max(axis=1))
            margin = logits[:, pos].max(axis=1) - contrast
            z = (margin - self.config.margin_bias) / self.config.margin_temperature
            scores[:, j] = 1.0 / (1.0 + np.exp(-z))
        # Never report certainty: a threshold of 1.0 must always mean "never flag".
        return np.clip(scores, 0.0, 0.9999)

    def _build_result(self, scores: np.ndarray, source: str | None) -> ModerationResult:
        labels = [
            Label(c.name, round(float(s), 4), parent=c.parent, threshold=c.threshold)
            for c, s in zip(self.config.categories, scores)
        ]
        labels.sort(key=lambda label: label.confidence, reverse=True)
        return ModerationResult(labels=labels, source=source)

    def analyze(self, image: ImageInput) -> ModerationResult:
        """Analyse a single image (path, URL, bytes, file object or PIL image)."""
        return self.analyze_batch([image])[0]

    def analyze_batch(self, images: Iterable[ImageInput]) -> list[ModerationResult]:
        sources = list(images)
        pil_images = [load_image(s) for s in sources]
        if not pil_images:
            return []
        scores = self.score_embeddings(self.engine.encode_images(pil_images))
        return [self._build_result(row, describe_source(s)) for row, s in zip(scores, sources)]

    def is_safe(self, image: ImageInput) -> bool:
        return self.analyze(image).is_safe

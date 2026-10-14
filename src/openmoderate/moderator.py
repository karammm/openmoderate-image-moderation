"""The main entry point: `Moderator`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from openmoderate.config import ModerationConfig
from openmoderate.engine.base import Engine
from openmoderate.io import ImageInput, describe_source, load_image, trim_borders
from openmoderate.result import Label, ModerationResult
from openmoderate.training.head import LinearHead

if TYPE_CHECKING:
    from PIL import Image

    from openmoderate.video import VideoInput, VideoModerationResult


class _TextIndex(NamedTuple):
    embeddings: np.ndarray
    positives: list[np.ndarray]
    negatives: list[np.ndarray]
    safe: np.ndarray


class LabelSpec(NamedTuple):
    name: str
    parent: str | None
    threshold: float


class Moderator:
    """Detect policy-violating content in images.

    For example:

    ```python
    from openmoderate import Moderator

    mod = Moderator()
    result = mod.analyze("upload.jpg")
    if not result.is_safe:
        print(result.violations)
    ```

    Args:
        config: A `ModerationConfig`, a dict, or a path to a YAML file.
        thresholds: Per-category threshold overrides, e.g. ``{"weapons": 0.4}``.
        categories: Only check these categories.
        exclude: Skip these categories.
        head: A trained head (``.omh`` path or `LinearHead`) from
            ``openmoderate train``. Its labels are added to the result; labels that also
            exist as zero-shot categories are blended according to ``head_weight``.
        head_weight: For labels known to both, ``1.0`` uses only the trained head,
            ``0.0`` only the zero-shot score, values in between blend them.
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
        head: LinearHead | str | Path | None = None,
        head_weight: float = 1.0,
        engine: Engine | None = None,
        device: str = "auto",
    ) -> None:
        if config is None:
            config = ModerationConfig()
        elif isinstance(config, (str, Path)):
            config = ModerationConfig.from_yaml(config)
        elif isinstance(config, Mapping):
            config = ModerationConfig.from_dict(config)
        self.head = LinearHead.load(head) if isinstance(head, (str, Path)) else head
        if not 0.0 <= head_weight <= 1.0:
            raise ValueError("head_weight must be between 0 and 1")
        self.head_weight = head_weight
        if self.head is not None and self.head.model_name not in (None, config.model_name):
            raise ValueError(
                f"Head was trained on {self.head.model_name!r} embeddings but the moderator "
                f"uses {config.model_name!r}; set model_name to match."
            )

        # Split filters/overrides between zero-shot categories and head-only labels.
        known = {c.name for c in config.categories}
        head_labels = self.head.labels if self.head else []
        head_only = [name for name in head_labels if name not in known]
        thresholds = dict(thresholds or {})
        head_thresholds = {k: thresholds.pop(k) for k in list(thresholds) if k in head_only}
        zs_categories = None if categories is None else [c for c in categories if c in known]
        if categories is not None:
            unknown = set(categories) - known - set(head_only)
            if unknown:
                raise KeyError(f"Unknown category: {sorted(unknown)}")
            head_only = [name for name in head_only if name in categories]
        if exclude:
            head_only = [name for name in head_only if name not in exclude]
            # Head-only names are handled above; anything else is validated by the config.
            exclude = [c for c in exclude if c in known or c not in head_labels]
        self.config = config.with_overrides(thresholds, zs_categories, exclude)

        self._specs = [LabelSpec(c.name, c.parent, c.threshold) for c in self.config.categories]
        self._blend: list[tuple[int, int]] = []  # (spec index, head column)
        self._extra_cols: list[int] = []
        if self.head is not None:
            for j, spec in enumerate(self._specs):
                if spec.name in self.head.labels:
                    self._blend.append((j, self.head.labels.index(spec.name)))
            for name in head_only:
                col = self.head.labels.index(name)
                threshold = head_thresholds.get(name, self.head.thresholds.get(name, 0.5))
                self._specs.append(LabelSpec(name, self.head.parents.get(name), threshold))
                self._extra_cols.append(col)

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
        return [spec.name for spec in self._specs]

    @property
    def label_specs(self) -> list[LabelSpec]:
        """Every label this moderator reports, with its parent and threshold."""
        return list(self._specs)

    @property
    def thresholds(self) -> dict[str, float]:
        return {spec.name: spec.threshold for spec in self._specs}

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

    def score_all(self, image_embeddings: np.ndarray) -> np.ndarray:
        """Final scores for every label in `category_names` (zero-shot + head)."""
        scores = self.score_embeddings(image_embeddings)
        if self.head is None:
            return scores
        if image_embeddings.shape[1] != self.head.dim:
            raise ValueError(
                f"Head expects {self.head.dim}-d embeddings, engine produced "
                f"{image_embeddings.shape[1]}-d; was it trained with a different model?"
            )
        head_scores = self.head.predict(image_embeddings)
        w = self.head_weight
        for j, col in self._blend:
            scores[:, j] = w * head_scores[:, col] + (1 - w) * scores[:, j]
        extra = head_scores[:, self._extra_cols]
        return np.clip(np.concatenate([scores, extra], axis=1), 0.0, 0.9999)

    def score_images(self, images: list[Image.Image]) -> np.ndarray:
        """Scores for already-loaded RGB PIL images (after border trimming, if enabled)."""
        if self.config.trim_borders:
            images = [trim_borders(im) for im in images]
        return self.score_all(self.engine.encode_images(images))

    def _build_result(self, scores: np.ndarray, source: str | None) -> ModerationResult:
        labels = [
            Label(spec.name, round(float(s), 4), parent=spec.parent, threshold=spec.threshold)
            for spec, s in zip(self._specs, scores)
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
        scores = self.score_images(pil_images)
        return [self._build_result(row, describe_source(s)) for row, s in zip(scores, sources)]

    def is_safe(self, image: ImageInput) -> bool:
        return self.analyze(image).is_safe

    def analyze_video(
        self,
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
        """Moderate a video by sampling frames (needs ``pip install "openmoderate[video]"``).

        Args:
            video: Path, bytes or file object.
            fps: Frames sampled per second of video.
            max_frames: Stop after this many sampled frames.
            max_duration: Stop decoding after this many seconds (``result.truncated``).
            min_frames: Ignore segments shorter than this many flagged frames, to suppress
                one-frame false positives.
            stop_on_violation: Stop at the first violating segment, for fast rejection.
            keep_frame_scores: Include every sampled frame's scores in the result.

        Returns:
            A `openmoderate.video.VideoModerationResult` with timestamped
            ``segments`` per violated label.
        """
        from openmoderate.video import analyze_video

        return analyze_video(
            self,
            video,
            fps=fps,
            max_frames=max_frames,
            max_duration=max_duration,
            min_frames=min_frames,
            stop_on_violation=stop_on_violation,
            batch_size=batch_size,
            keep_frame_scores=keep_frame_scores,
        )

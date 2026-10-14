"""Moderation configuration: which categories to check and with what thresholds."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from openmoderate.categories import DEFAULT_CATEGORIES, SAFE_PROMPTS, Category

DEFAULT_MODEL = "ViT-B-32"
DEFAULT_PRETRAINED = "laion2b_s34b_b79k"


@dataclass
class ModerationConfig:
    categories: tuple[Category, ...] = DEFAULT_CATEGORIES
    safe_prompts: tuple[str, ...] = SAFE_PROMPTS
    model_name: str = field(default_factory=lambda: os.getenv("OPENMODERATE_MODEL", DEFAULT_MODEL))
    pretrained: str = field(
        default_factory=lambda: os.getenv("OPENMODERATE_PRETRAINED", DEFAULT_PRETRAINED)
    )
    cache_dir: str | None = field(default_factory=lambda: os.getenv("OPENMODERATE_CACHE_DIR"))
    # Calibration of the zero-shot score: sigmoid((margin - bias) / temperature), where
    # margin = logit_scale * (best category prompt similarity - best safe prompt similarity).
    # Tuned on a small hand-labelled set; a margin of 2.5 maps to a score of 0.5.
    logit_scale: float = 100.0
    margin_bias: float = 2.5
    margin_temperature: float = 1.5
    # Crop letterbox bars and uniform padding before scoring (see io.trim_borders).
    trim_borders: bool = True

    def with_overrides(
        self,
        thresholds: Mapping[str, float] | None = None,
        enabled: list[str] | None = None,
        disabled: list[str] | None = None,
    ) -> ModerationConfig:
        known = {c.name for c in self.categories}
        for name in [*(thresholds or {}), *(enabled or []), *(disabled or [])]:
            if name not in known:
                raise KeyError(f"Unknown category: {name!r}. Known: {sorted(known)}")

        categories = []
        for c in self.categories:
            if enabled is not None and c.name not in enabled:
                continue
            if disabled and c.name in disabled:
                continue
            if thresholds and c.name in thresholds:
                c = replace(c, threshold=float(thresholds[c.name]))
            categories.append(c)
        return replace(self, categories=tuple(categories))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ModerationConfig:
        """Build a config from a dict (e.g. parsed YAML).

        Supported keys: ``model``, ``pretrained``, ``cache_dir``, ``safe_prompts``,
        ``thresholds`` (name -> float), ``enabled``/``disabled`` (lists of names) and
        ``custom_categories`` (list of ``{name, prompts, threshold, parent}``).
        """
        cfg = cls()
        if "model" in data:
            cfg.model_name = data["model"]
        if "pretrained" in data:
            cfg.pretrained = data["pretrained"]
        if "cache_dir" in data:
            cfg.cache_dir = data["cache_dir"]
        if "trim_borders" in data:
            cfg.trim_borders = bool(data["trim_borders"])
        if "safe_prompts" in data:
            cfg.safe_prompts = tuple(data["safe_prompts"])
        if "custom_categories" in data:
            custom = tuple(
                Category(
                    name=c["name"],
                    prompts=tuple(c["prompts"]),
                    threshold=float(c.get("threshold", 0.5)),
                    parent=c.get("parent"),
                    description=c.get("description", ""),
                    negatives=tuple(c.get("negatives", ())),
                )
                for c in data["custom_categories"]
            )
            cfg.categories = cfg.categories + custom
        return cfg.with_overrides(
            thresholds=data.get("thresholds"),
            enabled=data.get("enabled"),
            disabled=data.get("disabled"),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> ModerationConfig:
        import yaml

        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh) or {})

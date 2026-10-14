"""Result types returned by :class:`openmoderate.Moderator`."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Label:
    """A single moderation label with its confidence score in ``[0, 1]``."""

    name: str
    confidence: float
    parent: str | None = None
    threshold: float | None = None

    @property
    def flagged(self) -> bool:
        return self.threshold is not None and self.confidence >= self.threshold


@dataclass
class ModerationResult:
    """Outcome of analysing one image.

    ``labels`` holds a score for every configured category (sorted by confidence),
    ``violations`` holds only the labels whose score crossed their threshold.
    """

    labels: list[Label] = field(default_factory=list)
    source: str | None = None

    @property
    def violations(self) -> list[Label]:
        return [label for label in self.labels if label.flagged]

    @property
    def is_safe(self) -> bool:
        return not self.violations

    def score(self, name: str) -> float:
        for label in self.labels:
            if label.name == name:
                return label.confidence
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "is_safe": self.is_safe,
            "violations": [asdict(v) for v in self.violations],
            "labels": [asdict(label) for label in self.labels],
        }

    def __repr__(self) -> str:
        names = ", ".join(f"{v.name}={v.confidence:.2f}" for v in self.violations)
        return f"ModerationResult(is_safe={self.is_safe}, violations=[{names}])"

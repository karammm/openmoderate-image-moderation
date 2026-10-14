"""Train a `LinearHead` on frozen image embeddings (no GPU required)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from openmoderate.training.head import LinearHead


@dataclass
class TrainConfig:
    epochs: int = 300
    learning_rate: float = 0.05
    weight_decay: float = 1e-3
    val_split: float = 0.2
    threshold: float = 0.5
    seed: int = 0
    balance_classes: bool = True


@dataclass
class TrainReport:
    head: LinearHead
    val_metrics: dict[str, dict[str, float]] = field(default_factory=dict)
    n_train: int = 0
    n_val: int = 0


def compute_metrics(
    targets: np.ndarray, scores: np.ndarray, labels: list[str], thresholds: list[float]
) -> dict[str, dict[str, float]]:
    """Per-label precision / recall / F1 / support at the given thresholds."""
    out: dict[str, dict[str, float]] = {}
    for j, label in enumerate(labels):
        pred = scores[:, j] >= thresholds[j]
        truth = targets[:, j] >= 0.5
        tp = int((pred & truth).sum())
        fp = int((pred & ~truth).sum())
        fn = int((~pred & truth).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": int(truth.sum()),
        }
    return out


def _fit(x: np.ndarray, y: np.ndarray, cfg: TrainConfig) -> tuple[np.ndarray, np.ndarray]:
    """Full-batch Adam on class-balanced binary cross-entropy, one column per label."""
    n, dim = x.shape
    k = y.shape[1]
    rng = np.random.default_rng(cfg.seed)
    w = rng.normal(0, 0.01, size=(k, dim)).astype(np.float64)
    b = np.zeros(k)

    if cfg.balance_classes:
        pos = y.sum(axis=0).clip(min=1)
        neg = (n - y.sum(axis=0)).clip(min=1)
        sample_w = np.where(y > 0.5, n / (2 * pos), n / (2 * neg))
    else:
        sample_w = np.ones_like(y)

    # Embeddings are unit-norm with small per-dimension values; scale up so a linear model
    # can reach confident logits without huge weights.
    xs = x * np.sqrt(dim)
    m_w, v_w = np.zeros_like(w), np.zeros_like(w)
    m_b, v_b = np.zeros_like(b), np.zeros_like(b)
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    for t in range(1, cfg.epochs + 1):
        z = xs @ w.T + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        grad_z = sample_w * (p - y) / n
        g_w = grad_z.T @ xs + cfg.weight_decay * w
        g_b = grad_z.sum(axis=0)
        m_w = beta1 * m_w + (1 - beta1) * g_w
        v_w = beta2 * v_w + (1 - beta2) * g_w**2
        m_b = beta1 * m_b + (1 - beta1) * g_b
        v_b = beta2 * v_b + (1 - beta2) * g_b**2
        lr_t = cfg.learning_rate * np.sqrt(1 - beta2**t) / (1 - beta1**t)
        w -= lr_t * m_w / (np.sqrt(v_w) + eps)
        b -= lr_t * m_b / (np.sqrt(v_b) + eps)
    # Fold the input scaling back into the weights so the head works on raw embeddings.
    return w * np.sqrt(dim), b


def _split(y: np.ndarray, val_split: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Stratified-ish split: every label (and the unlabelled group) keeps a val share."""
    rng = np.random.default_rng(seed)
    groups = [np.where(y[:, j] > 0.5)[0] for j in range(y.shape[1])]
    groups.append(np.where(y.sum(axis=1) == 0)[0])
    val: set[int] = set()
    for idx in groups:
        idx = rng.permutation(idx)
        n_val = int(round(len(idx) * val_split))
        if len(idx) >= 2:
            n_val = max(1, min(n_val, len(idx) - 1))
        else:
            n_val = 0
        val.update(int(i) for i in idx[:n_val])
    val_idx = np.array(sorted(val), dtype=int)
    train_idx = np.array(sorted(set(range(len(y))) - val), dtype=int)
    return train_idx, val_idx


def train_head(
    embeddings: np.ndarray,
    targets: np.ndarray,
    labels: list[str],
    config: TrainConfig | None = None,
    *,
    model_name: str | None = None,
    pretrained: str | None = None,
    parents: dict[str, str | None] | None = None,
) -> TrainReport:
    """Train a head, report held-out metrics, then refit on all data for the final head."""
    cfg = config or TrainConfig()
    thresholds = [cfg.threshold] * len(labels)

    val_metrics: dict[str, dict[str, float]] = {}
    n_train, n_val = len(targets), 0
    if cfg.val_split > 0:
        train_idx, val_idx = _split(targets, cfg.val_split, cfg.seed)
        if len(val_idx) and len(train_idx):
            w, b = _fit(embeddings[train_idx], targets[train_idx], cfg)
            probe = LinearHead(labels, w, b)
            val_metrics = compute_metrics(
                targets[val_idx], probe.predict(embeddings[val_idx]), labels, thresholds
            )
            n_train, n_val = len(train_idx), len(val_idx)

    w, b = _fit(embeddings, targets, cfg)
    head = LinearHead(
        labels=labels,
        weights=w,
        bias=b,
        thresholds=dict(zip(labels, thresholds)),
        parents=parents or {},
        model_name=model_name,
        pretrained=pretrained,
        metrics={"validation": val_metrics, "n_train": n_train, "n_val": n_val},
    )
    return TrainReport(head=head, val_metrics=val_metrics, n_train=n_train, n_val=n_val)

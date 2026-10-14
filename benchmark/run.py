"""Reproducible accuracy benchmark on openly licensed Wikimedia Commons images.

    pip install openmoderate
    python benchmark/run.py                    # default policy
    python benchmark/run.py --config my.yaml   # your policy
    python benchmark/run.py --head my.omh      # with a trained head
    python benchmark/run.py --split dev        # the half used for tuning

The manifest is split in half (stratified per label, by content hash). Prompts and
thresholds are tuned on ``dev`` only; the published numbers are for ``test``.

Images listed in ``manifest.csv`` are downloaded once into ``benchmark/data/`` (not
committed; each file keeps its own Commons licence, see the manifest). Results are written
to ``benchmark/results.json`` and ``benchmark/RESULTS.md``.

Each image carries one label, so metrics are computed per category against the safe
images only: a riot photo that also shows a gun is not counted as a ``weapons`` false
positive just because it was labelled ``violence``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.csv"
DATA = HERE / "data"
SAFE_LABELS = {"safe", "hard_negatives"}
USER_AGENT = "openmoderate-benchmark/1.0 (https://github.com/karammm/openmoderate-image-moderation)"


def load_manifest() -> list[dict[str, str]]:
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def download(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Fetch missing images; return the rows whose image is available locally."""
    available, failed = [], 0
    for i, row in enumerate(rows, 1):
        path = DATA / row["label"] / row["file"]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(row["source_url"], headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    path.write_bytes(resp.read())
                time.sleep(0.1)  # be polite to Wikimedia
            except Exception as exc:  # network errors, removed files
                failed += 1
                print(f"  could not download {row['file']}: {exc}", file=sys.stderr)
                continue
            print(f"\rDownloading {i}/{len(rows)}", end="", file=sys.stderr)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if row.get("sha256") and digest != row["sha256"]:
            print(f"\n  note: {row['file']} differs from the recorded version", file=sys.stderr)
        available.append({**row, "path": str(path)})
    print(f"\n{len(available)} images ready, {failed} unavailable", file=sys.stderr)
    return available


def evaluate(rows: list[dict[str, str]], moderator) -> dict:
    results = moderator.analyze_batch([r["path"] for r in rows])
    flagged = [{v.name for v in res.violations} for res in results]
    categories = sorted({r["label"] for r in rows} - SAFE_LABELS)
    safe_idx = [i for i, r in enumerate(rows) if r["label"] in SAFE_LABELS]

    per_category = {}
    for cat in categories:
        pos = [i for i, r in enumerate(rows) if r["label"] == cat]
        tp = sum(cat in flagged[i] for i in pos)
        fp = sum(cat in flagged[i] for i in safe_idx)
        caught_any = sum(bool(flagged[i]) for i in pos)
        per_category[cat] = {
            "images": len(pos),
            "recall": round(tp / len(pos), 3) if pos else None,
            "precision_vs_safe": round(tp / (tp + fp), 3) if tp + fp else None,
            "false_positives_on_safe": fp,
            "flagged_any_category": round(caught_any / len(pos), 3) if pos else None,
        }

    groups: dict[str, list[int]] = defaultdict(list)
    for i in safe_idx:
        groups[f"{rows[i]['label']}: {rows[i]['group']}"].append(i)
    safe_groups = {
        name: {
            "images": len(idx),
            "flagged": sum(bool(flagged[i]) for i in idx),
            "flagged_as": sorted({c for i in idx for c in flagged[i]}),
        }
        for name, idx in sorted(groups.items())
    }
    any_fp = sum(bool(flagged[i]) for i in safe_idx)
    return {
        "categories": per_category,
        "safe": {
            "images": len(safe_idx),
            "flagged": any_fp,
            "false_positive_rate": round(any_fp / len(safe_idx), 3) if safe_idx else None,
        },
        "safe_groups": safe_groups,
        # Safe images that were flagged, and violating images whose own label was missed.
        "errors": [
            {"file": r["file"], "label": r["label"], "flagged": sorted(flagged[i])}
            for i, r in enumerate(rows)
            if (flagged[i] if r["label"] in SAFE_LABELS else r["label"] not in flagged[i])
        ],
    }


def to_markdown(report: dict, meta: dict) -> str:
    def pct(x):
        return "–" if x is None else f"{x:.0%}"

    lines = [
        "# Benchmark results",
        "",
        f"openmoderate {meta['version']} · model `{meta['model']}` · policy: {meta['policy']}"
        f" · split: {meta['split']}",
        "",
        "| Category | Images | Recall | Precision (vs. safe set) | Flagged as anything |",
        "|---|---:|---:|---:|---:|",
    ]
    for cat, m in report["categories"].items():
        lines.append(
            f"| `{cat}` | {m['images']} | {pct(m['recall'])} | "
            f"{pct(m['precision_vs_safe'])} | {pct(m['flagged_any_category'])} |"
        )
    s = report["safe"]
    lines += [
        "",
        f"**Safe images flagged:** {s['flagged']} of {s['images']} "
        f"({pct(s['false_positive_rate'])} false-positive rate).",
        "",
        "| Safe group | Images | Flagged | Flagged as |",
        "|---|---:|---:|---|",
    ]
    for name, g in report["safe_groups"].items():
        lines.append(
            f"| {name} | {g['images']} | {g['flagged']} | {', '.join(g['flagged_as']) or '–'} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", help="Policy YAML")
    parser.add_argument("--head", help="Trained head (.omh)")
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--split", choices=["test", "dev", "all"], default="test", help="Default: test"
    )
    parser.add_argument("--errors", action="store_true", help="List misclassified images")
    parser.add_argument("--no-write", action="store_true", help="Print only")
    args = parser.parse_args(argv)

    import openmoderate
    from openmoderate import Moderator

    rows = [r for r in load_manifest() if args.split == "all" or r["split"] == args.split]
    rows = download(rows)
    mod = Moderator(args.config, head=args.head, device=args.device)
    report = evaluate(rows, mod)
    custom = " ".join(p for p in (args.config, args.head) if p)
    meta = {
        "version": openmoderate.__version__,
        "model": f"{mod.config.model_name} / {mod.config.pretrained}",
        "policy": custom or "default",
        "split": args.split,
    }
    markdown = to_markdown(report, meta)
    print(markdown)
    if args.errors:
        for err in report["errors"]:
            print(f"  {err['label']:15} {err['file']:45} flagged={err['flagged']}")
    if not args.no_write and args.split == "test":
        (HERE / "results.json").write_text(json.dumps({"meta": meta, **report}, indent=1) + "\n")
        (HERE / "RESULTS.md").write_text(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

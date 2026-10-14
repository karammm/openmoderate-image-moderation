"""``openmoderate`` command-line interface.

openmoderate scan ./uploads [--json] [--fail-on-violation]
openmoderate train ./dataset -o my_head.omh
openmoderate evaluate ./dataset [--head my_head.omh]
openmoderate categories
openmoderate download
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from openmoderate import __version__


def _parse_thresholds(items: list[str] | None) -> dict[str, float]:
    out = {}
    for item in items or []:
        name, sep, value = item.partition("=")
        if not sep:
            raise SystemExit(f"--threshold expects NAME=VALUE, got {item!r}")
        out[name.strip()] = float(value)
    return out


def _add_policy_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", help="Policy YAML file")
    p.add_argument("--head", help="Trained head (.omh) from `openmoderate train`")
    p.add_argument(
        "--head-weight", type=float, default=1.0, help="Blend for labels in both (default 1.0)"
    )
    p.add_argument(
        "--threshold", "-t", action="append", metavar="NAME=VALUE", help="Override a threshold"
    )
    p.add_argument("--only", nargs="+", metavar="CATEGORY", help="Only check these categories")
    p.add_argument("--exclude", nargs="+", metavar="CATEGORY", help="Skip these categories")
    p.add_argument("--device", default="auto", help="auto, cpu, cuda or mps")


def _build_moderator(args: argparse.Namespace):
    from openmoderate import Moderator

    return Moderator(
        args.config,
        thresholds=_parse_thresholds(args.threshold),
        categories=args.only,
        exclude=args.exclude,
        head=args.head,
        head_weight=args.head_weight,
        device=args.device,
    )


def cmd_scan(args: argparse.Namespace) -> int:
    from openmoderate.io import ImageLoadError, iter_image_files

    sources: list[str] = []
    for target in args.paths:
        if target.startswith(("http://", "https://")):
            sources.append(target)
        else:
            files = iter_image_files(target)
            if not files:
                print(f"warning: no images found at {target}", file=sys.stderr)
            sources.extend(str(f) for f in files)

    mod = _build_moderator(args)
    flagged = errors = 0
    for i in range(0, len(sources), args.batch_size):
        chunk = sources[i : i + args.batch_size]
        try:
            results = mod.analyze_batch(chunk)
        except ImageLoadError:
            # Fall back to one-by-one so a single bad file doesn't sink the batch.
            results = []
            for src in chunk:
                try:
                    results.append(mod.analyze(src))
                except ImageLoadError as exc:
                    errors += 1
                    _emit_error(args, src, exc)
        for res in results:
            flagged += not res.is_safe
            _emit_result(args, res)

    if not args.json:
        total = len(sources)
        print(f"\n{total} scanned, {flagged} flagged, {errors} unreadable", file=sys.stderr)
    if args.fail_on_violation and flagged:
        return 1
    return 2 if errors else 0


def _emit_result(args: argparse.Namespace, res) -> None:
    if args.json:
        print(json.dumps(res.to_dict()))
        return
    verdict = "SAFE   " if res.is_safe else "FLAGGED"
    details = ", ".join(f"{v.name} {v.confidence:.0%}" for v in res.violations)
    print(f"{verdict}  {res.source}  {details}".rstrip())


def _emit_error(args: argparse.Namespace, src: str, exc: Exception) -> None:
    if args.json:
        print(json.dumps({"source": src, "error": str(exc)}))
    else:
        print(f"ERROR    {src}  {exc}", file=sys.stderr)


def cmd_train(args: argparse.Namespace) -> int:
    from openmoderate.config import ModerationConfig
    from openmoderate.engine.clip_engine import ClipEngine
    from openmoderate.training import FolderDataset, TrainConfig, train_head

    cfg = ModerationConfig.from_yaml(args.config) if args.config else ModerationConfig()
    dataset = FolderDataset.from_folder(args.dataset, safe_label=args.safe_label)
    print(f"Dataset: {len(dataset)} images", file=sys.stderr)
    summary = dataset.summary()
    for label, count in summary.items():
        print(f"  {label:20} {count}", file=sys.stderr)
    n_safe = summary["(no label)"]
    if n_safe < max(50, max(summary[label] for label in dataset.labels)):
        print(
            f"\nwarning: only {n_safe} images in '{args.safe_label}/'. The head learns what is "
            "NOT a violation from this folder, so fill it with a broad sample of your normal "
            "traffic (people, products, scenes...). A small or narrow safe set causes false "
            "positives that validation metrics will not reveal.",
            file=sys.stderr,
        )

    engine = ClipEngine(cfg.model_name, cfg.pretrained, device=args.device, cache_dir=cfg.cache_dir)
    embeddings = dataset.embed(engine, verbose=True)
    parents = {c.name: c.parent for c in cfg.categories if c.name in dataset.labels}
    report = train_head(
        embeddings,
        dataset.targets,
        dataset.labels,
        TrainConfig(
            epochs=args.epochs,
            learning_rate=args.lr,
            val_split=args.val_split,
            threshold=args.threshold,
        ),
        model_name=cfg.model_name,
        pretrained=cfg.pretrained,
        parents=parents,
    )
    if report.val_metrics:
        print(f"\nValidation ({report.n_val} held-out images):", file=sys.stderr)
        _print_metrics(report.val_metrics)
    else:
        print("\n(Not enough images for a validation split; no metrics.)", file=sys.stderr)
    report.head.save(args.output)
    print(f"\nSaved head to {args.output} (trained on all {len(dataset)} images)", file=sys.stderr)
    print(f'Use it with: Moderator(head="{args.output}")', file=sys.stderr)
    return 0


def _print_metrics(metrics: dict[str, dict[str, float]]) -> None:
    print(f"  {'label':20} {'precision':>9} {'recall':>7} {'f1':>6} {'n':>5}", file=sys.stderr)
    for label, m in metrics.items():
        print(
            f"  {label:20} {m['precision']:9.2f} {m['recall']:7.2f} {m['f1']:6.2f} "
            f"{m['support']:5d}",
            file=sys.stderr,
        )


def cmd_evaluate(args: argparse.Namespace) -> int:
    import numpy as np

    from openmoderate.training import FolderDataset, compute_metrics

    dataset = FolderDataset.from_folder(args.dataset, safe_label=args.safe_label)
    mod = _build_moderator(args)
    names = mod.category_names
    missing = [label for label in dataset.labels if label not in names]
    if missing:
        print(
            f"warning: dataset labels not checked by this moderator, skipped: {missing}",
            file=sys.stderr,
        )
    labels = [label for label in dataset.labels if label in names]
    if not labels:
        raise SystemExit("No dataset label matches a moderator category; nothing to evaluate.")

    embeddings = dataset.embed(mod.engine, verbose=not args.json)
    scores = mod.score_all(embeddings)
    cols = [names.index(label) for label in labels]
    targets = dataset.targets[:, [dataset.labels.index(label) for label in labels]]
    all_thresholds = mod.thresholds
    thresholds = [all_thresholds[label] for label in labels]
    metrics = compute_metrics(targets, scores[:, cols], labels, thresholds)

    # Overall: is an image flagged at all vs. does it carry any violation label.
    flagged_any = np.any(scores >= np.array([all_thresholds[n] for n in names]), axis=1)
    overall = compute_metrics(
        (dataset.targets.sum(axis=1, keepdims=True) > 0).astype(float),
        flagged_any[:, None].astype(float),
        ["any_violation"],
        [0.5],
    )
    if args.json:
        print(json.dumps({"labels": metrics, **overall}, indent=2))
    else:
        print(f"\nEvaluated {len(dataset)} images:", file=sys.stderr)
        _print_metrics({**metrics, **overall})
    return 0


def cmd_categories(args: argparse.Namespace) -> int:
    from openmoderate import Moderator

    class _NoEngine:  # categories don't need the model
        pass

    mod = Moderator(args.config, head=args.head, engine=_NoEngine())  # type: ignore[arg-type]
    zero_shot = {c.name for c in mod.config.categories}
    trained = set(mod.head.labels) if mod.head else set()
    for spec in mod.label_specs:
        kind = "+".join(
            k for k, s in (("zero-shot", zero_shot), ("trained", trained)) if spec.name in s
        )
        print(f"{spec.name:20} {spec.parent or '-':12} {spec.threshold:5.2f}  {kind}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from openmoderate.config import ModerationConfig
    from openmoderate.engine.clip_engine import ClipEngine

    cfg = ModerationConfig.from_yaml(args.config) if args.config else ModerationConfig()
    print(f"Downloading {cfg.model_name} ({cfg.pretrained})...", file=sys.stderr)
    ClipEngine(cfg.model_name, cfg.pretrained, device="cpu", cache_dir=cfg.cache_dir).encode_texts(
        ["warm up"]
    )
    print("Done. The model is cached and openmoderate can now run offline.", file=sys.stderr)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import os

    try:
        import uvicorn
    except ImportError:
        raise SystemExit(
            "`serve` needs extra dependencies: pip install 'openmoderate[server]'"
        ) from None

    # The app reads its settings from the environment so multi-worker mode works too.
    for env, value in (
        ("OPENMODERATE_CONFIG", args.config),
        ("OPENMODERATE_HEAD", args.head),
        ("OPENMODERATE_DEVICE", args.device),
    ):
        if value:
            os.environ[env] = value
    if args.allow_urls:
        os.environ["OPENMODERATE_ALLOW_URLS"] = "true"
    if args.host not in ("127.0.0.1", "localhost") and not os.getenv("OPENMODERATE_API_KEY"):
        print(
            f"warning: serving on {args.host} without OPENMODERATE_API_KEY; anyone who can "
            "reach this port can use the API.",
            file=sys.stderr,
        )
    uvicorn.run(
        "openmoderate.server.app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openmoderate", description="Open-source image content moderation."
    )
    parser.add_argument("--version", action="version", version=f"openmoderate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="Scan images, folders or URLs")
    p.add_argument("paths", nargs="+", help="Image files, folders (recursive) or URLs")
    p.add_argument("--json", action="store_true", help="Output one JSON object per line")
    p.add_argument(
        "--fail-on-violation", action="store_true", help="Exit with code 1 if anything is flagged"
    )
    p.add_argument("--batch-size", type=int, default=16)
    _add_policy_args(p)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("train", help="Train a head on a folder dataset (dataset/<label>/*.jpg)")
    p.add_argument("dataset", help="Folder with one sub-folder per label, plus safe/")
    p.add_argument("-o", "--output", default="head.omh", help="Output file (default head.omh)")
    p.add_argument("--safe-label", default="safe", help="Folder name for safe images")
    p.add_argument("--epochs", type=int, default=300)
    p.add_argument("--lr", type=float, default=0.05)
    p.add_argument("--val-split", type=float, default=0.2)
    p.add_argument("--threshold", type=float, default=0.5, help="Decision threshold to store")
    p.add_argument("--config", help="Policy YAML (for model choice and category parents)")
    p.add_argument("--device", default="auto")
    p.set_defaults(func=cmd_train)

    p = sub.add_parser("evaluate", help="Measure precision/recall on a labelled folder dataset")
    p.add_argument("dataset")
    p.add_argument("--safe-label", default="safe")
    p.add_argument("--json", action="store_true")
    _add_policy_args(p)
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("categories", help="List categories and thresholds")
    p.add_argument("--config")
    p.add_argument("--head")
    p.set_defaults(func=cmd_categories)

    p = sub.add_parser("download", help="Pre-download model weights (for offline/Docker use)")
    p.add_argument("--config")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("serve", help="Run the REST API server")
    p.add_argument("--host", default="127.0.0.1", help="Bind address (0.0.0.0 for all)")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--workers", type=int, default=1, help="Processes (each loads the model)")
    p.add_argument("--config", help="Policy YAML file")
    p.add_argument("--head", help="Trained head (.omh)")
    p.add_argument("--device", help="auto, cpu, cuda or mps")
    p.add_argument("--allow-urls", action="store_true", help="Allow {'url': ...} requests")
    p.add_argument("--log-level", default="info")
    p.set_defaults(func=cmd_serve)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

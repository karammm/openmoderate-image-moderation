"""Tests for the release and benchmark helper scripts."""

import importlib.util
from pathlib import Path

import pytest

from openmoderate.result import Label, ModerationResult

ROOT = Path(__file__).resolve().parent.parent


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_changelog_section_extracts_one_version():
    changelog = load("scripts/changelog_section.py", "changelog_section")
    text = (
        "# Changelog\n\n## [Unreleased]\n\n"
        "## [1.2.0] - 2026-01-01\n\n### Added\n- a\n\n"
        "## [1.1.0] - x\n- b\n"
    )
    assert changelog.section("v1.2.0", text) == "### Added\n- a\n"
    assert changelog.section("1.1.0", text) == "- b\n"
    with pytest.raises(SystemExit):
        changelog.section("v9.9.9", text)


def test_every_released_version_has_a_changelog_entry():
    changelog = load("scripts/changelog_section.py", "changelog_section")
    import openmoderate

    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.section(openmoderate.__version__, text).strip()


class FakeModerator:
    """Flags each image with whatever label its path says."""

    def analyze_batch(self, paths):
        out = []
        for p in paths:
            names = p.split("|")[1].split(",") if "|" in p and p.split("|")[1] else []
            out.append(ModerationResult([Label(n, 0.9, threshold=0.5) for n in names]))
        return out


def test_benchmark_metrics():
    run = load("benchmark/run.py", "benchmark_run")
    rows = [
        {"label": "weapons", "group": "g", "file": "w1", "path": "w1|weapons"},
        {"label": "weapons", "group": "g", "file": "w2", "path": "w2|"},
        {"label": "violence", "group": "g", "file": "v1", "path": "v1|violence,weapons"},
        {"label": "safe", "group": "Dogs", "file": "s1", "path": "s1|"},
        {"label": "hard_negatives", "group": "Knives", "file": "k1", "path": "k1|weapons"},
    ]
    report = run.evaluate(rows, FakeModerator())
    weapons = report["categories"]["weapons"]
    assert weapons["recall"] == 0.5
    # The violence image also flagged as weapons is NOT a weapons false positive.
    assert weapons["false_positives_on_safe"] == 1
    assert weapons["precision_vs_safe"] == 0.5
    assert report["safe"] == {"images": 2, "flagged": 1, "false_positive_rate": 0.5}
    assert report["safe_groups"]["hard_negatives: Knives"]["flagged_as"] == ["weapons"]
    assert {e["file"] for e in report["errors"]} == {"w2", "k1"}
    assert "| `weapons` | 2 | 50% | 50% | 50% |" in run.to_markdown(
        report, {"version": "x", "model": "m", "policy": "p", "split": "test"}
    )


def test_benchmark_manifest_is_well_formed():
    run = load("benchmark/run.py", "benchmark_run")
    rows = run.load_manifest()
    assert len(rows) >= 400
    assert {r["split"] for r in rows} == {"dev", "test"}
    assert all(
        r["license"] and r["page_url"].startswith("https://commons.wikimedia.org/") for r in rows
    )
    assert len({r["sha256"] for r in rows}) == len(rows)  # no duplicate images
    assert len({(r["label"], r["file"]) for r in rows}) == len(rows)

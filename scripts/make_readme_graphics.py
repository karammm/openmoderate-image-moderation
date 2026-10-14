"""Generate the README graphics in docs/assets/.

    python scripts/make_readme_graphics.py

Both SVGs follow GitHub's light/dark theme via prefers-color-scheme. Edit ROADMAP or the
demo transcript below and re-run when things change.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "assets"

ROADMAP = [
    ("v0.1", "Core engine", True),
    ("v0.2", "CLI + training", True),
    ("v0.3", "REST API + Docker", True),
    ("v0.4", "Framework middleware", False),
    ("v0.5", "Video", False),
    ("v1.0", "Stable release", False),
]

CATEGORIES = [
    ("nudity", "explicit"),
    ("sexual activity", "explicit"),
    ("suggestive", "suggestive"),
    ("violence", "violence"),
    ("gore", "violence"),
    ("weapons", "violence"),
    ("hate symbols", "hate"),
    ("drugs", "drugs"),
    ("self-harm", "self_harm"),
    ("alcohol", "substances"),
    ("tobacco", "substances"),
]

THEME = """
  :root, svg {
    --bg: #ffffff; --surface: #f6f8fa; --border: #d0d7de; --text: #1f2328;
    --muted: #59636e; --accent: #0969da; --accent-soft: #ddf4ff; --safe: #1a7f37;
    --flag: #cf222e; --code: #1f2328; --term-bg: #0d1117; --term-text: #e6edf3;
    --term-muted: #8b949e;
  }
  @media (prefers-color-scheme: dark) {
    :root, svg {
      --bg: #0d1117; --surface: #161b22; --border: #30363d; --text: #e6edf3;
      --muted: #9198a1; --accent: #4493f8; --accent-soft: #121d2f; --safe: #3fb950;
      --flag: #f85149; --code: #e6edf3; --term-bg: #010409; --term-text: #e6edf3;
      --term-muted: #8b949e;
    }
  }
  text {
    white-space: pre; fill: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
  .muted { fill: var(--muted); }
  .accent { fill: var(--accent); }
  .safe { fill: var(--safe); }
  .flag { fill: var(--flag); }
  .label { font-size: 13px; font-weight: 600; letter-spacing: 0.08em; fill: var(--muted); }
  .box { fill: var(--surface); stroke: var(--border); stroke-width: 1; }
  .arrow { stroke: var(--muted); stroke-width: 1.5; fill: none; }
"""


def text_width(s: str, size: float, mono: bool = False) -> float:
    """Rough rendered width; good enough for layout of short labels."""
    return len(s) * size * (0.61 if mono else 0.52)


def t(x, y, s, size=14, cls="", weight=None, anchor="start", extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    c = f' class="{cls}"' if cls else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}"{w}{c} text-anchor="{anchor}"{extra}>'
        f"{escape(s)}</text>"
    )


def arrow_defs() -> str:
    return (
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'style="fill: var(--muted)"/></marker></defs>'
    )


def infographic() -> str:
    W, H = 1200, 960
    L, R = 48, 1152
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-labelledby="title desc" xml:space="preserve">',
        '<title id="title">How openmoderate works</title>',
        '<desc id="desc">openmoderate is an open-source Python library that checks uploaded '
        "images for nudity, violence, weapons, hate symbols, drugs and more. It runs a CLIP "
        "model locally, compares each image against text descriptions of every category, "
        "and returns whether the image is safe. Use it as a Python library, a command-line "
        "tool or a REST API.</desc>",
        f"<style>{THEME}</style>",
        arrow_defs(),
        f'<rect width="{W}" height="{H}" rx="16" style="fill: var(--bg)"/>',
        f'<text x="{L}" y="64"><tspan font-size="36" font-weight="700">openmoderate</tspan>'
        '<tspan dx="16" font-size="20" class="muted">open-source image moderation for Python'
        "</tspan></text>",
        t(
            L,
            98,
            "Detect nudity, violence, weapons, hate symbols, drugs and more in uploaded "
            "images. Runs on your own servers: no cloud account, no per-image fees.",
            16,
            cls="muted",
        ),
    ]

    # --- How it works -----------------------------------------------------------------
    parts.append(t(L, 152, "HOW IT WORKS", cls="label"))
    steps = [
        ("1  Upload", ["file path, URL, bytes,", "upload object or image"]),
        ("2  Normalize", ["fix rotation, flatten", "alpha, cap the size"]),
        ("3  Embed", ["CLIP turns the image", "into a vector, locally"]),
        ("4  Compare", ["against text for every", "category + look-alikes"]),
        ("5  Score", ["a calibrated 0–1", "score per category"]),
        ("6  Decide", ["your thresholds give", "is_safe + violations"]),
    ]
    bw, gap, top, bh = 160, 28.8, 170, 104
    for i, (title, lines) in enumerate(steps):
        x = L + i * (bw + gap)
        parts.append(f'<rect class="box" x="{x}" y="{top}" width="{bw}" height="{bh}" rx="10"/>')
        parts.append(t(x + 14, top + 30, title, 16, weight=650))
        for j, line in enumerate(lines):
            parts.append(t(x + 14, top + 58 + j * 19, line, 13, cls="muted"))
        if i < len(steps) - 1:
            ax = x + bw
            parts.append(
                f'<line class="arrow" x1="{ax + 3}" y1="{top + bh / 2}" x2="{ax + gap - 3}" '
                f'y2="{top + bh / 2}" marker-end="url(#ah)"/>'
            )

    # Optional trained head branch: from "Embed" down, across, and up into "Score".
    embed_cx = L + 2 * (bw + gap) + bw / 2
    score_cx = L + 4 * (bw + gap) + bw / 2
    hx, hy, hw, hh = L + 3 * (bw + gap), top + bh + 34, 2 * bw + gap, 58
    parts.append(
        f'<rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="10" '
        'style="fill: var(--accent-soft); stroke: var(--accent); stroke-dasharray: 5 4"/>'
    )
    parts.append(
        t(hx + 14, hy + 24, "Optional: a head trained on your images", 14, cls="accent", weight=650)
    )
    parts.append(
        t(hx + 14, hy + 44, "openmoderate train ./dataset → blends in", 12.5, cls="muted mono")
    )
    parts.append(
        f'<path class="arrow" d="M{embed_cx},{top + bh + 3} V{hy + hh / 2} H{hx - 3}" '
        'marker-end="url(#ah)"/>'
    )
    parts.append(
        f'<line class="arrow" x1="{score_cx}" y1="{hy - 3}" x2="{score_cx}" '
        f'y2="{top + bh + 3}" marker-end="url(#ah)"/>'
    )
    parts.append(t(L, hy + 24, "Categories are plain text, so you can add", 13, cls="muted"))
    parts.append(t(L, hy + 43, "your own in YAML without any training data.", 13, cls="muted"))

    # --- Three ways to use it ---------------------------------------------------------
    y0 = hy + hh + 54
    parts.append(t(L, y0, "USE IT THREE WAYS", cls="label"))
    cards = [
        (
            "Python library",
            [
                ("$ pip install openmoderate", "muted"),
                ("from openmoderate import Moderator", ""),
                ('res = Moderator().analyze("up.jpg")', ""),
                ("res.is_safe     # False", ""),
                ("res.violations  # weapons 0.96", ""),
            ],
        ),
        (
            "Command line",
            [
                ("$ openmoderate scan ./uploads", "muted"),
                ("FLAGGED  pistol.jpg  weapons 100%", "flag"),
                ("SAFE     dog.jpg", "safe"),
                ("$ openmoderate train ./dataset", "muted"),
                ("Saved head to head.omh", ""),
            ],
        ),
        (
            "REST API + Docker",
            [
                ("$ openmoderate serve", "muted"),
                ("$ curl -F file=@up.jpg \\", "muted"),
                ("    localhost:8000/v1/moderate", "muted"),
                ('{"is_safe": false, "violations": …}', ""),
                ("$ docker run -p 8000:8000 openmoderate", "muted"),
            ],
        ),
    ]
    cw, cgap, ctop, ch = (R - L - 2 * 24) / 3, 24, y0 + 18, 178
    for i, (title, lines) in enumerate(cards):
        x = L + i * (cw + cgap)
        parts.append(f'<rect class="box" x="{x}" y="{ctop}" width="{cw}" height="{ch}" rx="10"/>')
        parts.append(t(x + 18, ctop + 32, title, 17, weight=650))
        for j, (line, cls) in enumerate(lines):
            parts.append(t(x + 18, ctop + 64 + j * 22, line, 13, cls=f"mono {cls}".strip()))

    # --- Categories -------------------------------------------------------------------
    y1 = ctop + ch + 52
    parts.append(t(L, y1, "DETECTS OUT OF THE BOX", cls="label"))
    x, y = L, y1 + 18
    chips = [name for name, _ in CATEGORIES] + ["+ your own categories"]
    for name in chips:
        w = text_width(name, 14) + 28
        if x + w > R:
            x, y = L, y + 44
        own = name.startswith("+")
        style = (
            "fill: var(--accent-soft); stroke: var(--accent); stroke-dasharray: 4 3"
            if own
            else "fill: var(--surface); stroke: var(--border)"
        )
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="32" rx="16" style="{style}"/>')
        parts.append(t(x + w / 2, y + 21, name, 14, cls="accent" if own else "", anchor="middle"))
        x += w + 10

    # --- Roadmap ----------------------------------------------------------------------
    y2 = y + 32 + 56
    parts.append(t(L, y2, "ROADMAP", cls="label"))
    ly = y2 + 40
    step = (R - L - 120) / (len(ROADMAP) - 1)
    xs = [L + 60 + i * step for i in range(len(ROADMAP))]
    last_done = max(i for i, (_, _, done) in enumerate(ROADMAP) if done)
    parts.append(
        f'<line x1="{xs[0]}" y1="{ly}" x2="{xs[-1]}" y2="{ly}" '
        'style="stroke: var(--border); stroke-width: 3"/>'
    )
    parts.append(
        f'<line x1="{xs[0]}" y1="{ly}" x2="{xs[last_done]}" y2="{ly}" '
        'style="stroke: var(--accent); stroke-width: 3"/>'
    )
    for (ver, name, done), cx in zip(ROADMAP, xs):
        style = (
            "fill: var(--accent); stroke: var(--accent)"
            if done
            else "fill: var(--bg); stroke: var(--border); stroke-width: 2"
        )
        parts.append(f'<circle cx="{cx}" cy="{ly}" r="9" style="{style}"/>')
        if done:
            parts.append(
                f'<path d="M{cx - 4},{ly} l3,3 l5,-6" '
                'style="stroke: var(--bg); stroke-width: 2; fill: none"/>'
            )
        parts.append(
            t(cx, ly + 32, ver, 15, weight=650, anchor="middle", cls="" if done else "muted")
        )
        parts.append(t(cx, ly + 52, name, 13, cls="muted", anchor="middle"))

    H = int(ly + 120)
    parts.append(
        t(
            L,
            H - 24,
            "Apache-2.0  ·  github.com/karammm/openmoderate-image-moderation",
            13,
            cls="muted",
        )
    )
    parts.append("</svg>")
    # Height depends on the layout above, so patch it into the header at the end.
    parts[0] = (
        parts[0]
        .replace('height="960"', f'height="{H}"')
        .replace('viewBox="0 0 1200 960"', f'viewBox="0 0 1200 {H}"')
    )
    bg = next(i for i, part in enumerate(parts) if part.startswith(f'<rect width="{W}"'))
    parts[bg] = parts[bg].replace('height="960"', f'height="{H}"')
    return "\n".join(parts)


# Real output from scanning public-domain test photos with the default model.
DEMO = [
    ("cmd", "pip install openmoderate"),
    ("cmd", "openmoderate scan ./uploads"),
    ("safe", "SAFE     uploads/beach.jpg"),
    ("flag", "FLAGGED  uploads/pistol.jpg     weapons 100%"),
    ("safe", "SAFE     uploads/dog.jpg"),
    ("flag", "FLAGGED  uploads/riot.jpg       violence 99%"),
    ("flag", "FLAGGED  uploads/swastika.jpg   hate_symbols 100%"),
    ("safe", "SAFE     uploads/flag_us.jpg"),
    ("out", "6 scanned, 3 flagged, 0 unreadable"),
    ("blank", ""),
    ("cmd", "openmoderate serve --port 8000 &"),
    ("cmd", "curl -F file=@cigarette.jpg localhost:8000/v1/moderate"),
    ("out", '{"is_safe": false, "violations": [{"name": "tobacco", "confidence": 0.96}]}'),
]


def demo() -> str:
    W, pad, lh, top = 900, 24, 26, 64
    H = top + len(DEMO) * lh + 40
    total = 16.0  # seconds per loop
    show_end = 92.0  # % of the loop at which everything fades out

    # Each line appears at its own time and stays until the loop resets.
    times, clock = [], 0.4
    for kind, _ in DEMO:
        clock += 0.9 if kind == "cmd" else 0.35
        times.append(clock)
        if kind == "cmd":
            clock += 0.6  # pause as if the command were running
    keyframes, rules = [], []
    for i, start in enumerate(times):
        p = min(start / total * 100, show_end - 1)
        keyframes.append(
            f"@keyframes l{i} {{ 0%, {p:.2f}% {{ opacity: 0 }} {p + 0.6:.2f}%, {show_end}% "
            f"{{ opacity: 1 }} 100% {{ opacity: 0 }} }}"
        )
        rules.append(f".l{i} {{ opacity: 0; animation: l{i} {total}s linear infinite; }}")
    css = (
        THEME
        + "\n".join(keyframes)
        + "\n"
        + "\n".join(rules)
        + """
  .term { fill: var(--term-bg); }
  .tt { fill: var(--term-text); font-size: 14px; }
  .tm { fill: var(--term-muted); font-size: 14px; }
  .ts { fill: #3fb950; font-size: 14px; }
  .tf { fill: #f85149; font-size: 14px; }
  .prompt { fill: #4493f8; font-size: 14px; }
  @media (prefers-reduced-motion: reduce) {
    .ln { animation: none !important; opacity: 1 !important; }
  }
"""
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        'role="img" aria-labelledby="dtitle ddesc" xml:space="preserve">',
        '<title id="dtitle">openmoderate terminal demo</title>',
        '<desc id="ddesc">A terminal session: installing openmoderate, scanning a folder of '
        "uploads (a pistol, a riot and a swastika are flagged, a beach, a dog and a US flag "
        "are safe), then starting the REST server and checking a photo of a cigarette, which "
        "is flagged as tobacco.</desc>",
        f"<style>{css}</style>",
        f'<rect class="term" width="{W}" height="{H}" rx="12"/>',
        '<circle cx="24" cy="22" r="6" fill="#ff5f57"/>',
        '<circle cx="44" cy="22" r="6" fill="#febc2e"/>',
        '<circle cx="64" cy="22" r="6" fill="#28c840"/>',
        f'<text x="{W / 2}" y="27" text-anchor="middle" class="tm mono" font-size="13">'
        "openmoderate demo</text>",
    ]
    cls_for = {"safe": "ts", "flag": "tf", "out": "tt", "blank": "tt"}
    for i, (kind, line) in enumerate(DEMO):
        y = top + i * lh
        if kind == "cmd":
            parts.append(
                f'<text x="{pad}" y="{y}" class="mono ln l{i}"><tspan class="prompt">$ </tspan>'
                f'<tspan class="tt">{escape(line)}</tspan></text>'
            )
        else:
            cls = f"mono ln {cls_for[kind]} l{i}"
            parts.append(f'<text x="{pad}" y="{y}" class="{cls}">{escape(line)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "how-it-works.svg").write_text(infographic(), encoding="utf-8")
    (OUT / "demo.svg").write_text(demo(), encoding="utf-8")
    print(f"Wrote {OUT / 'how-it-works.svg'} and {OUT / 'demo.svg'}")

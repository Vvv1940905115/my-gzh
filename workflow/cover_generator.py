#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate deterministic WeChat-ready images from a workflow task."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from image.make_theme_images import render_flow, render_hero  # noqa: E402

COVER_SIZE = (1200, 510)


def _slug_file(slug, suffix):
    clean = "".join(ch if ch.isalnum() else "-" for ch in slug.lower()).strip("-")
    return f"ai-{clean or 'workflow'}-{suffix}.png"


def generate_cover(title, subtitle="", slug="workflow"):
    """Render a 1200x510 cover into images/ and return its path."""
    output = _slug_file(slug, "cover")
    fig = {
        "layout": "hero",
        "output": output,
        "size": list(COVER_SIZE),
        "gradient": ["#101828", "#1d4ed8", "#0d9488"],
        "badge": "AI WORKFLOW",
        "title": title,
        "subtitle": subtitle,
        "title_size": 56 if len(title) <= 18 else 46,
        "subtitle_size": 28,
    }
    render_hero(fig)
    return ROOT / "images" / output


def generate_diagram(title, items, slug="workflow"):
    """Render a five-step or fewer flow image into images/."""
    if not 1 <= len(items) <= 5:
        raise ValueError("A workflow diagram needs 1-5 items.")
    palette = ["#2563eb", "#0d9488", "#f59e0b", "#8b5cf6", "#be185d"]
    normalized = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            item = {"title": item}
        normalized.append(
            {
                "title": item.get("title", f"Step {index + 1}"),
                "body": item.get("body", ""),
                "color": item.get("color", palette[index % len(palette)]),
            }
        )
    output = _slug_file(slug, "diagram")
    fig = {
        "layout": "flow",
        "output": output,
        "size": [1200, 510],
        "title": title,
        "top": 185,
        "card_height": 190,
        "footer_y": 425,
        "items": normalized,
    }
    render_flow(fig)
    return ROOT / "images" / output

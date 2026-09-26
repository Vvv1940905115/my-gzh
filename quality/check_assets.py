#!/usr/bin/env python3
"""Scan article directories for missing metadata, covers, and local images."""

import json
import sys
sys.dont_write_bytecode = True
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_DIR = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "out"
REPORT_PATH = OUT_DIR / "missing-assets.txt"
REQUIRED_META_FIELDS = ("title", "summary", "author", "source", "cover", "tags")
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
COVER_RATIO = 1200 / 510
RATIO_TOLERANCE = 0.02


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"__error__": str(exc)}


def inspect_image(path, is_cover=False):
    """Return a problem string for corrupt files, bad formats, or bad cover ratios."""
    if Image is None:
        return (
            "Pillow not installed; cannot inspect image "
            "(pip install -r config/requirements.lock)"
        )
    try:
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            fmt = (img.format or "").upper()
            width, height = img.size
    except Exception as exc:
        return f"corrupt or unreadable image: {exc}"
    if fmt not in ALLOWED_IMAGE_FORMATS:
        return f"unsupported image format: {fmt or 'unknown'} (use jpg/png/webp)"
    if is_cover and height:
        ratio = width / height
        if abs(ratio - COVER_RATIO) / COVER_RATIO > RATIO_TOLERANCE:
            return (
                f"cover {width}x{height} (ratio {ratio:.2f}) deviates from "
                f"2.35:1 (1200x510, tolerance {RATIO_TOLERANCE:.0%})"
            )
    return None


def scan_articles(project_root=None):
    root = Path(project_root) if project_root else PROJECT_ROOT
    problems = []
    article_files = sorted(root.glob("articles/*/article.md"))
    if not article_files:
        problems.append(("articles/", "no article.md files found"))

    try:
        from check_article import image_refs_in, resolve_path
    except ImportError:
        sys.path.insert(0, str(QUALITY_DIR))
        from check_article import image_refs_in, resolve_path

    for article in article_files:
        article_dir = article.parent
        relative = article.relative_to(root).as_posix()
        meta_path = article_dir / "meta.json"
        if not meta_path.exists():
            problems.append((relative, "missing meta.json"))
            meta = {}
        else:
            meta = read_json(meta_path)
            if "__error__" in meta:
                problems.append(
                    (meta_path.relative_to(root).as_posix(), meta["__error__"])
                )
                meta = {}
            else:
                for field in REQUIRED_META_FIELDS:
                    if field not in meta or meta.get(field) in (None, ""):
                        problems.append((relative, f"missing meta field: {field}"))

        for ref in image_refs_in(article.read_text(encoding="utf-8-sig")):
            ref_path = resolve_path(ref)
            if not ref_path.exists():
                problems.append((relative, f"missing article image: {ref}"))
                continue
            issue = inspect_image(ref_path)
            if issue:
                problems.append((relative, f"{ref}: {issue}"))

        cover = str(meta.get("cover", "")).strip()
        if cover:
            cover_path = resolve_path(cover)
            if not cover_path.exists():
                problems.append((relative, f"missing cover image: {cover}"))
            else:
                issue = inspect_image(cover_path, is_cover=True)
                if issue:
                    problems.append((relative, f"cover {cover}: {issue}"))

    return problems


def write_report(problems):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    if problems:
        lines.append(f"Asset problems: {len(problems)}")
        for location, issue in problems:
            lines.append(f"{location}: {issue}")
    else:
        lines.append("All article assets and metadata are present.")
    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    problems = scan_articles()
    write_report(problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

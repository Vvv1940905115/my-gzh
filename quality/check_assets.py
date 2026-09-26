#!/usr/bin/env python3
"""Scan article directories for missing metadata, covers, and local images."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_DIR = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "out"
REPORT_PATH = OUT_DIR / "missing-assets.txt"
REQUIRED_META_FIELDS = ("title", "summary", "author", "source", "cover", "tags")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"__error__": str(exc)}


def scan_articles():
    problems = []
    article_files = sorted((PROJECT_ROOT / "articles").glob("*/article.md"))
    if not article_files:
        problems.append(("articles/", "no article.md files found"))

    for article in article_files:
        article_dir = article.parent
        relative = article.relative_to(PROJECT_ROOT).as_posix()
        meta_path = article_dir / "meta.json"
        if not meta_path.exists():
            problems.append((relative, "missing meta.json"))
            meta = {}
        else:
            meta = read_json(meta_path)
            if "__error__" in meta:
                problems.append((meta_path.relative_to(PROJECT_ROOT).as_posix(), meta["__error__"]))
                meta = {}
            else:
                for field in REQUIRED_META_FIELDS:
                    if field not in meta or meta.get(field) in (None, ""):
                        problems.append((relative, f"missing meta field: {field}"))

        try:
            from check_article import image_refs_in, resolve_path
        except ImportError:
            sys.path.insert(0, str(QUALITY_DIR))
            from check_article import image_refs_in, resolve_path

        for ref in image_refs_in(article.read_text(encoding="utf-8-sig")):
            if not resolve_path(ref).exists():
                problems.append((relative, f"missing article image: {ref}"))

        cover = str(meta.get("cover", "")).strip()
        if cover and not resolve_path(cover).exists():
            problems.append((relative, f"missing cover image: {cover}"))

    return problems


def write_report(problems):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    if problems:
        lines.append(f"Missing assets: {len(problems)}")
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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a new article skeleton with standard directory structure and meta.json.

Usage:
    python quality/new_article.py --slug my-post-title --title "Article title"
    python quality/new_article.py --slug my-post-title --title "Article title" --author "Author"
    python quality/new_article.py --slug my-post-title --title "Article title" --cover images/cover.jpg --tags AI work
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]

ARTICLE_TEMPLATE = """# {title}

> Add a hook in the first 100 characters.

## First section

Body copy...

## Second section

Body copy...

---

![]({cover})

Caption: describe the image.

---

> Closing insight or quote.
"""

META_TEMPLATE = {
    "title": "",
    "summary": "",
    "author": "",
    "source": "",
    "cover": "",
    "tags": [],
    "video_vid": "",
}


def safe_slug(value):
    slug = re.sub(r"[^a-z0-9-]", "-", str(value).strip().lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "untitled"


def create_article(
    slug,
    title,
    summary="",
    author="",
    source="",
    cover="images/cover.jpg",
    tags=None,
    force=False,
):
    """Create the standard article scaffold and return its paths."""
    slug = safe_slug(slug)
    article_dir = ROOT / "articles" / slug
    article_file = article_dir / "article.md"
    meta_file = article_dir / "meta.json"

    if article_dir.exists() and not force:
        raise FileExistsError(f"articles/{slug}/ already exists.")

    article_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(META_TEMPLATE)
    meta["title"] = title
    meta["summary"] = summary
    meta["author"] = author
    meta["source"] = source
    meta["cover"] = cover
    meta["tags"] = tags or []

    article_file.write_text(
        ARTICLE_TEMPLATE.format(title=title, cover=cover),
        encoding="utf-8",
    )
    meta_file.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"slug": slug, "article": article_file, "meta": meta_file}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Create a new article skeleton")
    parser.add_argument("--slug", required=True, help="URL-safe slug (e.g. ai-asking-framework)")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--summary", default="", help="Summary (<=120 chars)")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--source", default="", help="Source attribution")
    parser.add_argument("--cover", default="images/cover.jpg", help="Cover image path (relative to project root)")
    parser.add_argument("--tags", nargs="*", default=[], help="Tags (space-separated)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    try:
        result = create_article(
            slug=args.slug,
            title=args.title,
            summary=args.summary,
            author=args.author,
            source=args.source,
            cover=args.cover,
            tags=args.tags if args.tags else ["AI"],
            force=args.force,
        )
    except FileExistsError:
        print(f"ERROR: articles/{safe_slug(args.slug)}/ already exists. Use --force to overwrite.")
        sys.exit(1)

    slug = result["slug"]
    article_file = result["article"]
    meta_file = result["meta"]

    print(f"Created: {article_file.relative_to(ROOT)}")
    print(f"Created: {meta_file.relative_to(ROOT)}")
    print(f"Slug:    {slug}")
    print()
    print("Next steps:")
    print(f"  1. Edit {article_file.relative_to(ROOT)} with your content.")
    print(f"  2. Place cover image at: {args.cover}")
    print(f"  3. Run: python quality/check_article.py --article articles/{slug}/article.md")
    print(f"  4. Run: python publish/md_to_wechat.py --article articles/{slug}/article.md")
    if not args.summary:
        print("  NOTE: meta.summary is empty. Fill it before pushing to WeChat.")
    cover_exists = (ROOT / args.cover).exists()
    if not cover_exists:
        print(f"  NOTE: Cover image not found: {args.cover}. Place it before pushing.")


if __name__ == "__main__":
    main()

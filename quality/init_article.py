#!/usr/bin/env python3
"""Initialize a new article workspace from the state template.

Creates articles/<slug>/, copies state-template.json into it as state.json
(pre-filled with slug/title/date), and creates an empty article.md.

Usage:
    python quality/init_article.py --slug my-article --title "我的文章标题"
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "articles"
TEMPLATE_PATH = ARTICLES_DIR / "state-template.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a new article workspace.")
    parser.add_argument("--slug", required=True, help="URL-friendly slug (directory name)")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--track", default="", help="Topic track (e.g. AI编程, Agent)")
    args = parser.parse_args()

    slug = args.slug.strip()
    if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        print(f"Error: invalid slug '{slug}'. Use a simple directory name (no slashes, no leading dot).")
        return 2

    article_dir = ARTICLES_DIR / slug
    if article_dir.exists():
        print(f"Error: article directory already exists: {article_dir}")
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if TEMPLATE_PATH.exists():
        state = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    else:
        print(f"Warning: template not found ({TEMPLATE_PATH}). Creating a minimal state.")
        state = {}

    state["slug"] = slug
    state["title"] = args.title.strip()
    state["topic_track"] = args.track.strip()
    state["created_at"] = now
    state["updated_at"] = now
    state["current_stage"] = "大纲"
    state["published"] = False

    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (article_dir / "article.md").write_text(
        f"# {args.title.strip()}\n\n", encoding="utf-8"
    )

    print(f"Article workspace created: {article_dir}")
    print(f"  state.json  <- pre-filled (slug={slug}, title={args.title.strip()})")
    print(f"  article.md  <- empty, ready to write")
    print(f"\nNext steps:")
    print(f"  1. Write your article in {article_dir / 'article.md'}")
    print(f"  2. Run quality/check_forbidden.py --file {article_dir / 'article.md'}")
    print(f"  3. Run quality/check_duplication.py --file {article_dir / 'article.md'}")
    print(f"  4. Run quality/format.py --file {article_dir / 'article.md'}")
    print(f"  5. Run quality/push_wechat_draft.py --file {article_dir / 'article.md'} --dry-run")

    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""Post-publish pipeline: extract article metrics and append to learned/performance.md.

Usage:
    python quality/post_publish.py --slug <article-slug> [--views N --share-rate F --wow-rate F --title-ctr F]

If metric flags are omitted, reads them from articles/<slug>/state.json.
After appending, updates state.json to mark published=true and record metrics.

This script is automatically invoked by push_wechat_draft.py on successful publish.
It can also be run standalone to backfill metrics for previously published articles.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEARNED_DIR = PROJECT_ROOT / "learned"
PERFORMANCE_MD = LEARNED_DIR / "performance.md"
ARTICLES_DIR = PROJECT_ROOT / "articles"


def load_state(slug: str) -> dict | None:
    state_path = ARTICLES_DIR / slug / "state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return None


def save_state(slug: str, state: dict) -> None:
    state_path = ARTICLES_DIR / slug / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_performance_row(row: dict) -> None:
    """Append a markdown table row to learned/performance.md."""
    line = (
        f"| {row['publish_date']} "
        f"| {row['title']} "
        f"| {row['slug']} "
        f"| {row['views']} "
        f"| {row['share_rate']}% "
        f"| {row['wow_rate']}% "
        f"| {row['title_ctr']}% "
        f"| {row['topic_track']} "
        f"| {row.get('note', '')} |\n"
    )
    PERFORMANCE_MD.parent.mkdir(parents=True, exist_ok=True)
    with PERFORMANCE_MD.open("a", encoding="utf-8") as f:
        f.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-publish metrics extraction and sedimentation.")
    parser.add_argument("--slug", required=True, help="Article slug (directory name under articles/)")
    parser.add_argument("--views", type=int, help="Total views")
    parser.add_argument("--share-rate", type=float, help="Share rate (%%)")
    parser.add_argument("--wow-rate", type=float, help="Wow/like rate (%%)")
    parser.add_argument("--title-ctr", type=float, help="Title CTR (%%)")
    parser.add_argument("--note", default="", help="Optional note for this row")
    args = parser.parse_args()

    state = load_state(args.slug)
    if state is None:
        print(f"Warning: no state.json found for slug '{args.slug}'. Creating a minimal one.")
        state = {
            "slug": args.slug,
            "title": args.slug,
            "topic_track": "",
            "current_stage": "发布",
            "published": False,
            "metrics": {"views": None, "share_rate": None, "wow_rate": None, "title_ctr": None},
        }

    metrics = state.get("metrics", {})
    views = args.views if args.views is not None else metrics.get("views")
    share_rate = args.share_rate if args.share_rate is not None else metrics.get("share_rate")
    wow_rate = args.wow_rate if args.wow_rate is not None else metrics.get("wow_rate")
    title_ctr = args.title_ctr if args.title_ctr is not None else metrics.get("title_ctr")

    if views is None:
        print("Error: views is required. Pass --views or ensure state.json has metrics.views.")
        return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = {
        "publish_date": now,
        "title": state.get("title", args.slug),
        "slug": args.slug,
        "views": views,
        "share_rate": share_rate if share_rate is not None else 0.0,
        "wow_rate": wow_rate if wow_rate is not None else 0.0,
        "title_ctr": title_ctr if title_ctr is not None else 0.0,
        "topic_track": state.get("topic_track", ""),
        "note": args.note,
    }

    append_performance_row(row)
    print(f"Appended performance row for '{args.slug}' to learned/performance.md")

    state["published"] = True
    state["published_at"] = now
    state["metrics"] = {
        "views": views,
        "share_rate": share_rate,
        "wow_rate": wow_rate,
        "title_ctr": title_ctr,
    }
    state["updated_at"] = now
    save_state(args.slug, state)
    print(f"Updated articles/{args.slug}/state.json: published=true, metrics recorded.")

    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""Shingle-based duplication check.

Splits an article into 13-character shingles and compares against all
archived articles under references/private/archive/. Prints duplicate
passages and returns exit code 0 (< threshold) or 1 (>= threshold).

Usage:
    python quality/check_duplication.py --file articles/my-slug/article.md
    python quality/check_duplication.py --file article.md --threshold 15
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = PROJECT_ROOT / "references" / "private" / "archive"
SHINGLE_SIZE = 13


def make_shingles(text: str, size: int) -> set[str]:
    """Produce a set of `size`-character shingles from text."""
    cleaned = text.replace("\n", " ").replace("\r", " ")
    return {cleaned[i:i + size] for i in range(len(cleaned) - size + 1)}


def find_passages(article_text: str, archive_text: str, size: int) -> list[str]:
    """Return the actual overlapping text runs between two documents."""
    a_clean = article_text.replace("\n", " ").replace("\r", " ")
    b_clean = archive_text.replace("\n", " ").replace("\r", " ")
    b_shingles = make_shingles(b_clean, size)
    passages: list[str] = []
    run: list[str] = []
    for i in range(len(a_clean) - size + 1):
        seg = a_clean[i:i + size]
        if seg in b_shingles:
            run.append(seg)
        else:
            if run:
                passages.append("".join(run))
                run = []
    if run:
        passages.append("".join(run))
    return passages


def main() -> int:
    parser = argparse.ArgumentParser(description="Shingle-based duplication check.")
    parser.add_argument("--file", required=True, help="Path to the article markdown file")
    parser.add_argument("--threshold", type=float, default=15.0, help="Max allowed duplication %%")
    args = parser.parse_args()

    article_path = Path(args.file).resolve()
    if not article_path.exists():
        print(f"Error: file not found: {article_path}")
        return 2

    article_text = article_path.read_text(encoding="utf-8")
    if len(article_text) < SHINGLE_SIZE:
        print(f"Error: article is shorter than shingle size ({SHINGLE_SIZE}). Nothing to check.")
        return 2

    if not ARCHIVE_DIR.exists() or not any(ARCHIVE_DIR.iterdir()):
        print(f"Warning: archive directory is empty or missing ({ARCHIVE_DIR}).")
        print("Nothing to compare against. Duplication rate is 0%% by default.")
        return 0

    article_shingles = make_shingles(article_text, SHINGLE_SIZE)
    total_shingles = len(article_shingles)
    if total_shingles == 0:
        print("Error: no shingles generated. Is the file empty or whitespace-only?")
        return 2

    all_dup_shingles: set[str] = set()
    duplicate_passages: list[str] = []

    for archive_file in sorted(ARCHIVE_DIR.iterdir()):
        if not archive_file.is_file():
            continue
        try:
            archive_text = archive_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            print(f"Warning: skipping unreadable file: {archive_file.name}")
            continue
        archive_shingles = make_shingles(archive_text, SHINGLE_SIZE)
        overlap = article_shingles & archive_shingles
        if overlap:
            all_dup_shingles |= overlap
            passages = find_passages(article_text, archive_text, SHINGLE_SIZE)
            if passages:
                duplicate_passages.append(f"--- {archive_file.name} ---")
                duplicate_passages.extend(f"  [{len(p)} chars] {p[:80]}{'...' if len(p) > 80 else ''}" for p in passages[:20])

    dup_count = len(all_dup_shingles)
    dup_rate = (dup_count / total_shingles) * 100

    print(f"Article: {article_path.name}")
    print(f"Total shingles: {total_shingles}")
    print(f"Duplicated shingles: {dup_count}")
    print(f"Duplication rate: {dup_rate:.1f}%")
    print(f"Threshold: {args.threshold}%")

    if duplicate_passages:
        print("\nDuplicate passages:")
        for line in duplicate_passages:
            print(line)

    if dup_rate >= args.threshold:
        print(f"\nFAIL: duplication rate {dup_rate:.1f}% exceeds threshold {args.threshold}%.")
        return 1

    print(f"\nPASS: duplication rate is within threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python3
"""Word and paragraph count checker.

Reports total characters, paragraph count, longest paragraph, and
flags paragraphs that exceed the layout rule (max ~300 chars / 5 lines).
Also estimates token count (Chinese chars ~ 1 token, English words ~ 1.3 tokens).

Usage:
    python quality/token_count.py --file articles/my-slug/article.md
"""

import argparse
import re
import sys
from pathlib import Path


MAX_PARAGRAPH_CHARS = 300


def count_stats(text: str) -> dict:
    """Extract character/paragraph/token statistics from markdown text."""
    # Strip markdown syntax for counting
    stripped = re.sub(r"^#{1,4}\s+", "", text, flags=re.MULTILINE)       # headings
    stripped = re.sub(r"```.*?```", "", stripped, flags=re.DOTALL)       # code blocks
    stripped = re.sub(r"`[^`]+`", "", stripped)                          # inline code
    stripped = re.sub(r"!\[[^\]]*\]\([^)]*\)", "[图片]", stripped)      # images
    stripped = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", stripped)       # links
    stripped = re.sub(r"[#*_>\-|]", "", stripped)                        # markdown punctuation
    stripped = re.sub(r"\s+", "", stripped)                              # all whitespace

    total_chars = len(stripped)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    para_count = len(paragraphs)

    longest = max(paragraphs, key=len) if paragraphs else ""
    longest_chars = len(re.sub(r"\s+", "", longest))
    over_limit = [
        (i + 1, len(re.sub(r"\s+", "", p)), re.sub(r"\s+", "", p)[:50])
        for i, p in enumerate(paragraphs)
        if len(re.sub(r"\s+", "", p)) > MAX_PARAGRAPH_CHARS
    ]

    # Rough token estimate
    cjk_chars = sum(1 for c in stripped if "\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf")
    latin_words = len(re.findall(r"[a-zA-Z]+", stripped))
    estimated_tokens = cjk_chars + int(latin_words * 1.3)

    return {
        "total_chars": total_chars,
        "cjk_chars": cjk_chars,
        "latin_words": latin_words,
        "paragraphs": para_count,
        "longest_paragraph_chars": longest_chars,
        "over_limit_paragraphs": over_limit,
        "estimated_tokens": estimated_tokens,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Word and paragraph count checker.")
    parser.add_argument("--file", required=True, help="Path to the article markdown file")
    args = parser.parse_args()

    article_path = Path(args.file).resolve()
    if not article_path.exists():
        print(f"Error: file not found: {article_path}")
        return 2

    text = article_path.read_text(encoding="utf-8")
    stats = count_stats(text)

    print(f"File: {article_path.name}")
    print(f"Total characters (content only): {stats['total_chars']}")
    print(f"  Chinese characters: {stats['cjk_chars']}")
    print(f"  English words: {stats['latin_words']}")
    print(f"Estimated tokens: {stats['estimated_tokens']}")
    print(f"Paragraphs: {stats['paragraphs']}")
    print(f"Longest paragraph: {stats['longest_paragraph_chars']} chars")

    if stats["over_limit_paragraphs"]:
        print(f"\nWARN: {len(stats['over_limit_paragraphs'])} paragraph(s) exceed {MAX_PARAGRAPH_CHARS} chars:")
        for para_no, chars, preview in stats["over_limit_paragraphs"]:
            print(f"  Paragraph {para_no}: {chars} chars -> {preview}...")
        print(f"\nConsider splitting these paragraphs for better mobile readability.")
        return 0

    print(f"\nPASS: all paragraphs are within {MAX_PARAGRAPH_CHARS} chars.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


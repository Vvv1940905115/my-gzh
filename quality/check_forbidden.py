#!/usr/bin/env python3
"""Forbidden/banned-word scanner.

Reads word list from references/sensitive/banned-words.txt.
Expected format per line: word|risk_level  (risk_level: high | medium | low)
Lines starting with # are comments. Blank lines are ignored.

High-risk words cause immediate FAIL (exit 1).
Medium/low-risk words produce WARN output but do not fail.

Usage:
    python quality/check_forbidden.py --file articles/my-slug/article.md
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BANNED_WORDS_PATH = PROJECT_ROOT / "references" / "sensitive" / "banned-words.txt"


def load_banned_words(path: Path) -> dict[str, str]:
    """Parse banned-words.txt into {word: risk_level}."""
    words: dict[str, str] = {}
    if not path.exists():
        return words
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        word = parts[0].strip()
        risk = parts[1].strip().lower() if len(parts) > 1 else "medium"
        if word:
            words[word] = risk
    return words


def scan(article_text: str, banned_words: dict[str, str]) -> tuple[list, list]:
    """Return (failures, warnings) as lists of (word, risk, line_number, context)."""
    failures: list = []
    warnings: list = []
    lines = article_text.splitlines()
    for word, risk in banned_words.items():
        for line_no, line in enumerate(lines, start=1):
            if word in line:
                context = line.strip()[:60]
                entry = (word, risk, line_no, context)
                if risk == "high":
                    failures.append(entry)
                else:
                    warnings.append(entry)
    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Forbidden-word scanner.")
    parser.add_argument("--file", required=True, help="Path to the article markdown file")
    args = parser.parse_args()

    article_path = Path(args.file).resolve()
    if not article_path.exists():
        print(f"Error: file not found: {article_path}")
        return 2

    banned_words = load_banned_words(BANNED_WORDS_PATH)
    if not banned_words:
        print(f"Warning: banned-words list is empty or missing ({BANNED_WORDS_PATH}).")
        print("Nothing to check. PASS by default.")
        return 0

    article_text = article_path.read_text(encoding="utf-8")
    failures, warnings = scan(article_text, banned_words)

    if failures:
        print("FAIL: high-risk forbidden words found:")
        for word, risk, line_no, context in failures:
            print(f"  Line {line_no}: [{risk}] '{word}' -> {context}")
        print(f"\nTotal high-risk hits: {len(failures)}")
        return 1

    if warnings:
        print("WARN: medium/low-risk words found:")
        for word, risk, line_no, context in warnings:
            print(f"  Line {line_no}: [{risk}] '{word}' -> {context}")
        print(f"\nTotal warnings: {len(warnings)}")
        print("\nPASS: no high-risk violations.")
        return 0

    print("PASS: no forbidden words detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


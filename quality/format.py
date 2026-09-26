#!/usr/bin/env python3
"""Markdown to WeChat-compatible HTML converter.

Attempts to use the `markdown` library if available; falls back to a
basic regex-based converter for simple documents. Output is a standalone
HTML file suitable for pasting into the WeChat editor.

Usage:
    python quality/format.py --file articles/my-slug/article.md
    python quality/format.py --file article.md --output styled.html
"""

import argparse
import re
import sys
from pathlib import Path


def try_markdown_lib(text: str) -> str | None:
    """Attempt to convert using the markdown library. Return None if unavailable."""
    try:
        import markdown  # type: ignore
        return markdown.markdown(text, extensions=["tables", "fenced_code"])
    except ImportError:
        return None


def basic_convert(text: str) -> str:
    """Minimal Markdown-to-HTML fallback for headings, bold, italic, code, lists."""
    lines = text.splitlines()
    html_lines: list[str] = []
    in_code_block = False
    in_list = False
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                lang = stripped[3:].strip()
                css = f' class="language-{lang}"' if lang else ""
                html_lines.append(f"<pre><code{css}>")
                in_code_block = True
            continue
        if in_code_block:
            html_lines.append(line)
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h{level}>{heading.group(2)}</h{level}>")
            continue

        list_item = re.match(r"^[-*]\s+(.+)$", stripped)
        if list_item:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{list_item.group(1)}</li>")
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False

        if not stripped:
            html_lines.append("<br>")
            continue

        # Inline: bold, italic, inline code, links
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
        s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
        html_lines.append(f"<p>{s}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_code_block:
        html_lines.append("</code></pre>")

    return "\n".join(html_lines)


WECHAT_STYLE = """
body { font-family: -apple-system, "PingFang SC", "Helvetica Neue", sans-serif;
       font-size: 15px; line-height: 1.8; color: #333; padding: 20px; }
h2 { font-size: 18px; font-weight: 600; margin: 28px 0 12px; color: #1a1a1a; }
h3 { font-size: 16px; font-weight: 600; margin: 20px 0 8px; color: #1a1a1a; }
p { margin: 0 0 14px; }
code { background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-size: 13px; }
pre { background: #f8f8f8; padding: 14px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #ddd; margin: 14px 0; padding: 4px 14px; color: #666; }
ul { padding-left: 24px; margin: 0 0 14px; }
table { border-collapse: collapse; width: 100%%; margin: 14px 0; }
th, td { border: 1px solid #e0e0e0; padding: 8px 10px; text-align: left; font-size: 14px; }
th { background: #f5f5f5; }
img { max-width: 100%%; height: auto; }
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown to WeChat HTML.")
    parser.add_argument("--file", required=True, help="Path to the article markdown file")
    parser.add_argument("--output", help="Output HTML path (default: same dir, .html extension)")
    args = parser.parse_args()

    article_path = Path(args.file).resolve()
    if not article_path.exists():
        print(f"Error: file not found: {article_path}")
        return 2

    text = article_path.read_text(encoding="utf-8")
    body = try_markdown_lib(text)
    if body is None:
        body = basic_convert(text)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{article_path.stem}</title>
<style>{WECHAT_STYLE}</style>
</head>
<body>
{body}
</body>
</html>"""

    if args.output:
        out_path = Path(args.output).resolve()
    else:
        out_path = article_path.with_suffix(".html")

    out_path.write_text(html, encoding="utf-8")
    print(f"Formatted HTML written to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


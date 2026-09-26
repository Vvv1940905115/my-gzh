#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert article.md into a polished, WeChat-compatible HTML fragment.

All visual styling is inline so the output survives WeChat's sanitizer
(which strips <style> blocks and class-based styles inside the article body).
Supported markdown:
  - paragraph / lead (first paragraph is auto-styled as a 导语)
  - # / ## / ### headings (accent bar style)
  - **bold**, *em*, `code`, ![alt](src), [text](href)
  - > blockquote (金句 box)
  - :::card ... :::  and  :::note ... :::  and  :::quote ... :::  containers
  - 图注：...  line right after an image -> centered caption
  - - / 1. lists, | tables |, --- divider, @video[path]
"""

import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# ---- Typography palette (WeChat-safe, inline) -------------------------------
PARAGRAPH_STYLE = (
    "margin:20px 16px; font-size:16px; line-height:2; color:#222222; "
    "letter-spacing:1px; word-spacing:1px; word-break:break-word; text-align:left;"
)
LEAD_STYLE = PARAGRAPH_STYLE
HEADING_STYLES = {
    1: (
        "margin:34px 16px 24px; font-size:19px; font-weight:bold; color:#222222; "
        "line-height:1.5; text-align:center; letter-spacing:1px;"
    ),
    2: (
        "margin:40px 16px 26px; padding-left:15px; border-left:6px solid #00997f; "
        "font-size:20px; font-weight:bold; color:#222222; line-height:1.5; "
        "text-align:left; letter-spacing:1px;"
    ),
    3: (
        "margin:26px 60px 18px; padding-bottom:6px; border-bottom:3px solid #00997f; "
        "font-size:16px; font-weight:bold; color:#222222; text-align:center; "
        "letter-spacing:1px;"
    ),
}
BLOCKQUOTE_STYLE = (
    "margin:22px 16px; padding:2px 0 2px 16px; border-left:4px solid #00997f; "
    "color:#555555; font-size:16px; line-height:2; letter-spacing:1px; "
    "word-spacing:1px; text-align:left;"
)
BLOCKQUOTE_MARK_STYLE = (
    "display:block; font-size:24px; line-height:.9; margin-bottom:4px; "
    "color:#00997f; font-family:Georgia,'Times New Roman',serif;"
)
CARD_STYLE = (
    "margin:18px 16px; padding:14px 18px; background:#ffffff; "
    "border:1px solid #ececec; border-left:4px solid #00997f; border-radius:4px;"
)
CARD_TITLE_STYLE = (
    "margin:0 0 8px; font-size:16px; font-weight:bold; color:#222222; "
    "line-height:1.6; letter-spacing:1px;"
)
CARD_LINE_STYLE = (
    "margin:6px 0; font-size:15px; line-height:1.9; color:#444444; letter-spacing:1px;"
)
NOTE_STYLE = (
    "margin:20px 16px; padding:12px 16px; background:#fafafa; "
    "border-left:4px solid #00997f; "
    "font-size:15px; line-height:2; color:#444444; letter-spacing:1px;"
)
QUOTE_BOX_STYLE = (
    "margin:24px 16px; padding:16px 20px; background:#fafafa; "
    "border-left:4px solid #00997f; "
    "color:#222222; font-size:16px; line-height:2; letter-spacing:1px;"
)
QUOTE_MARK_STYLE = (
    "display:block; font-size:28px; line-height:.9; margin-bottom:6px; "
    "color:#00997f; font-family:Georgia,'Times New Roman',serif;"
)
HIGHLIGHT_BOX_STYLE = (
    "margin:26px 16px; padding:16px 20px; background:#f0f9f6; "
    "border-left:4px solid #00997f; border-radius:4px;"
)
HIGHLIGHT_ICON_STYLE = (
    "display:inline-block; width:32px; height:32px; line-height:32px; text-align:center; "
    "background:#00997f; color:#fff; border-radius:8px; font-size:17px; margin-right:12px; vertical-align:middle;"
)
HIGHLIGHT_TEXT_STYLE = (
    "font-size:17px; font-weight:bold; color:#0b6b58; letter-spacing:1px; line-height:1.8; vertical-align:middle;"
)
CODE_BLOCK_STYLE = (
    "margin:14px 0; padding:14px 16px; background:#f6f8fa; border-radius:6px; "
    "font-family:Consolas,Menlo,monospace; font-size:13px; line-height:1.7; "
    "color:#24292f; white-space:pre-wrap; word-break:break-all;"
)
CODE_INLINE_STYLE = (
    "font-family:Consolas,Menlo,monospace; background:#f2f3f5; padding:2px 5px; "
    "border-radius:4px; font-size:13px; color:#00997f;"
)
IMAGE_WRAP_STYLE = "text-align:center; margin:26px 16px;"
IMAGE_STYLE = (
    "width:100%; max-width:1080px; display:block; margin:0 auto;"
)
CAPTION_STYLE = (
    "margin:6px 16px 24px; font-size:13px; line-height:1.5; color:#8f8f8f; "
    "text-align:right; font-weight:300; letter-spacing:1px;"
)
VIDEO_STYLE = (
    "margin:16px 0; padding:18px 14px; background:#f6f8fa; "
    "border:1px dashed #d8dee6; border-radius:6px; text-align:center; "
    "color:#8a919f; font-size:14px; line-height:1.7;"
)
LINK_STYLE = "color:#00997f; text-decoration:none;"
TABLE_STYLE = "width:100%; border-collapse:collapse; margin:16px 0; font-size:14px;"
TD_STYLE = "border:1px solid #d8dee6; padding:8px 10px; line-height:1.6;"
FOOTER_STYLE = (
    "margin:36px 16px 0; padding-top:18px; border-top:1px solid #ececec; "
    "color:#8f8f8f; font-size:13px; text-align:center; line-height:1.9; "
    "letter-spacing:1px;"
)
TAG_STYLE = (
    "display:inline-block; margin:0 4px; color:#8f8f8f; font-size:13px;"
)

TOKEN_RE = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|!\[[^\]]*\]\([^)]+\)|\[[^\]]+\]\([^)]+\))"
)


def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def default_meta_for(article_path):
    """Infer the matching meta file: article-foo.md -> meta-foo.json."""
    path = Path(article_path)
    if path.name == "article.md":
        return path.with_name("meta.json")
    if path.name.startswith("article"):
        return path.with_name("meta" + path.stem[len("article") :] + ".json")
    return path.with_name("meta.json")


def safe_slug(value):
    """Normalize a record key for file and URL-safe local storage."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value).strip()).strip("-").lower()
    return slug or "article"


def article_slug(article_path, meta_path=None):
    """Return a stable per-article record key without relying on file stems."""
    path = Path(article_path)
    meta_candidates = []
    if meta_path is not None:
        meta_candidates.append(Path(meta_path))
    meta_candidates.append(default_meta_for(path))

    for candidate in meta_candidates:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw_slug = str(data.get("slug", "")).strip()
        if raw_slug:
            return safe_slug(raw_slug)

    resolved = path.resolve()
    if path.name != "article.md":
        return safe_slug(path.stem)

    if resolved.parent == ROOT.resolve():
        return "article"

    if resolved.parent.name.lower() != "articles":
        return safe_slug(resolved.parent.name)

    # Two articles under different directories can both be named article.md.
    # Hash the project-relative path so even malformed slug directories stay unique.
    try:
        relative = resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        relative = resolved.as_posix()
    digest = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
    return safe_slug(f"article-{digest}")


def resolve_image_src(src, image_map):
    if src.startswith(("http://", "https://", "//", "data:")):
        return src
    mapped = str(image_map.get(src, "")).strip()
    return mapped or src


def render_inline(text, image_map):
    pieces = []
    position = 0
    for match in TOKEN_RE.finditer(text):
        pieces.append(html.escape(text[position : match.start()]))
        pieces.append(render_token(match.group(0), image_map))
        position = match.end()
    pieces.append(html.escape(text[position:]))
    return "".join(pieces)


def render_token(token, image_map):
    if token.startswith("**") and token.endswith("**") and len(token) > 4:
        return '<strong style="color:#00997f;">' + render_inline(token[2:-2], image_map) + "</strong>"
    if token.startswith("*") and token.endswith("*") and len(token) > 2:
        return "<em>" + render_inline(token[1:-1], image_map) + "</em>"
    if token.startswith("`") and token.endswith("`"):
        inner = html.escape(token[1:-1])
        return f'<span style="{CODE_INLINE_STYLE}">{inner}</span>'

    image_match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", token)
    if image_match:
        alt = html.escape(image_match.group(1))
        src = resolve_image_src(image_match.group(2).strip(), image_map)
        src_escaped = html.escape(src, quote=True)
        return f'<img alt="{alt}" src="{src_escaped}" style="{IMAGE_STYLE}" />'

    link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
    if link_match:
        text = render_inline(link_match.group(1), image_map)
        href = html.escape(link_match.group(2).strip(), quote=True)
        return f'<a href="{href}" style="{LINK_STYLE}">{text}</a>'

    return token


def split_table_row(line):
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def parse_blocks(lines):
    blocks = []
    paragraph = []
    index = 0

    def flush_paragraph():
        if paragraph:
            blocks.append(("paragraph", paragraph[:]))
            paragraph.clear()

    while index < len(lines):
        line = lines[index].rstrip("\n")
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        # Fenced container: :::card / :::note / :::quote ... :::
        container = re.fullmatch(r":::(\w+)", stripped)
        if container:
            flush_paragraph()
            kind = container.group(1)
            body = []
            index += 1
            while index < len(lines) and lines[index].strip() != ":::":
                body.append(lines[index].rstrip("\n"))
                index += 1
            index += 1  # skip closing :::
            blocks.append(("container", (kind, body)))
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index].rstrip("\n"))
                index += 1
            index += 1
            blocks.append(("code", code_lines))
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            blocks.append((f"heading{level}", heading.group(2).strip()))
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip()[1:].strip())
                index += 1
            blocks.append(("quote", quote_lines))
            continue

        caption = re.match(r"^图注[：:]\s*(.*)$", stripped)
        if caption:
            flush_paragraph()
            blocks.append(("caption", caption.group(1).strip()))
            index += 1
            continue

        if stripped.startswith("|"):
            next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
            if re.match(r"^\|?[\s:|-]+\|?$", next_line) and "-" in next_line:
                header_cells = split_table_row(line)
                index += 2
                rows = []
                while index < len(lines) and lines[index].strip().startswith("|"):
                    rows.append(split_table_row(lines[index]))
                    index += 1
                blocks.append(("table", (header_cells, rows)))
                continue

        video = re.fullmatch(r"@video\[([^\]]+)\]", stripped)
        if video:
            flush_paragraph()
            blocks.append(("video", video.group(1).strip()))
            index += 1
            continue

        unordered = re.match(r"^\s*[-*]\s+(.*)$", line)
        ordered = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if unordered or ordered:
            flush_paragraph()
            kind = "unordered" if unordered else "ordered"
            items = []
            pattern = re.compile(r"^\s*[-*]\s+(.*)$" if kind == "unordered" else r"^\s*\d+\.\s+(.*)$")
            while index < len(lines):
                match = pattern.match(lines[index].strip())
                if not match:
                    break
                items.append(match.group(1))
                index += 1
            blocks.append((kind, items))
            continue

        if stripped == "---":
            flush_paragraph()
            blocks.append(("hr", None))
            index += 1
            continue

        paragraph.append(line)
        index += 1

    flush_paragraph()
    return blocks


def render_container(kind, body, image_map):
    if kind == "highlight":
        text = "<br>".join(render_inline(line, image_map) for line in body)
        icon = f'<span style="{HIGHLIGHT_ICON_STYLE}">⚡</span>'
        return (
            f'<div style="{HIGHLIGHT_BOX_STYLE}">'
            f'{icon}<span style="{HIGHLIGHT_TEXT_STYLE}">{text}</span>'
            f'</div>'
        )
    if kind == "quote":
        inner = "<br>".join(render_inline(line, image_map) for line in body)
        mark = f'<span style="{QUOTE_MARK_STYLE}">“</span>'
        return f'<div style="{QUOTE_BOX_STYLE}">{mark}{inner}</div>'
    if kind == "note":
        inner = "<br>".join(render_inline(line, image_map) for line in body)
        return f'<div style="{NOTE_STYLE}">{inner}</div>'
    if kind == "card":
        pieces = []
        for i, line in enumerate(body):
            if i == 0 and line.strip().startswith("**"):
                text = render_inline(line.strip()[2:-2], image_map)
                pieces.append(f'<p style="{CARD_TITLE_STYLE}">{text}</p>')
            else:
                text = render_inline(line, image_map)
                pieces.append(f'<p style="{CARD_LINE_STYLE}">{text}</p>')
        return f'<div style="{CARD_STYLE}">{"".join(pieces)}</div>'
    # generic fallback
    inner = "<br>".join(render_inline(line, image_map) for line in body)
    return f'<div style="{NOTE_STYLE}">{inner}</div>'


def render_blocks(blocks, image_map):
    rendered = []
    emitted_paragraph = False
    for kind, payload in blocks:
        if kind == "paragraph":
            inline = render_inline("<br>".join(payload), image_map)
            if re.fullmatch(r"<img [^>]+ />", inline):
                rendered.append(f'<p style="{IMAGE_WRAP_STYLE}">{inline}</p>')
            elif not emitted_paragraph:
                rendered.append(f'<p style="{LEAD_STYLE}">{inline}</p>')
                emitted_paragraph = True
            else:
                rendered.append(f'<p style="{PARAGRAPH_STYLE}">{inline}</p>')
        elif kind.startswith("heading"):
            level = int(kind[-1])
            inline = render_inline(payload, image_map)
            rendered.append(f'<p style="{HEADING_STYLES[level]}">{inline}</p>')
        elif kind == "quote":
            inner = "<br>".join(render_inline(line, image_map) for line in payload)
            mark = f'<span style="{BLOCKQUOTE_MARK_STYLE}">“</span>'
            rendered.append(f'<blockquote style="{BLOCKQUOTE_STYLE}">{mark}{inner}</blockquote>')
        elif kind == "container":
            kind_name, body = payload
            rendered.append(render_container(kind_name, body, image_map))
        elif kind == "code":
            inner = "<br>".join(html.escape(line) for line in payload)
            rendered.append(f'<p style="{CODE_BLOCK_STYLE}">{inner}</p>')
        elif kind == "caption":
            rendered.append(f'<p style="{CAPTION_STYLE}">{render_inline(payload, image_map)}</p>')
        elif kind == "table":
            header_cells, rows = payload
            header_html = "".join(
                f'<td style="{TD_STYLE} font-weight:bold; background:#f7f8fa;">'
                f"{render_inline(cell, image_map)}</td>"
                for cell in header_cells
            )
            row_html = "".join(
                "<tr>"
                + "".join(f'<td style="{TD_STYLE}">{render_inline(cell, image_map)}</td>' for cell in row)
                + "</tr>"
                for row in rows
            )
            rendered.append(f'<table style="{TABLE_STYLE}"><tr>{header_html}</tr>{row_html}</table>')
        elif kind in ("unordered", "ordered"):
            for index, item in enumerate(payload, start=1):
                prefix = f"{index}. " if kind == "ordered" else "• "
                item_style = (
                    "margin:12px 16px; font-size:16px; line-height:2; "
                    "color:#222222; text-align:left; letter-spacing:1px;"
                )
                rendered.append(
                    f'<p style="{item_style}">{prefix}{render_inline(item, image_map)}</p>'
                )
        elif kind == "video":
            src = html.escape(payload, quote=True)
            rendered.append(
                f'<div class="wechat-video" data-video-src="{src}" '
                f'style="{VIDEO_STYLE}">文末视频占位：{src}</div>'
            )
        elif kind == "hr":
            rendered.append('<p style="margin:28px 0; border-top:1px solid #eceef1;"></p>')
    return "\n".join(rendered)


def render_footer(meta):
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tag_html = "".join(f'<span style="{TAG_STYLE}">#{html.escape(t)}</span>' for t in tags)
    author = str(meta.get("author", "")).strip()
    source = str(meta.get("source", "")).strip()
    meta_parts = [part for part in (author, source) if part]
    done_mark = "— 完 —"
    lines = ['<p style="margin:0 16px 14px; font-size:14px; color:#8f8f8f; '
             'text-align:center; letter-spacing:2px;">' + done_mark + '</p>']
    if tag_html:
        lines.append(f'<p style="{FOOTER_STYLE}">{tag_html}</p>')
    if meta_parts:
        text = "作者 / 来源：" + " / ".join(html.escape(p) for p in meta_parts)
        lines.append(f'<p style="{FOOTER_STYLE}">{text}</p>')
    return "\n".join(lines)


def make_local_srcs_relative(content, out_dir):
    def replace(match):
        src = match.group(1)
        if src.startswith(("http://", "https://", "//", "data:")):
            return match.group(0)
        candidate = Path(src)
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        try:
            relative = os.path.relpath(candidate, out_dir.resolve()).replace("\\", "/")
        except ValueError:
            return match.group(0)
        return f'src="{relative}"'

    return re.sub(r'src="([^"]+)"', replace, content)


def build_preview(title, content, local_images):
    escaped_title = html.escape(title)
    if local_images:
        notice = (
            "提示：正文里还有本地图片。先把图片上传到公众号素材库，"
            "再把链接填进 images/wechat-urls.json，重新生成后再复制。"
        )
    else:
        notice = "图片已使用微信链接，可以直接点「复制正文」。"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped_title}</title>
<style>
  body {{ margin:0; background:#eef1f4; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
  .toolbar {{ position:sticky; top:0; z-index:10; display:flex; align-items:center; gap:12px; padding:12px 20px; background:#1f2329; color:#fff; box-shadow:0 2px 8px rgba(0,0,0,.15); }}
  .toolbar h1 {{ font-size:15px; font-weight:600; margin:0; flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  .toolbar button {{ border:0; border-radius:6px; padding:8px 14px; font-size:13px; cursor:pointer; background:#2f6fdb; color:#fff; }}
  .toolbar span {{ font-size:12px; color:#c8d0d9; }}
  .notice {{ max-width:720px; margin:0 auto 20px; padding:12px 16px; background:#fff7e6; border:1px solid #ffd591; border-radius:8px; font-size:13px; color:#8c5a10; }}
  .phone {{ max-width:720px; margin:24px auto; background:#fff; padding:28px 22px 36px; box-shadow:0 4px 16px rgba(31,35,41,.08); }}
</style>
</head>
<body>
<div class="toolbar">
  <h1>{escaped_title}</h1>
  <button id="copyBtn">复制正文</button>
  <span id="status"></span>
</div>
<div class="notice">{html.escape(notice)}</div>
<div class="phone" id="preview">
{content}
</div>
<script>
  var button = document.getElementById("copyBtn");
  var status = document.getElementById("status");
  button.addEventListener("click", function () {{
    var html = document.getElementById("preview").innerHTML;
    var done = function () {{ status.textContent = "已复制"; }};
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(html).then(done, function () {{ fallbackCopy(html, done); }});
    }} else {{
      fallbackCopy(html, done);
    }}
  }});
  function fallbackCopy(text, done) {{
    var area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    try {{ document.execCommand("copy"); done(); }} catch (e) {{ status.textContent = "复制失败，请手动全选"; }}
    area.remove();
  }}
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Markdown to WeChat-compatible HTML")
    parser.add_argument("--article", default=str(ROOT / "article.md"))
    parser.add_argument(
        "--meta", default=None, help="Meta JSON file (default: inferred from --article)."
    )
    parser.add_argument("--images-map", default=str(ROOT / "images" / "wechat-urls.json"))
    parser.add_argument(
        "--out", default=None, help="Preview HTML path (default: out/<slug>.wechat.html)."
    )
    parser.add_argument(
        "--fragment-out",
        default=None,
        help="Fragment HTML path (default: out/<slug>.wechat.fragment.html).",
    )
    args = parser.parse_args()

    article_path = Path(args.article)
    meta_path = Path(args.meta) if args.meta else default_meta_for(article_path)
    record_key = article_slug(article_path, meta_path)
    meta = load_json(meta_path)
    image_map = load_json(Path(args.images_map))

    blocks = parse_blocks(article_path.read_text(encoding="utf-8").splitlines())
    content = render_blocks(blocks, image_map)
    content += "\n" + render_footer(meta)

    out_path = Path(args.out) if args.out else ROOT / "out" / f"{record_key}.wechat.html"
    content = make_local_srcs_relative(content, out_path.parent)
    local_images = re.findall(r'src="((?!https?://|//|data:)[^"]+)"', content)

    fragment_path = (
        Path(args.fragment_out)
        if args.fragment_out
        else ROOT / "out" / f"{record_key}.wechat.fragment.html"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_path.parent.mkdir(parents=True, exist_ok=True)

    title = str(meta.get("title", "公众号文章"))
    out_path.write_text(build_preview(title, content, local_images), encoding="utf-8")
    fragment_path.write_text(content + "\n", encoding="utf-8")

    print(f"Record key: {record_key}")
    print(f"Written: {out_path}")
    print(f"Written: {fragment_path}")
    if local_images:
        print("Reminder: fill images/wechat-urls.json and rerun to embed WeChat image links.")


if __name__ == "__main__":
    main()

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
import html
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# ---- Typography palette (WeChat-safe, inline) -------------------------------
PARAGRAPH_STYLE = (
    "margin:12px 0; font-size:16px; line-height:1.95; color:#2b2f36; "
    "letter-spacing:.2px; word-break:break-word; text-align:justify;"
)
LEAD_STYLE = (
    "margin:14px 0 20px; padding:14px 16px; font-size:16px; line-height:1.95; "
    "color:#1a1d23; font-weight:600; background:#f5f8ff; "
    "border-left:4px solid #2f6fdb; border-radius:0 8px 8px 0; "
    "letter-spacing:.2px; text-align:justify;"
)
HEADING_STYLES = {
    1: (
        "margin:34px 0 16px; padding:8px 0 8px 14px; border-left:5px solid #2f6fdb; "
        "font-size:20px; font-weight:800; color:#16181d; line-height:1.5; "
        "background:linear-gradient(90deg,#eef3ff 0%,#ffffff 70%); border-radius:0 6px 6px 0;"
    ),
    2: (
        "margin:30px 0 14px; padding:7px 0 7px 13px; border-left:4px solid #2f6fdb; "
        "font-size:18px; font-weight:800; color:#16181d; line-height:1.5;"
    ),
    3: (
        "margin:22px 0 10px; padding-left:11px; border-left:3px solid #9bb4e8; "
        "font-size:16px; font-weight:700; color:#22262d; line-height:1.5;"
    ),
}
BLOCKQUOTE_STYLE = (
    "margin:18px 0; padding:18px 20px 18px 22px; background:#fdf8ee; "
    "border-left:4px solid #e0a93b; border-radius:10px; color:#5b5232; "
    "font-size:15px; line-height:1.9; box-shadow:0 2px 10px rgba(224,169,59,.08);"
)
BLOCKQUOTE_MARK_STYLE = (
    "display:block; font-size:30px; line-height:.9; margin-bottom:6px; "
    "color:#e0a93b; font-family:Georgia,'Times New Roman',serif;"
)
CARD_STYLE = (
    "margin:16px 0; padding:16px 18px; background:#ffffff; "
    "border:1px solid #eef0f3; border-left:4px solid #2f6fdb; "
    "border-radius:10px; box-shadow:0 2px 10px rgba(31,35,41,.06);"
)
CARD_TITLE_STYLE = (
    "margin:0 0 8px; font-size:16px; font-weight:800; color:#1f3a6e; line-height:1.6;"
)
CARD_LINE_STYLE = (
    "margin:6px 0; font-size:15px; line-height:1.85; color:#3a4049;"
)
NOTE_STYLE = (
    "margin:18px 0; padding:16px 18px 16px 20px; background:#f6f9ff; "
    "border-left:4px solid #3b82d9; border-radius:10px; "
    "font-size:15px; line-height:1.9; color:#37445c; "
    "box-shadow:0 2px 10px rgba(59,130,217,.06);"
)
QUOTE_BOX_STYLE = (
    "margin:22px 0; padding:22px 24px 22px 26px; "
    "background:linear-gradient(135deg,#222831 0%,#2c3440 100%); "
    "border-left:4px solid #e8b53d; border-radius:14px; "
    "color:#f4f6f9; font-size:16px; font-weight:600; "
    "line-height:1.85; letter-spacing:.3px; "
    "box-shadow:0 6px 18px rgba(31,35,41,.18);"
)
QUOTE_MARK_STYLE = (
    "display:block; font-size:34px; line-height:.9; margin-bottom:8px; "
    "color:#e8b53d; font-family:Georgia,'Times New Roman',serif;"
)
HIGHLIGHT_BOX_STYLE = (
    "margin:24px 0; padding:22px 24px 22px 28px; "
    "background:linear-gradient(135deg,#f0f7ff 0%,#eaf4fc 50%,#f7fbff 100%); "
    "border-left:5px solid #2f6fdb; "
    "border-right:1px solid #d6e5f2; "
    "border-top:1px solid #d6e5f2; "
    "border-bottom:1px solid #d6e5f2; "
    "border-radius:14px; "
    "box-shadow:0 4px 20px rgba(47,111,219,.09), inset 0 1px 0 rgba(255,255,255,.8);"
)
HIGHLIGHT_ICON_STYLE = (
    "display:inline-block; width:32px; height:32px; line-height:32px; text-align:center; "
    "background:#2f6fdb; color:#fff; border-radius:8px; font-size:17px; margin-right:12px; vertical-align:middle;"
)
HIGHLIGHT_TEXT_STYLE = (
    "font-size:18px; font-weight:700; color:#1a3a5c; letter-spacing:.5px; line-height:1.7; vertical-align:middle;"
)
CODE_BLOCK_STYLE = (
    "margin:14px 0; padding:14px 16px; background:#f6f8fa; border-radius:6px; "
    "font-family:Consolas,Menlo,monospace; font-size:13px; line-height:1.7; "
    "color:#24292f; white-space:pre-wrap; word-break:break-all;"
)
CODE_INLINE_STYLE = (
    "font-family:Consolas,Menlo,monospace; background:#f2f3f5; padding:2px 5px; "
    "border-radius:4px; font-size:13px; color:#c0392b;"
)
IMAGE_WRAP_STYLE = "text-align:center; margin:18px 0;"
IMAGE_STYLE = (
    "width:100%; max-width:1080px; display:block; margin:0 auto; "
    "border-radius:10px; box-shadow:0 2px 12px rgba(31,35,41,.08);"
)
CAPTION_STYLE = (
    "margin:8px 0 18px; font-size:13px; line-height:1.6; color:#9aa1ab; "
    "text-align:center; letter-spacing:.3px;"
)
VIDEO_STYLE = (
    "margin:16px 0; padding:18px 14px; background:#f6f8fa; "
    "border:1px dashed #d8dee6; border-radius:6px; text-align:center; "
    "color:#8a919f; font-size:14px; line-height:1.7;"
)
LINK_STYLE = "color:#2f6fdb; text-decoration:none;"
TABLE_STYLE = "width:100%; border-collapse:collapse; margin:16px 0; font-size:14px;"
TD_STYLE = "border:1px solid #d8dee6; padding:8px 10px; line-height:1.6;"
FOOTER_STYLE = (
    "margin:30px 0 0; padding-top:16px; border-top:1px solid #e8eaed; "
    "color:#8a919f; font-size:13px; text-align:center; line-height:1.8;"
)
TAG_STYLE = (
    "display:inline-block; margin:4px 4px 0 0; padding:3px 10px; "
    "background:#eef3ff; color:#2f6fdb; border-radius:20px; font-size:12px;"
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
        return "<strong>" + render_inline(token[2:-2], image_map) + "</strong>"
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
                    "margin:8px 0 8px 22px; font-size:16px; line-height:1.9; "
                    "color:#2b2f36; text-align:justify;"
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
    lines = []
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
    parser.add_argument("--meta", default=str(ROOT / "meta.json"))
    parser.add_argument("--images-map", default=str(ROOT / "images" / "wechat-urls.json"))
    parser.add_argument("--out", default=str(ROOT / "out" / "article.wechat.html"))
    parser.add_argument("--fragment-out", default=str(ROOT / "out" / "article.wechat.fragment.html"))
    args = parser.parse_args()

    article_path = Path(args.article)
    meta = load_json(Path(args.meta))
    image_map = load_json(Path(args.images_map))

    blocks = parse_blocks(article_path.read_text(encoding="utf-8").splitlines())
    content = render_blocks(blocks, image_map)
    content += "\n" + render_footer(meta)

    out_path = Path(args.out)
    content = make_local_srcs_relative(content, out_path.parent)
    local_images = re.findall(r'src="((?!https?://|//|data:)[^"]+)"', content)

    fragment_path = Path(args.fragment_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_path.parent.mkdir(parents=True, exist_ok=True)

    title = str(meta.get("title", "公众号文章"))
    out_path.write_text(build_preview(title, content, local_images), encoding="utf-8")
    fragment_path.write_text(content + "\n", encoding="utf-8")

    print(f"Written: {out_path}")
    print(f"Written: {fragment_path}")
    if local_images:
        print("Reminder: fill images/wechat-urls.json and rerun to embed WeChat image links.")


if __name__ == "__main__":
    main()

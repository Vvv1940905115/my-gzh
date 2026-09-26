#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert article.md into a polished, WeChat-compatible HTML preview.

Standard Markdown is parsed by the markdown package; WeChat-specific syntax and
inline styling live in wechat_render. The preview uses inline styles so output
survives WeChat's sanitizer (which strips <style> blocks and class-based styles
inside the article body). It supports:
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
import sys
sys.dont_write_bytecode = True
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.common import default_meta_for  # noqa: E402
from wechat_render import render_article  # noqa: E402

FOOTER_STYLE = (
    "margin:36px 16px 0; padding-top:18px; border-top:1px solid #ececec; "
    "color:#8f8f8f; font-size:13px; text-align:center; line-height:1.9; "
    "letter-spacing:1px;"
)
TAG_STYLE = (
    "display:inline-block; margin:0 4px; color:#8f8f8f; font-size:13px;"
)

def load_json(path):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


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

    content = render_article(article_path.read_text(encoding="utf-8"), image_map)
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

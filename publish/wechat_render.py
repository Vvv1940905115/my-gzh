#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Markdown into WeChat-compatible HTML.

Markdown is parsed by the standard ``markdown`` package. WeChat-specific
constructs are converted to placeholders before parsing and rendered from the
resulting HTML tree, with every style injected inline.
"""

import html
import re

try:
    import markdown
except ImportError as exc:
    raise SystemExit(
        "The markdown package is required. Run: pip install -r requirements.txt"
    ) from exc

from html.parser import HTMLParser


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
IMAGE_STYLE = "width:100%; max-width:1080px; display:block; margin:0 auto;"
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
LIST_ITEM_STYLE = (
    "margin:12px 16px; font-size:16px; line-height:2; "
    "color:#222222; text-align:left; letter-spacing:1px;"
)
HR_STYLE = "margin:28px 0; border-top:1px solid #eceef1;"

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "source"}
UNWRAP_TAGS = {
    "blockquote", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ol", "p",
    "pre", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
CONTAINER_RE = re.compile(r":::(\w+)")
VIDEO_RE = re.compile(r"@video\[([^\]]+)\]")


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"type": "root", "children": []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {
            "type": "element",
            "tag": tag,
            "attrs": dict(attrs),
            "children": [],
        }
        self._append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._append(
            {"type": "element", "tag": tag, "attrs": dict(attrs), "children": []}
        )

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self._append({"type": "text", "value": data})

    def handle_comment(self, data):
        self._append({"type": "comment", "value": data})

    def _append(self, node):
        self.stack[-1]["children"].append(node)


def _escape(value):
    return html.escape(str(value), quote=True)


def _attrs(attrs):
    pieces = []
    for key, value in attrs.items():
        if value is None:
            pieces.append(key)
        else:
            pieces.append(f'{key}="{_escape(value)}"')
    return (" " + " ".join(pieces)) if pieces else ""


def _serialize(node):
    if node["type"] == "text":
        return _escape(node["value"])
    if node["type"] == "comment":
        return ""

    tag = node["tag"]
    inner = "".join(_serialize(child) for child in node["children"])
    opening = f"<{tag}{_attrs(node['attrs'])}>"
    if tag in VOID_TAGS:
        return opening
    return f"{opening}{inner}</{tag}>"


def _is_blank(node):
    return node["type"] == "text" and not node["value"].strip()


def _visible_text(node):
    if node["type"] == "text":
        return node["value"]
    if node["type"] != "element":
        return ""
    return "".join(_visible_text(child) for child in node["children"])


def _find_all(node, tag):
    found = []
    for child in node.get("children", []):
        if child.get("type") == "element":
            if child["tag"] == tag:
                found.append(child)
            found.extend(_find_all(child, tag))
    return found


def _inline(node, image_map):
    if node["type"] == "text":
        return _escape(node["value"])
    if node["type"] != "element":
        return ""

    tag = node["tag"]
    inner = "".join(_inline(child, image_map) for child in node["children"])
    if tag == "strong":
        return f'<strong style="color:#00997f;">{inner}</strong>'
    if tag == "code":
        return f'<span style="{CODE_INLINE_STYLE}">{inner}</span>'
    if tag == "a":
        attrs = dict(node["attrs"])
        attrs["style"] = LINK_STYLE
        return f'<a{_attrs(attrs)}>{inner}</a>'
    if tag == "img":
        attrs = dict(node["attrs"])
        src = str(attrs.get("src", ""))
        mapped = str(image_map.get(src, "")).strip()
        if mapped or not src.startswith(("http://", "https://", "//", "data:")):
            attrs["src"] = mapped or src
        attrs["style"] = IMAGE_STYLE
        return f'<img{_attrs(attrs)} />'
    if tag == "br":
        return "<br />"
    if tag in VOID_TAGS:
        return f"<{tag}{_attrs(node['attrs'])} />"
    if tag in UNWRAP_TAGS:
        return inner
    return f"<{tag}{_attrs(node['attrs'])}>{inner}</{tag}>"


def _fragment(markdown_text, image_map):
    rendered = markdown.markdown(markdown_text, extensions=["extra", "sane_lists"])
    builder = _TreeBuilder()
    builder.feed(rendered)
    builder.close()
    return "".join(
        _inline(child, image_map) for child in builder.root["children"] if not _is_blank(child)
    )


def _render_container(kind, body, image_map):
    if kind == "highlight":
        text = "<br>".join(_fragment(line, image_map) for line in body)
        icon = f'<span style="{HIGHLIGHT_ICON_STYLE}">⚡</span>'
        return f'<div style="{HIGHLIGHT_BOX_STYLE}">{icon}<span style="{HIGHLIGHT_TEXT_STYLE}">{text}</span></div>'
    if kind == "quote":
        inner = "<br>".join(_fragment(line, image_map) for line in body)
        return f'<div style="{QUOTE_BOX_STYLE}"><span style="{QUOTE_MARK_STYLE}">“</span>{inner}</div>'
    if kind == "note":
        inner = "<br>".join(_fragment(line, image_map) for line in body)
        return f'<div style="{NOTE_STYLE}">{inner}</div>'
    if kind == "card":
        pieces = []
        for index, line in enumerate(body):
            title_match = re.fullmatch(r"\*\*(.+)\*\*", line.strip()) if index == 0 else None
            if title_match:
                text = _fragment(title_match.group(1), image_map)
                pieces.append(f'<p style="{CARD_TITLE_STYLE}">{text}</p>')
            else:
                text = _fragment(line, image_map)
                pieces.append(f'<p style="{CARD_LINE_STYLE}">{text}</p>')
        return f'<div style="{CARD_STYLE}">{"".join(pieces)}</div>'
    inner = "<br>".join(_fragment(line, image_map) for line in body)
    return f'<div style="{NOTE_STYLE}">{inner}</div>'


def _render_video(src):
    escaped = _escape(src)
    return (
        f'<div class="wechat-video" data-video-src="{escaped}" style="{VIDEO_STYLE}">'
        f"文末视频占位：{escaped}</div>"
    )


def _preprocess(article_text):
    placeholders = []
    lines = article_text.splitlines()
    result = []
    in_code_fence = False
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            result.append(lines[index])
            index += 1
            continue
        if in_code_fence:
            result.append(lines[index])
            index += 1
            continue

        container = CONTAINER_RE.fullmatch(stripped)
        if container:
            kind = container.group(1)
            body = []
            index += 1
            while index < len(lines) and lines[index].strip() != ":::":
                body.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            placeholder = f"WECHAT-CONTAINER-{len(placeholders)}"
            placeholders.append((kind, body))
            result.append(f"<!--{placeholder}-->")
            continue

        video = VIDEO_RE.fullmatch(stripped)
        if video:
            placeholder = f"WECHAT-VIDEO-{len(placeholders)}"
            placeholders.append(video.group(1).strip())
            result.append(f"<!--{placeholder}-->")
            index += 1
            continue

        result.append(lines[index])
        index += 1
    return "\n".join(result), placeholders


def _render_comment(node, placeholders, image_map):
    value = node["value"].strip()
    if value.startswith("WECHAT-CONTAINER-"):
        kind, body = placeholders[int(value.rsplit("-", 1)[-1])]
        return _render_container(kind, body, image_map)
    if value.startswith("WECHAT-VIDEO-"):
        return _render_video(placeholders[int(value.rsplit("-", 1)[-1])])
    return ""


def _is_image_only(node):
    children = [child for child in node["children"] if not _is_blank(child)]
    return (
        len(children) == 1
        and children[0]["type"] == "element"
        and children[0]["tag"] == "img"
    )


def _render_list(node, ordered, image_map):
    pieces = []
    try:
        start = int(str(node.get("attrs", {}).get("start", "1")))
    except ValueError:
        start = 1
    for child in node["children"]:
        if not (child.get("type") == "element" and child["tag"] == "li"):
            continue
        content = []
        nested = []
        for item_child in child["children"]:
            if item_child.get("type") == "element" and item_child["tag"] in {"ul", "ol"}:
                nested.append(item_child)
            elif not _is_blank(item_child):
                content.append(_inline(item_child, image_map))
        prefix = f"{start}. " if ordered else "• "
        start += 1
        pieces.append(f'<p style="{LIST_ITEM_STYLE}">{prefix}{"".join(content)}</p>')
        for sub_list in nested:
            pieces.append(_render_list(sub_list, sub_list["tag"] == "ol", image_map))
    return "\n".join(piece for piece in pieces if piece)


def _render_table(node, image_map):
    pieces = [f'<table style="{TABLE_STYLE}">']
    for row in _find_all(node, "tr"):
        cells = [
            child
            for child in row["children"]
            if child.get("type") == "element" and child["tag"] in {"th", "td"}
        ]
        is_header = bool(cells) and all(cell["tag"] == "th" for cell in cells)
        cell_style = TD_STYLE
        if is_header:
            cell_style += " font-weight:bold; background:#f7f8fa;"
        row_html = "".join(
            f'<td style="{cell_style}">{_inline(cell, image_map)}</td>' for cell in cells
        )
        pieces.append(f"<tr>{row_html}</tr>")
    pieces.append("</table>")
    return "\n".join(pieces)


def _render_node(node, placeholders, image_map, state):
    if node["type"] == "comment":
        return _render_comment(node, placeholders, image_map)
    if node["type"] == "text":
        if not node["value"].strip():
            return ""
        state["paragraph"] = True
        return f'<p style="{PARAGRAPH_STYLE}">{_escape(node["value"].strip())}</p>'
    if node["type"] != "element":
        return ""

    tag = node["tag"]
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = min(int(tag[1]), 3)
        return f'<p style="{HEADING_STYLES[level]}">{_inline(node, image_map)}</p>'
    if tag == "p":
        text = _visible_text(node).strip()
        if text.startswith(("图注：", "图注:")):
            style = CAPTION_STYLE
        elif _is_image_only(node):
            style = IMAGE_WRAP_STYLE
        elif not state["paragraph"]:
            style = LEAD_STYLE
            state["paragraph"] = True
        else:
            style = PARAGRAPH_STYLE
        return f'<p style="{style}">{_inline(node, image_map)}</p>'
    if tag == "blockquote":
        inner = "<br>".join(
            _inline(child, image_map) for child in node["children"] if not _is_blank(child)
        )
        mark = f'<span style="{BLOCKQUOTE_MARK_STYLE}">“</span>'
        return f'<blockquote style="{BLOCKQUOTE_STYLE}">{mark}{inner}</blockquote>'
    if tag == "table":
        return _render_table(node, image_map)
    if tag == "pre":
        code_nodes = _find_all(node, "code")
        text = _visible_text(code_nodes[0] if code_nodes else node)
        return f'<p style="{CODE_BLOCK_STYLE}">{_escape(text)}</p>'
    if tag in {"ul", "ol"}:
        return _render_list(node, tag == "ol", image_map)
    if tag == "hr":
        return f'<p style="{HR_STYLE}"></p>'
    return _serialize(node)


def render_article(article_text, image_map):
    """Render article Markdown as an inline-styled WeChat HTML fragment."""
    source, placeholders = _preprocess(article_text)
    rendered = markdown.markdown(source, extensions=["extra", "sane_lists"])
    builder = _TreeBuilder()
    builder.feed(rendered)
    builder.close()
    state = {"paragraph": False}
    return "\n".join(
        _render_node(child, placeholders, image_map, state)
        for child in builder.root["children"]
    ).strip()

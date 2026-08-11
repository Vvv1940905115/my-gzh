#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取同行公众号/知乎等文章，保存到 references/ 目录。"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import trafilatura


ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = ROOT / "references"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# 公众号链接经常有访问限制，读取不到时需要提示手动保存。
WECHAT_HOSTS = {"mp.weixin.qq.com"}


def ensure_utf8_stdio():
    """让控制台能正常打印简体中文，避免 Windows 默认编码报错。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def now_iso():
    """返回本地时间的 ISO 字符串，方便记录读取时间。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_filename(text, max_len=60):
    """把标题等文字转成适合做文件名的形式。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", text).strip(" ._")
    return cleaned[:max_len] or "article"


def manual_instructions(url=""):
    """打印读取不到时的手动保存说明。"""
    print("自动读取失败，请手动处理：")
    print("1. 在浏览器打开文章，全选复制正文。")
    print("2. 保存成纯文本文件，例如 out/manual_reference.txt。")
    print("3. 再运行：")
    print("   python tools/fetch_reference.py --manual-file out/manual_reference.txt")
    if url:
        print(f"   想保留原链接时加 --url \"{url}\"")


def extract_article(html):
    """用 trafilatura 提取正文和标题，拿不到就返回空字符串。"""
    content = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
    ) or ""

    title = ""
    metadata = trafilatura.extract_metadata(html)
    if metadata is not None and getattr(metadata, "title", None):
        title = str(metadata.title).strip()

    return title, content.strip()


def fetch_from_url(url):
    """请求网页并提取正文。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    response.raise_for_status()
    return extract_article(response.text)


def build_record(url, title, content, method):
    """生成统一结构的参考文章记录。"""
    return {
        "url": url,
        "domain": urlparse(url).netloc.lower() if url else "",
        "title": title,
        "fetched_at": now_iso(),
        "method": method,
        "content": content,
        "content_length": len(content),
    }


def save_record(record, output_name=None):
    """把记录写成 JSON，默认按时间和标题命名。"""
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)

    if output_name:
        filename = output_name
        if not filename.lower().endswith(".json"):
            filename += ".json"
    else:
        base = safe_filename(record["title"] or record["domain"] or "article")
        filename = f"{datetime.now():%Y%m%d-%H%M%S}-{base}.json"

    path = REFERENCES_DIR / filename
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def save_manual_reference(file_path, url, output_name=None):
    """把手动保存的纯文本整理成参考文章记录。"""
    content = Path(file_path).read_text(encoding="utf-8").strip()
    if not content:
        raise SystemExit(f"文件为空：{file_path}")

    title = content.splitlines()[0].strip()
    record = build_record(url, title, content, "manual")
    return save_record(record, output_name)


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="读取同行文章并保存到 references/ 目录"
    )
    parser.add_argument("--url", help="同行文章链接")
    parser.add_argument(
        "--manual-file",
        help="手动复制保存的纯文本文件路径",
    )
    parser.add_argument("--output", help="自定义输出文件名，默认自动生成")
    args = parser.parse_args()

    if args.manual_file:
        path = save_manual_reference(args.manual_file, args.url or "", args.output)
        print(f"已保存：{path}")
        return

    if not args.url:
        parser.error("需要提供 --url，或使用 --manual-file 手动导入")

    domain = urlparse(args.url).netloc.lower()
    print(f"正在读取：{args.url}")

    try:
        title, content = fetch_from_url(args.url)
    except Exception as exc:
        if domain in WECHAT_HOSTS:
            manual_instructions(args.url)
        raise SystemExit(f"读取失败：{exc}")

    if not content:
        manual_instructions(args.url)
        raise SystemExit("未提取到正文。")

    record = build_record(args.url, title, content, "auto")
    path = save_record(record, args.output)

    print(f"已保存：{path}")
    print(f"标题：{record['title'] or '未识别'}")
    print(f"正文长度：{record['content_length']}")


if __name__ == "__main__":
    main()

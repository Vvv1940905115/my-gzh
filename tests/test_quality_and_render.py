#!/usr/bin/env python3
"""Regression tests for dedup, banned words, rendering, and push API helpers."""

import importlib.util
import json
import os
import shutil
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "publish"))


def load_module(name, relative):
    path = PROJECT_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


md = load_module("test_wechat_render_module", "publish/wechat_render.py")
push = load_module("test_push_api_module", "publish/wechat_push.py")
import wechat_api
quality = load_module("test_quality_functions", "quality/check_article.py")


class ContractTest:
    def __init__(self):
        self.failures = []

    def check(self, name, condition, detail=""):
        if condition:
            print(f"PASS {name}")
        else:
            suffix = f": {detail}" if detail else ""
            print(f"FAIL {name}{suffix}")
            self.failures.append(name)


def test_quality(case):
    root = Path(tempfile.mkdtemp(prefix="wechat-quality-"))
    old_root = quality.ROOT
    quality.ROOT = root
    try:
        source = root / "archive.md"
        repeated = "这是一段足够长并且用于重复检测的正文"
        source.write_text(repeated, encoding="utf-8")
        case.check(
            "dedup detects repeated run",
            not quality.dedup_check(f"开头 {repeated} 结尾", [source], 13, 25.0),
        )
        source.write_text("完全不同而且唯一来源文本", encoding="utf-8")
        case.check(
            "dedup allows unique article",
            quality.dedup_check("全新独立正文没有被旧来源覆盖", [source], 13, 25.0),
        )

        words_path = root / "banned.txt"
        words_path.write_text("强制|高|替换\n提示|中|确认\n", encoding="utf-8")
        words = quality.load_banned_words(words_path)
        case.check("banned words load table rows", words == [("强制", "高", "替换"), ("提示", "中", "确认")], str(words))
        case.check("high risk word blocks publish", not quality.banned_words_check("不要强制", {}, words))
        case.check("medium risk word only warns", quality.banned_words_check("不要提示", {}, words))

        missing_source = quality.citation_warnings("平台新增了 1200 万人。")
        with_source = quality.citation_warnings("平台新增了 1200 万人，来源：官网报告。")
        case.check("data paragraph without source warns", missing_source == ["平台新增了 1200 万人。"], str(missing_source))
        case.check("data paragraph with source passes", with_source == [], str(with_source))

        citation_cases = [
            ("增长了三倍", "Chinese numeral + multiplier"),
            ("突破千万用户", "Breaking through 10M"),
            ("占全球市场一半", "Half of global market"),
            ("收入达到 5000 万", "Revenue 50M"),
            ("五成用户选择了", "50% of users"),
            ("成本降至 2 亿美元", "Cost down to 200M USD"),
            ("翻了十番", "Multiplied by 2^10"),
            ("提升了 20 个点", "20 percentage points"),
            ("将近一半的用户", "Nearly half"),
            ("接近三成的受访者", "Nearly 30%"),
            ("超过百万的播放量", "Over 1M views"),
        ]
        for cite_text, cite_desc in citation_cases:
            cite_result = quality.citation_warnings(cite_text)
            case.check(
                f"citation catches {cite_desc}",
                len(cite_result) > 0,
                f"Pattern '{cite_text}' was MISSED (got {cite_result})"
            )
        case.check(
            "citation no false positive on prose",
            quality.citation_warnings("这篇文章没有数据，只是感想。") == [],
        )
    finally:
        quality.ROOT = old_root
        shutil.rmtree(root, ignore_errors=True)


def test_render(case):
    image_map = {"images/a.png": "https://mmbiz.example/a.png"}
    article = """# 标题

第一段 **重点** 内容。

![图片](images/a.png)

图注：图片说明

| 列一 | 列二 |
| --- | --- |
| 甲 | 乙 |

- 项目一
- 项目二

:::highlight
核心观点
:::

@video[media/demo.mp4]
"""
    rendered = md.render_article(article, image_map)
    checks = {
        "heading has inline style and no nested h1": '<p style="' in rendered and "<h1>" not in rendered,
        "bold text is accent styled": '<strong style="color:#00997f;">重点</strong>' in rendered,
        "remote image map is applied": "https://mmbiz.example/a.png" in rendered,
        "caption uses caption style": md.CAPTION_STYLE in rendered and rendered.index("图片说明") > -1,
        "standard table is styled": "<table" in rendered and "<thead>" not in rendered,
        "lists are flattened for WeChat": "• 项目一" in rendered and "<ul>" not in rendered,
        "highlight container remains supported": md.HIGHLIGHT_BOX_STYLE in rendered,
        "video keeps machine-readable source": 'data-video-src="media/demo.mp4"' in rendered,
        "no raw markdown remains": "**" not in rendered and ":::" not in rendered,
    }
    for name, condition in checks.items():
        case.check(name, condition, rendered)


def test_push_helpers(case):
    root = Path(tempfile.mkdtemp(prefix="wechat-push-"))
    old_root = push.ROOT
    old_home = os.environ.get("CODEX_HOME")
    old_cache_file = wechat_api.TOKEN_CACHE_FILE
    push.ROOT = root
    wechat_api.TOKEN_CACHE_FILE = root / "out" / "access-token.json"
    os.environ["CODEX_HOME"] = str(root / ".codex")
    try:
        placeholder_dir = root / ".codex" / "skills" / "wechat-publisher"
        placeholder_dir.mkdir(parents=True)
        placeholder_file = placeholder_dir / "config.json"
        placeholder_file.write_text(
            json.dumps({"app_id": "YOUR_APP_ID_HERE", "app_secret": "YOUR_APP_SECRET_HERE"}),
            encoding="utf-8",
        )
        try:
            push.load_config()
            rejected = False
        except SystemExit:
            rejected = True
        case.check("push rejects placeholder credentials", rejected)

        placeholder_file.write_text(
            json.dumps({"app_id": "wx123", "app_secret": "secret"}),
            encoding="utf-8",
        )
        config = push.load_config()
        case.check("push loads valid credentials", config["app_id"] == "wx123")

        original_get_json = wechat_api.get_json
        wechat_api.get_json = lambda url: {"access_token": "token-from-mock"}
        try:
            token = push.get_access_token(config)
        finally:
            wechat_api.get_json = original_get_json
        case.check("access token API uses injected mock", token == "token-from-mock")
    finally:
        push.ROOT = old_root
        wechat_api.TOKEN_CACHE_FILE = old_cache_file
        if old_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = old_home
        shutil.rmtree(root, ignore_errors=True)


def test_assets(case):
    assets = load_module("test_check_assets", "quality/check_assets.py")
    root = Path(tempfile.mkdtemp(prefix="wechat-assets-"))
    old_quality_root = quality.ROOT
    quality.ROOT = root
    quality_dir = str(PROJECT_ROOT / "quality")
    if quality_dir not in sys.path:
        sys.path.insert(0, quality_dir)
    import check_article
    old_check_root = check_article.ROOT
    check_article.ROOT = root
    old_cwd = os.getcwd()
    os.chdir(root)
    try:
        demo_dir = root / "articles" / "demo"
        bad_dir = root / "articles" / "bad"
        (root / "images").mkdir()
        demo_dir.mkdir(parents=True)
        bad_dir.mkdir(parents=True)
        meta = {
            "title": "t", "summary": "s", "author": "a",
            "source": "x", "cover": "images/cover-demo.jpg", "tags": [],
        }
        bad_meta = dict(meta, cover="images/cover-bad.jpg")
        (demo_dir / "article.md").write_text("![pic](images/pic-demo.png)\n", encoding="utf-8")
        (demo_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        (bad_dir / "article.md").write_text(
            "![broken](images/broken-bad.png)\n![bmp](images/pic-bad.bmp)\n", encoding="utf-8"
        )
        (bad_dir / "meta.json").write_text(json.dumps(bad_meta, ensure_ascii=False), encoding="utf-8")

        assets.Image.new("RGB", (940, 400)).save(root / "images" / "cover-demo.jpg")
        assets.Image.new("RGB", (600, 400)).save(root / "images" / "pic-demo.png")
        assets.Image.new("RGB", (800, 600)).save(root / "images" / "cover-bad.jpg")
        assets.Image.new("RGB", (600, 400)).save(root / "images" / "pic-bad.bmp")
        (root / "images" / "broken-bad.png").write_bytes(b"not an image")

        problems = assets.scan_articles(root)
        joined = "\n".join(f"{loc}: {issue}" for loc, issue in problems)
        case.check(
            "assets accepts valid cover ratio and body image",
            not any(loc.startswith("articles/demo") for loc, _ in problems),
            joined,
        )
        case.check(
            "assets rejects off-ratio cover",
            any("articles/bad" in loc and "ratio" in issue for loc, issue in problems),
            joined,
        )
        case.check(
            "assets rejects non-web image format",
            any("articles/bad" in loc and "unsupported image format" in issue for loc, issue in problems),
            joined,
        )
        case.check(
            "assets rejects corrupt image",
            any("articles/bad" in loc and "corrupt or unreadable" in issue for loc, issue in problems),
            joined,
        )
    finally:
        os.chdir(old_cwd)
        quality.ROOT = old_quality_root
        check_article.ROOT = old_check_root
        shutil.rmtree(root, ignore_errors=True)


def main():
    case = ContractTest()
    test_quality(case)
    test_render(case)
    test_push_helpers(case)
    test_assets(case)
    if case.failures:
        print(f"{len(case.failures)} quality/render test(s) failed")
        return 1
    print("All quality/render tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

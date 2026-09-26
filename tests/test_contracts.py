#!/usr/bin/env python3
"""Small regression tests for path, slug, draft-id, and image contracts."""

import importlib.util
import json
import shutil
import sys
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


md = load_module("test_md_to_wechat", "publish/md_to_wechat.py")
push = load_module("test_push_wechat_draft", "publish/push_wechat_draft.py")
quality = load_module("test_check_article", "quality/check_article.py")


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


def run_tests(case):
    root = Path(tempfile.mkdtemp(prefix="wechat-contracts-"))
    old_md_root = md.ROOT
    old_push_root = push.ROOT
    old_quality_root = quality.ROOT
    md.ROOT = root
    push.ROOT = root
    quality.ROOT = root
    try:
        article_dir = root / "articles" / "meta-override"
        article_dir.mkdir(parents=True)
        article = article_dir / "article.md"
        article.write_text("# demo\n", encoding="utf-8")
        meta = article_dir / "meta.json"
        meta.write_text(json.dumps({"slug": "override-slug"}, ensure_ascii=False), encoding="utf-8")
        case.check("meta slug overrides directory", md.article_slug(article, meta) == "override-slug")

        fallback_dir = root / "articles" / "directory-fallback"
        fallback_dir.mkdir(parents=True)
        fallback_article = fallback_dir / "article.md"
        fallback_article.write_text("# demo\n", encoding="utf-8")
        case.check("article.md uses directory slug", md.article_slug(fallback_article) == "directory-fallback")

        root_article = root / "article.md"
        root_article.write_text("# demo\n", encoding="utf-8")
        case.check("root article keeps legacy key", md.article_slug(root_article) == "article")

        malformed_article = root / "articles" / "article.md"
        malformed_article.write_text("# demo\n", encoding="utf-8")
        malformed_key = md.article_slug(malformed_article)
        case.check(
            "malformed article path gets unique hash key",
            malformed_key.startswith("article-") and len(malformed_key) == len("article-") + 12,
            malformed_key,
        )

        expected_meta = root / "articles" / "foo" / "meta.json"
        case.check(
            "meta is inferred beside article.md",
            md.default_meta_for(root / "articles" / "foo" / "article.md") == expected_meta,
        )

        case.check("safe_slug keeps URL-safe text", md.safe_slug("中文 Slug!") == "slug")
        case.check("empty slug falls back to article", md.safe_slug("!!!") == "article")

        case.check(
            "draft id is per-slug",
            push.draft_id_path("override-slug") == root / "out" / "last-draft-id-override-slug.txt",
        )
        case.check(
            "legacy root draft id stays compatible",
            push.draft_id_path("article") == root / "out" / "last-draft-id.txt",
        )

        out_dir = root / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        content = '<img src="images/test.png" alt="test">'
        relative = md.make_local_srcs_relative(content, out_dir)
        case.check("local image src becomes out-relative", relative == '<img src="../images/test.png" alt="test">', relative)

        quality_root_image = root / "quality-images" / "unique.png"
        quality_root_image.parent.mkdir(parents=True)
        quality_root_image.write_bytes(b"png")
        resolved = quality.resolve_path("quality-images/unique.png")
        case.check("quality resolves image from project root", resolved == quality_root_image.resolve(), str(resolved))

        refs = quality.image_refs_in('![remote](https://example.com/a.png)\n![local](images/a.png)\n![spaced](<E:/demo/my image (2).png>)')
        case.check("quality handles local and angle-bracket image refs", refs == ["images/a.png", "E:/demo/my image (2).png"], str(refs))
    finally:
        md.ROOT = old_md_root
        push.ROOT = old_push_root
        quality.ROOT = old_quality_root
        shutil.rmtree(root, ignore_errors=True)


def main():
    case = ContractTest()
    run_tests(case)
    if case.failures:
        print(f"{len(case.failures)} contract test(s) failed")
        return 1
    print("All contract tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Regression tests for the end-to-end WeChat AI workflow."""

import importlib.util
import json
import shutil
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import image.make_theme_images as theme_images


def load_module(name, relative):
    path = PROJECT_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = load_module("test_ai_workflow", "workflow/run_ai_workflow.py")
import check_article as quality_checker
import cover_generator
import quality.new_article as new_article
import publish.wechat_push as wechat_push


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


class PatchedRoot:
    def __init__(self, root):
        self.targets = [
            (workflow, "ROOT", workflow.ROOT),
            (quality_checker, "ROOT", quality_checker.ROOT),
            (new_article, "ROOT", new_article.ROOT),
            (cover_generator, "ROOT", cover_generator.ROOT),
            (theme_images, "OUTPUT_DIR", theme_images.OUTPUT_DIR),
            (wechat_push, "ROOT", wechat_push.ROOT),
        ]
        self.root = root

    def __enter__(self):
        for module, attr, _ in self.targets:
            setattr(module, attr, self.root)
        setattr(theme_images, "OUTPUT_DIR", self.root / "images")
        return self.root

    def __exit__(self, exc_type, exc_value, traceback):
        for module, attr, old_value in self.targets:
            setattr(module, attr, old_value)


def run_review_case(case):
    root = Path(tempfile.mkdtemp(prefix="wechat-workflow-"))
    try:
        with PatchedRoot(root):
            task = {
                "slug": "workflow-smoke",
                "title": "AI 自动化工作流",
                "brief": "演示自动生成、质检、配图和预览。",
                "keywords": ["AI", "automation"],
                "tags": ["AI"],
                "content_markdown": "# AI 自动化工作流\n\n第一段介绍工作流。",
                "diagram": {
                    "title": "自动化流程",
                    "items": [
                        {"title": "接收任务", "body": "JSON 输入"},
                        {"title": "生成内容", "body": "Markdown"},
                        {"title": "质检配图", "body": "硬校验"},
                    ],
                },
            }
            result = workflow.run_workflow(task)
            article_file = root / "articles" / "workflow-smoke" / "article.md"
            meta_file = root / "articles" / "workflow-smoke" / "meta.json"
            article_text = article_file.read_text(encoding="utf-8")
            meta = json.loads(meta_file.read_text(encoding="utf-8"))

            case.check(
                "workflow creates review record",
                result["status"] == "review_required",
                str(result),
            )
            case.check(
                "workflow writes article scaffold",
                article_file.exists() and "# AI" in article_text,
            )
            case.check(
                "workflow writes generated diagram",
                "images/ai-workflow-smoke-diagram.png" in article_text,
            )
            case.check(
                "workflow writes generated cover",
                meta["cover"] == "images/ai-workflow-smoke-cover.png",
            )
            case.check("generated cover exists", (root / meta["cover"]).exists())
            case.check(
                "generated diagram exists",
                (root / "images" / "ai-workflow-smoke-diagram.png").exists(),
            )
            case.check("workflow writes preview", Path(result["preview_file"]).exists())
            case.check("workflow writes audit log", Path(result["log_file"]).exists())
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_push_contract(case):
    root = Path(tempfile.mkdtemp(prefix="wechat-workflow-push-"))
    try:
        with PatchedRoot(root):
            task = {
                "slug": "workflow-push",
                "title": "AI 推送前演练",
                "content_markdown": "# AI 推送前演练\n\n第一段。",
                "diagram": {"title": "流程", "items": ["任务", "生成"]},
            }
            prepared = workflow.prepare_article(task, task["content_markdown"])
            push_result = wechat_push.push_draft(
                article=prepared["article_file"],
                meta=prepared["meta_file"],
                dry_run=True,
                interactive=False,
            )
            case.check(
                "dry run avoids API and writes preview",
                push_result["dry_run"] is True,
            )
            case.check(
                "dry run validates generated images",
                Path(push_result["preview_file"]).exists(),
            )
            case.check(
                "dry run payload preview exists",
                (root / "out" / "workflow-push.wechat.dry-run.html").exists(),
            )

            captured = {}

            def fake_push_draft(**kwargs):
                captured.update(kwargs)
                return {
                    "preview_file": str(root / "out" / "fake.html"),
                    "draft_media_id": "draft-id",
                    "cover_media_id": "cover-id",
                    "dry_run": False,
                }

            with patch.object(workflow.wechat_push, "push_draft", fake_push_draft):
                pushed = workflow.run_workflow(dict(task), push=True, force=True, new_draft=True)
            case.check("workflow passes interactive off", captured["interactive"] is False)
            case.check("workflow passes new draft flag", captured["new_draft"] is True)
            case.check(
                "workflow reports draft created",
                pushed["status"] == "draft_created",
            )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    case = ContractTest()
    run_review_case(case)
    run_push_contract(case)
    if case.failures:
        print(f"{len(case.failures)} workflow test(s) failed")
        return 1
    print("All workflow tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

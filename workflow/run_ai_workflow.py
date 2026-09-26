#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI workflow for generating, checking, rendering, and pushing a WeChat draft.

Task JSON fields:
    trigger, source, slug, title, brief, summary, audience, tone,
    keywords, requirements, author, source, tags, cover,
    content_file, content_markdown, diagram

Triggers are normalized into this task JSON, so a cron job, menu callback,
or fan-message adapter can all call the same command.
"""

import argparse
import json
import shutil
import sys
sys.dont_write_bytecode = True
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = Path(__file__).resolve().parent
QUALITY_DIR = ROOT / "quality"
PUBLISH_DIR = ROOT / "publish"
for path in (str(ROOT), str(WORKFLOW_DIR), str(QUALITY_DIR), str(PUBLISH_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from content_generator import generate_article  # noqa: E402
from cover_generator import generate_cover, generate_diagram  # noqa: E402
import check_article as quality  # noqa: E402
import wechat_push  # noqa: E402
from md_to_wechat import (  # noqa: E402
    build_preview,
    make_local_srcs_relative,
    render_footer,
    render_article,
)
from quality.new_article import create_article, safe_slug  # noqa: E402
from quality.stage_gate import confirm as gate_confirm  # noqa: E402


class WorkflowError(RuntimeError):
    pass


IMAGE_PLACEHOLDER = "![](images/ai-generated.png)"


def load_task(path):
    if path == "-":
        data = json.loads(sys.stdin.read())
    else:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkflowError("Task JSON must be an object.")
    return data


def normalize_task(task):
    normalized = dict(task)
    title = str(normalized.get("title", "")).strip()
    if not title:
        slug_hint = str(normalized.get("slug", "")).replace("-", " ").strip()
        title = slug_hint.title() if slug_hint else ""
    if not title:
        raise WorkflowError("Task requires title or slug.")

    slug = safe_slug(normalized.get("slug") or title)
    normalized["title"] = title
    normalized["slug"] = slug
    normalized["keywords"] = list(normalized.get("keywords", []))
    normalized["requirements"] = list(normalized.get("requirements", []))
    normalized["tags"] = list(normalized.get("tags", []))
    return normalized


def load_content(task):
    if task.get("content_markdown"):
        return str(task["content_markdown"]), {"generator": "inline-task"}
    if task.get("content_file"):
        path = Path(task["content_file"])
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise WorkflowError(f"content_file not found: {path}")
        return path.read_text(encoding="utf-8"), {
            "generator": "content-file",
            "path": str(path),
        }
    return generate_article(task)


def summary_from_content(content, fallback=""):
    for paragraph in content.splitlines():
        text = paragraph.strip()
        if not text or text.startswith("#") or text.startswith("![") or text.startswith(">"):
            continue
        return text[:120]
    return fallback or "AI generated article pending review."


def _insert_after_h1(content, insertion):
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(index + 1, "\n" + insertion)
            return "\n".join(lines).strip() + "\n"
    return insertion + "\n" + content


def prepare_article(task, content, force=False):
    result = create_article(
        slug=task["slug"],
        title=task["title"],
        summary=summary_from_content(content, task.get("summary", "")),
        author=task.get("author", ""),
        source=task.get("source", ""),
        cover="",
        tags=task.get("tags", []),
        force=force,
        # 全自动链路：task.json 就是确认单，直接确认 track/topic/config
        auto=True,
        track=task.get("track", ""),
    )
    article_file = result["article"]
    meta_file = result["meta"]
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    if task.get("diagram"):
        diagram = generate_diagram(
            task["diagram"].get("title", "AI workflow"),
            task["diagram"].get("items", []),
            slug=task["slug"],
        )
        relative = diagram.relative_to(ROOT).as_posix()
        if IMAGE_PLACEHOLDER in content:
            content = content.replace(IMAGE_PLACEHOLDER, f"![]({relative})")
        else:
            content = _insert_after_h1(content, f"![]({relative})")
        meta["diagram_image"] = relative

    if not content.lstrip().startswith("# "):
        content = f"# {task['title']}\n\n{content}"
    article_file.write_text(content, encoding="utf-8")

    if task.get("cover"):
        cover = task["cover"]
    else:
        cover_path = generate_cover(
            task["title"],
            task.get("summary") or task.get("brief", ""),
            slug=task["slug"],
        )
        cover = cover_path.relative_to(ROOT).as_posix()
    meta["cover"] = cover
    meta["summary"] = summary_from_content(content, task.get("summary", ""))
    meta_file.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        gate_confirm(result["slug"], "draft", value="workflow 生成初稿",
                     note="run_ai_workflow.py：正文与封面已落盘")
    except SystemExit:
        pass
    return {
        "article_file": article_file,
        "meta_file": meta_file,
        "cover": cover,
        "meta": meta,
        "content": content,
        "slug": result["slug"],
    }


def run_quality_gates(article_file, meta_file, skip_dedup=False):
    article_text = quality.read_text(article_file)
    meta = json.loads(quality.read_text(meta_file))
    ok = True
    warnings = []

    if not quality.asset_check(article_text, meta):
        ok = False
    if not quality.banned_words_check(
        article_text,
        meta,
        quality.load_banned_words(quality.BANNED_WORDS_DEFAULT),
    ):
        ok = False

    citations = quality.citations_check(article_text)
    if citations:
        warnings.append({"type": "citation", "paragraphs": citations})

    if not skip_dedup:
        files = quality.collect_source_files([str(ROOT / "references" / "private" / "archive")])
        if files and not quality.dedup_check(article_text, files, 13, 25.0):
            ok = False

    return {"ok": ok, "warnings": warnings}


def write_preview(article_file, meta):
    meta_data = json.loads(meta.read_text(encoding="utf-8"))
    content = render_article(article_file.read_text(encoding="utf-8"), {})
    content += "\n" + render_footer(meta_data)
    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_path = out_dir / f"{article_file.parent.name}.workflow.html"
    preview_path.write_text(
        build_preview(meta_data.get("title", "Workflow Preview"), make_local_srcs_relative(content, out_dir), []),
        encoding="utf-8",
    )
    return preview_path


def write_log(run_id, task, stages, status, result=None, error=None):
    log_dir = ROOT / "out" / "workflow-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_task = dict(task)
    safe_task.pop("content_markdown", None)
    record = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "task": safe_task,
        "stages": stages,
        "result": result or {},
        "error": error,
    }
    log_path = log_dir / f"{run_id}.json"
    log_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return log_path


def run_workflow(task, push=False, force=False, skip_dedup=False, dry_run=False, new_draft=False):
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + safe_slug(task.get("slug", "run"))
    stages = []
    try:
        task = normalize_task(task)
        stages.append({"stage": "receive_task", "status": "ok", "slug": task["slug"]})

        content, generation_meta = load_content(task)
        stages.append({"stage": "invoke_skill", "status": "ok", **generation_meta})

        prepared = prepare_article(task, content, force=force)
        stages.append(
            {
                "stage": "execute",
                "status": "ok",
                "article": str(prepared["article_file"]),
                "meta": str(prepared["meta_file"]),
                "cover": prepared["cover"],
            }
        )

        gates = run_quality_gates(
            prepared["article_file"],
            prepared["meta_file"],
            skip_dedup=skip_dedup,
        )
        if not gates["ok"]:
            raise WorkflowError("Quality gates failed; review the output above.")
        stages.append(
            {
                "stage": "quality_gates",
                "status": "ok",
                "warnings": gates["warnings"],
            }
        )

        preview_file = write_preview(prepared["article_file"], prepared["meta_file"])
        stages.append({"stage": "output_result", "status": "ok", "preview": str(preview_file)})

        if not push:
            status = "review_required"
            result = {
                "run_id": run_id,
                "status": status,
                "article_file": str(prepared["article_file"]),
                "meta_file": str(prepared["meta_file"]),
                "preview_file": str(preview_file),
                "warnings": gates["warnings"],
                "pushed": False,
            }
        else:
            push_result = wechat_push.push_draft(
                article=prepared["article_file"],
                meta=prepared["meta_file"],
                interactive=False,
                new_draft=new_draft,
                dry_run=dry_run,
            )
            if dry_run:
                status = "dry_run"
                result = {
                    "run_id": run_id,
                    "status": status,
                    "article_file": str(prepared["article_file"]),
                    "meta_file": str(prepared["meta_file"]),
                    "preview_file": str(push_result["preview_file"]),
                    "warnings": gates["warnings"],
                    "pushed": False,
                    "dry_run": True,
                }
            else:
                status = "draft_created"
                result = {
                    "run_id": run_id,
                    "status": status,
                    "article_file": str(prepared["article_file"]),
                    "meta_file": str(prepared["meta_file"]),
                    "preview_file": str(push_result["preview_file"]),
                    "warnings": gates["warnings"],
                    "pushed": True,
                    "draft_media_id": push_result["draft_media_id"],
                    "cover_media_id": push_result["cover_media_id"],
                }
            stages.append(
                {
                    "stage": "push_draft",
                    "status": "ok",
                    "dry_run": dry_run,
                    "draft_media_id": push_result.get("draft_media_id"),
                }
            )

        log_path = write_log(run_id, task, stages, status, result)
        result["log_file"] = str(log_path)
        print(f"Workflow status: {status}")
        print(f"Log: {log_path}")
        return result
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        log_path = write_log(run_id, task, stages, "failed", error=error)
        print(f"Workflow failed: {exc}")
        print(f"Log: {log_path}")
        raise


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the WeChat AI automation workflow")
    parser.add_argument("--task", help="Task JSON file, or - for stdin")
    parser.add_argument("--slug")
    parser.add_argument("--title")
    parser.add_argument("--brief")
    parser.add_argument("--cover")
    parser.add_argument("--push", action="store_true", help="Push the final draft to WeChat")
    parser.add_argument("--new-draft", action="store_true", help="Always create a new draft")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --push, render and validate the draft without calling the WeChat API.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing article scaffold")
    parser.add_argument("--skip-dedup", action="store_true")
    args = parser.parse_args()

    if not args.task and not (args.slug and args.title):
        parser.error("Use --task TASK.json, or provide --slug and --title.")
    task = load_task(args.task) if args.task else {}
    for key in ("slug", "title", "brief", "cover"):
        value = getattr(args, key)
        if value:
            task[key] = value
    run_workflow(
        task,
        push=args.push,
        force=args.force,
        skip_dedup=args.skip_dedup,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

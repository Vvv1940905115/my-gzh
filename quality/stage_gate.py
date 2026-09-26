#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段闸门：track -> topic -> config -> draft -> qa -> publish

把 SKILL.md 里「输出后强制挂起」这类语言约束换成脚本判定。
稿件由 quality/new_article.py 初始化时生成 articles/<slug>/state.json；
之后每个阶段启动前调用 require()，前置阶段未确认就 sys.exit(1) 阻断。

CLI:
    python quality/stage_gate.py init    --slug <slug> [--track "AI工具"] [--auto] [--force]
    python quality/stage_gate.py confirm --slug <slug> --stage track --value "AI工具" [--note "..."]
    python quality/stage_gate.py check   --slug <slug> --stage draft [--strict]
    python quality/stage_gate.py show    --slug <slug> [--json]
    python quality/stage_gate.py reset   --slug <slug> --stage qa
    python quality/stage_gate.py trend   # 选题阶段热点规则摘要

topic 阶段会强制打印 references/public/trend-tracking.md 的热点规则，
确保热点追踪真正参与选题，而不是躺在 references/ 里不生效。
"""

import argparse
import json
import sys
sys.dont_write_bytecode = True
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 热点追踪库：选题阶段（topic）必读。实际文件在 references/public/ 下，
# 这里同时兜底 references/trend-tracking.md，避免路径写法不一致导致规则失效。
TREND_TRACKING_CANDIDATES = (
    ROOT / "references" / "public" / "trend-tracking.md",
    ROOT / "references" / "trend-tracking.md",
)

GATE_VERSION = 1
STAGES = ("track", "topic", "config", "draft", "qa", "publish")
STAGE_LABEL = {
    "track": "赛道确认",
    "topic": "主题确认",
    "config": "选配确认",
    "draft": "初稿完成",
    "qa": "质检通过",
    "publish": "发布",
}
# 全自动链路（task.json / workflow）允许一次性确认的前置阶段
AUTO_STAGES = ("track", "topic", "config")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def trend_tracking_path():
    for path in TREND_TRACKING_CANDIDATES:
        if path.exists():
            return path
    return TREND_TRACKING_CANDIDATES[0]


def trend_brief():
    """选题阶段必读的热点规则摘要（渠道清单 + 融入规则 + 登记表格式）。"""
    path = trend_tracking_path()
    if not path.exists():
        return "热点追踪库缺失：%s（请先补齐 references/public/trend-tracking.md）" % (
            path.relative_to(ROOT).as_posix())
    text = path.read_bytes().decode("utf-8-sig", errors="replace")
    channels = []
    collecting = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## 渠道清单"):
            collecting = True
            continue
        if collecting:
            if stripped.startswith("## "):
                break
            if stripped.startswith("|") and "---" not in stripped:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if len(cells) >= 2 and cells[0] not in ("渠道",):
                    channels.append("%s（%s）" % (cells[0], cells[1]))
    lines = [
        "热点规则（%s）：" % path.relative_to(ROOT).as_posix(),
        "  1. 选题前先扫下方渠道，相关度 ≥4 星的热点优先级高于常青选题；",
        "  2. 热点必须融入选题角度与开头 100 字；无法核实的标「需核实」并带时间与出处；",
        "  3. 超过 7 天的热点只作背景素材，不作主选题。",
    ]
    if channels:
        lines.append("  渠道清单：%s" % "、".join(channels))
    lines.append("  确认时用 --note 登记热点事件与出处，未核实的热点不得进入正文。")
    return "\n".join(lines)


def _die(message):
    print(message, file=sys.stderr)
    print("GATE BLOCKED", file=sys.stderr)
    sys.exit(1)


def slug_of(article_path):
    """Article path -> slug: articles/<slug>/article.md（根目录遗留稿返回 'article'）。"""
    path = Path(article_path).resolve()
    parent = path.parent.name
    return parent or "article"


def state_path(slug, root=None):
    base = Path(root) if root is not None else ROOT
    return base / "articles" / slug / "state.json"


def load_state(slug, root=None):
    path = state_path(slug, root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_bytes().decode("utf-8-sig", errors="replace"))
    except (ValueError, OSError):
        return None


def save_state(slug, data, root=None):
    data = dict(data)
    data["updated_at"] = _now()
    path = state_path(slug, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def _blank_stages():
    return {
        stage: {"confirmed": False, "value": None, "at": None, "note": None}
        for stage in STAGES
    }


def init_state(slug, track=None, auto=False, note=None, root=None, force=False):
    """初始化 state.json。已存在且 force=False 时保留现有进度。"""
    existing = load_state(slug, root)
    if existing and not force:
        return existing, False

    data = {
        "version": GATE_VERSION,
        "slug": slug,
        "created_at": _now(),
        "updated_at": _now(),
        "stage": "track",
        "mode": "auto" if auto else "manual",
        "stages": _blank_stages(),
        "rewrites": 0,
        "history": [{"stage": "track", "action": "init", "at": _now(), "note": note}],
    }
    if track is not None:
        data["stages"]["track"]["value"] = track
    if auto:
        for stage in AUTO_STAGES:
            data["stages"][stage] = {
                "confirmed": True,
                "value": track if stage == "track" else "由上游任务参数提供",
                "at": _now(),
                "note": note or "auto: 上游已提供完整参数，无需人工挂起",
            }
        data["stage"] = "draft"
    return save_state(slug, data, root), True


def pending_before(state, stage):
    """进入 stage 前仍未确认的前置阶段列表。"""
    index = STAGES.index(stage)
    return [s for s in STAGES[:index] if not state["stages"].get(s, {}).get("confirmed")]


def require(slug, stage, strict=False, root=None, quiet=False):
    """阶段准入校验。前置阶段未确认则 exit(1)。

    strict=False（默认）：无 state.json 时只 WARN 放行，兼容 workflow 与遗留稿件。
    strict=True：无 state.json 也阻断。
    """
    if stage not in STAGES:
        raise ValueError("unknown stage: %s" % stage)
    state = load_state(slug, root)
    if state is None:
        message = "未找到 articles/%s/state.json" % slug
        if strict:
            _die(
                "GATE BLOCKED: %s。\n"
                "  稿件必须先由 quality/new_article.py 初始化；--gate strict 不允许无状态稿件。"
                % message
            )
        if not quiet:
            print("GATE WARN: %s，跳过闸门校验（遗留稿件）。需要强约束时加 --gate strict。" % message)
        return None
    pending = pending_before(state, stage)
    if pending:
        labels = "、".join("%s(%s)" % (STAGE_LABEL[s], s) for s in pending)
        _die(
            "GATE BLOCKED: 进入「%s(%s)」前，以下阶段尚未确认：%s\n"
            "  逐个确认：python quality/stage_gate.py confirm --slug %s --stage %s --value \"...\"\n"
            "  查看进度：python quality/stage_gate.py show --slug %s"
            % (STAGE_LABEL[stage], stage, labels, slug, pending[0], slug)
        )
    if not quiet:
        print("GATE PASS: %s 允许进入 %s(%s)" % (slug, STAGE_LABEL[stage], stage))
    return state


def confirm(slug, stage, value=None, note=None, root=None):
    """确认某一阶段；前置未确认时阻断。"""
    if stage not in STAGES:
        raise ValueError("unknown stage: %s" % stage)
    state = load_state(slug, root)
    if state is None:
        _die(
            "GATE BLOCKED: 稿件 %s 无 state.json，无法确认阶段。\n"
            "  先运行：python quality/new_article.py --slug %s --title \"...\""
            % (slug, slug)
        )
    pending = pending_before(state, stage)
    if pending:
        labels = "、".join("%s(%s)" % (STAGE_LABEL[s], s) for s in pending)
        _die("GATE BLOCKED: 确认「%s」前必须先确认：%s" % (STAGE_LABEL[stage], labels))
    entry = state["stages"].setdefault(stage, {"confirmed": False, "value": None, "at": None, "note": None})
    entry["confirmed"] = True
    if value is not None:
        entry["value"] = value
    entry["at"] = _now()
    if note:
        entry["note"] = note
    index = STAGES.index(stage)
    if index + 1 < len(STAGES):
        state["stage"] = STAGES[index + 1]
    state.setdefault("history", []).append(
        {"stage": stage, "action": "confirm", "value": entry["value"], "at": entry["at"], "note": note}
    )
    return save_state(slug, state, root)


def reset_from(slug, stage, root=None):
    """把该阶段及其之后全部置为未确认（改稿、参数变更后重新走闸门）。"""
    if stage not in STAGES:
        raise ValueError("unknown stage: %s" % stage)
    state = load_state(slug, root)
    if state is None:
        _die("GATE BLOCKED: 稿件 %s 无 state.json，无法重置阶段。" % slug)
    index = STAGES.index(stage)
    for name in STAGES[index:]:
        entry = state["stages"].setdefault(name, {"confirmed": False, "value": None, "at": None, "note": None})
        entry["confirmed"] = False
        entry["at"] = None
    state["stage"] = stage
    state.setdefault("history", []).append({"stage": stage, "action": "reset", "at": _now(), "note": None})
    return save_state(slug, state, root)


def render(state):
    lines = []
    if state is None:
        return "无 state.json"
    lines.append("稿件: %s    当前阶段: %s(%s)    模式: %s" % (
        state.get("slug"), STAGE_LABEL.get(state.get("stage"), state.get("stage")),
        state.get("stage"), state.get("mode", "manual")))
    lines.append("重写轮次: %s" % state.get("rewrites", 0))
    lines.append("")
    for stage in STAGES:
        entry = state.get("stages", {}).get(stage, {})
        mark = "[x]" if entry.get("confirmed") else "[ ]"
        value = entry.get("value")
        value = "-" if value in (None, "") else value
        at = entry.get("at") or "-"
        lines.append("%s %-14s %-8s value=%s  at=%s" % (mark, STAGE_LABEL[stage], stage, value, at))
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="阶段闸门：track -> topic -> config -> draft -> qa -> publish")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化 state.json")
    p_init.add_argument("--slug", required=True)
    p_init.add_argument("--track", default=None, help="赛道名称（仅登记，不自动确认）")
    p_init.add_argument("--auto", action="store_true", help="全自动链路：直接确认 track/topic/config")
    p_init.add_argument("--note", default=None)
    p_init.add_argument("--force", action="store_true")

    p_confirm = sub.add_parser("confirm", help="确认某一阶段")
    p_confirm.add_argument("--slug", required=True)
    p_confirm.add_argument("--stage", required=True, choices=STAGES)
    p_confirm.add_argument("--value", default=None)
    p_confirm.add_argument("--note", default=None)

    p_check = sub.add_parser("check", help="校验能否进入某一阶段（不通过 exit 1）")
    p_check.add_argument("--slug", required=True)
    p_check.add_argument("--stage", required=True, choices=STAGES)
    p_check.add_argument("--strict", action="store_true", help="无 state.json 也阻断")
    p_check.add_argument("--quiet", action="store_true")

    p_show = sub.add_parser("show", help="查看阶段进度")
    p_show.add_argument("--slug", required=True)
    p_show.add_argument("--json", action="store_true")

    p_reset = sub.add_parser("reset", help="重置某阶段及其之后为未确认")
    p_reset.add_argument("--slug", required=True)
    p_reset.add_argument("--stage", required=True, choices=STAGES)

    sub.add_parser("trend", help="打印选题阶段热点规则摘要（references/public/trend-tracking.md）")

    args = parser.parse_args()

    if args.cmd == "init":
        state, created = init_state(args.slug, track=args.track, auto=args.auto,
                                    note=args.note, force=args.force)
        if created:
            print("已初始化: articles/%s/state.json" % args.slug)
        else:
            print("state.json 已存在，保留现有进度（--force 可重置）: articles/%s/state.json" % args.slug)
        print(render(state))
        return

    if args.cmd == "confirm":
        state = confirm(args.slug, args.stage, value=args.value, note=args.note)
        print("已确认: %s(%s)" % (STAGE_LABEL[args.stage], args.stage))
        if args.stage == "topic":
            print(trend_brief())
        print(render(state))
        return

    if args.cmd == "check":
        require(args.slug, args.stage, strict=args.strict, quiet=args.quiet)
        if args.stage == "topic":
            print(trend_brief())
        return

    if args.cmd == "trend":
        print(trend_brief())
        return

    if args.cmd == "show":
        state = load_state(args.slug)
        if args.json:
            print(json.dumps(state, ensure_ascii=False, indent=2) if state else "{}")
        else:
            print(render(state))
        sys.exit(0 if state else 1)

    if args.cmd == "reset":
        state = reset_from(args.slug, args.stage)
        print("已重置: %s 及其之后阶段" % STAGE_LABEL[args.stage])
        print(render(state))


if __name__ == "__main__":
    main()

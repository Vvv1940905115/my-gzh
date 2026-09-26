#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""质检报告：硬指标脚本判定 + 软指标模型评分留痕，落盘 articles/<slug>/qa-report.md

设计原则「SKILL 管流程，脚本管判定」的具体实现：
- 硬指标（查重 / 违禁词 / 配图资产）由 quality/check_article.py 判定，模型不得填写。
- 软指标（事实准确 / 风格规范 / 去 AI 感）由模型评分，但必须逐条给出扣分明细；
  声明分数与明细不一致、或扣分理由过短，脚本直接拒绝落盘，防止自评虚高。

CLI:
    python quality/qa_report.py init  --article articles/<slug>/article.md
    python quality/qa_report.py apply --slug <slug> --scores <soft.json>
    python quality/qa_report.py show  --slug <slug>

soft.json 格式:
{
  "dimensions": [
    {"name": "事实准确", "score": 88, "deductions": [
      {"item": "数据可核实来源", "full": 40, "got": 36, "reason": "第 2 节两处数据缺来源链接，已标注需核实"}
    ]}
  ],
  "note": "可选说明"
}
"""

import argparse
import contextlib
import io
import json
import sys
sys.dont_write_bytecode = True
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_QUALITY_DIR = Path(__file__).resolve().parent
if str(_QUALITY_DIR) not in sys.path:
    sys.path.insert(0, str(_QUALITY_DIR))

import check_article as ca  # noqa: E402
from lib.common import default_meta_for  # noqa: E402
from stage_gate import confirm as gate_confirm  # noqa: E402
from stage_gate import init_state, load_state, save_state  # noqa: E402
from stage_gate import require as gate_require  # noqa: E402

PASS_THRESHOLD = 85.0
MAX_REWRITE_ROUNDS = 2
HARD_WEIGHT = 0.20
SOFT_WEIGHT = 0.80
SOFT_DIMENSIONS = ("事实准确", "风格规范", "去AI感")
DIMENSION_WEIGHT = {"事实准确": 0.30, "风格规范": 0.30, "去AI感": 0.20, "硬指标": 0.20}
MIN_REASON_LEN = 10


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _capture(fn, *args, **kwargs):
    """Run a check_article function and capture its stdout."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - 报告里要暴露脚本异常
            return None, buf.getvalue().strip(), str(exc)
    return result, buf.getvalue().strip(), None


def _status(value, output, skip_marker=None, warn_marker=None, fail_marker=None):
    if skip_marker and skip_marker in output:
        return "SKIP"
    if fail_marker and fail_marker in output:
        return "FAIL"
    if warn_marker and warn_marker in output:
        return "WARN"
    return "PASS" if value else "FAIL"


def _summary_line(output, *markers):
    lines = [line.strip() for line in output.splitlines() if any(m in line for m in markers)]
    return " / ".join(lines[-2:]) if lines else "-"


def run_hard(article_path, meta_path=None, sources=None, banned_words=None,
             run_limit=None, rate_limit=None, skip_dedup=False, skip_banned=False,
             skip_images=False):
    """Run the deterministic checks and return a structured report."""
    article_text = ca.read_text(article_path)
    meta = None
    if meta_path and Path(meta_path).exists():
        meta = json.loads(ca.read_text(meta_path))

    items = []

    if not skip_images:
        ok, output, err = _capture(ca.asset_check, article_text, meta)
        status = _status(ok, output, fail_marker="图片资产: FAIL")
        items.append({
            "name": "配图资产", "full": 20, "got": 20 if status != "FAIL" else 0,
            "status": status, "output": output, "error": err,
            "note": _summary_line(output, "图片资产:", "缺失:"),
        })
    else:
        items.append({
            "name": "配图资产", "full": 20, "got": 0, "status": "SKIPPED",
            "output": "已用 --skip-images 跳过，未校验", "error": None, "note": "未校验",
        })

    if not skip_banned:
        path = ca.resolve_path(banned_words) if banned_words else ca.BANNED_WORDS_DEFAULT
        words = ca.load_banned_words(path)
        ok, output, err = _capture(ca.banned_words_check, article_text, meta, words)
        status = _status(ok, output, skip_marker="违禁词表不存在", warn_marker="违禁词: WARN",
                         fail_marker="违禁词: FAIL")
        items.append({
            "name": "违禁词", "full": 40, "got": 40 if status != "FAIL" else 0,
            "status": status, "output": output, "error": err,
            "note": _summary_line(output, "违禁词:", "命中"),
        })

    _, output, err = _capture(ca.citations_check, article_text)
    citation_warnings = ca.citation_warnings(article_text)
    citation_state = {
        "status": "WARN" if citation_warnings else "PASS",
        "count": len(citation_warnings),
        "output": output,
        "error": err,
    }

    if not skip_dedup:
        entries = sources or [str(ROOT / "references" / "private" / "archive")]
        files = ca.collect_source_files(entries)
        if files:
            ok, output, err = _capture(
                ca.dedup_check, article_text, files,
                run_limit or ca.RUN_LIMIT_DEFAULT, rate_limit or ca.RATE_LIMIT_DEFAULT,
            )
            status = _status(ok, output)
        else:
            ok, output, err = True, "查重来源: 无可用文件，跳过查重（不是失败）", None
            status = "SKIP"
        items.append({
            "name": "查重", "full": 40, "got": 40 if status != "FAIL" else 0,
            "status": status, "output": output, "error": err,
            "note": _summary_line(output, "重复率", "最长连续重复", "来源"),
        })

    skipped = [i["name"] for i in items if i["status"] in ("SKIPPED", "SKIP")]
    full_total = sum(i["full"] for i in items if i["status"] != "SKIPPED")
    got_total = sum(i["got"] for i in items if i["status"] != "SKIPPED")
    hard_score = round(got_total / full_total * 100, 1) if full_total else 0.0
    hard_pass = all(i["status"] != "FAIL" for i in items)
    return {
        "items": items,
        "full_total": full_total,
        "got_total": got_total,
        "score": hard_score,
        "pass": hard_pass,
        "skipped": skipped,
        "citations": citation_state,
        "sources": sources or ["references/private/archive"],
    }


def validate_soft(payload):
    """Validate the model's soft scores. Returns (normalized, errors)."""
    errors = []
    if not isinstance(payload, dict):
        return None, ["soft.json 根节点必须是对象"]
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        return None, ["soft.json 缺少 dimensions 数组"]

    names = [d.get("name") for d in dimensions if isinstance(d, dict)]
    missing = [n for n in SOFT_DIMENSIONS if n not in names]
    extra = [n for n in names if n not in SOFT_DIMENSIONS]
    if missing:
        errors.append("缺少软指标维度: %s" % "、".join(missing))
    if extra:
        errors.append("出现未知维度（硬指标由脚本判定，不接受模型填写）: %s" % "、".join(str(e) for e in extra))
    if len(set(names)) != len(names):
        errors.append("维度重复提交：%s" % "、".join(str(n) for n in names))

    normalized = []
    for dim in dimensions:
        if not isinstance(dim, dict):
            errors.append("维度条目必须是对象")
            continue
        name = dim.get("name")
        score = dim.get("score")
        deductions = dim.get("deductions")
        if name not in SOFT_DIMENSIONS:
            continue
        if not isinstance(score, (int, float)) or not 0 <= score <= 100:
            errors.append("维度「%s」的 score 必须是 0-100 的数字" % name)
            continue
        if not isinstance(deductions, list) or not deductions:
            errors.append("维度「%s」必须给出至少 1 条扣分明细（deductions）" % name)
            continue
        full_sum = 0.0
        got_sum = 0.0
        rows = []
        for index, item in enumerate(deductions, 1):
            if not isinstance(item, dict):
                errors.append("维度「%s」第 %d 条明细必须是对象" % (name, index))
                continue
            label = str(item.get("item", "")).strip()
            reason = str(item.get("reason", "")).strip()
            full = item.get("full")
            got = item.get("got")
            if not label:
                errors.append("维度「%s」第 %d 条明细缺少 item 名称" % (name, index))
            if not isinstance(full, (int, float)) or full <= 0:
                errors.append("维度「%s」第 %d 条明细的 full 必须为正数" % (name, index))
                continue
            if not isinstance(got, (int, float)) or not 0 <= got <= full:
                errors.append("维度「%s」第 %d 条明细的 got 必须落在 0-%s 之间" % (name, index, full))
                continue
            if len(reason) < MIN_REASON_LEN:
                errors.append(
                    "维度「%s」第 %d 条明细的扣分理由不足 %d 字（当前 %d 字），必须写清凭什么扣分"
                    % (name, index, MIN_REASON_LEN, len(reason))
                )
            full_sum += float(full)
            got_sum += float(got)
            rows.append({"item": label, "full": full, "got": got, "reason": reason})
        if not full_sum:
            errors.append("维度「%s」的明细满分合计为 0" % name)
            continue
        expected = round(got_sum / full_sum * 100, 1)
        if abs(float(score) - expected) > 0.5:
            errors.append(
                "维度「%s」声明 %s 分，但扣分明细合计为 %.1f 分（%s/%s），两者不一致"
                % (name, score, expected, _fmt_num(got_sum), _fmt_num(full_sum))
            )
        normalized.append({
            "name": name,
            "score": float(score),
            "weight": DIMENSION_WEIGHT[name],
            "deductions": rows,
            "full_sum": full_sum,
            "got_sum": got_sum,
        })

    if errors:
        return None, errors
    normalized.sort(key=lambda d: SOFT_DIMENSIONS.index(d["name"]))
    return {"dimensions": normalized, "note": str(payload.get("note", "")).strip()}, []


def _fmt_num(value):
    return str(int(value)) if float(value).is_integer() else ("%.1f" % value)


def compute(hard, soft):
    total = hard["score"] * HARD_WEIGHT
    rows = [{"name": "硬指标", "weight": HARD_WEIGHT, "score": hard["score"],
             "weighted": round(hard["score"] * HARD_WEIGHT, 1)}]
    for dim in soft["dimensions"]:
        weighted = round(dim["score"] * dim["weight"], 1)
        total += weighted
        rows.append({"name": dim["name"], "weight": dim["weight"],
                     "score": dim["score"], "weighted": weighted})
    return round(total, 1), rows


def decide(hard, total, rewrites):
    if not hard["pass"]:
        return "HARD_FAIL"
    if total >= PASS_THRESHOLD:
        return "PASS"
    if rewrites >= MAX_REWRITE_ROUNDS:
        return "NEEDS_HUMAN"
    return "NEEDS_REWRITE"


STATUS_TEXT = {
    "PASS": "PASS：可进入 publish 阶段",
    "NEEDS_REWRITE": "NEEDS_REWRITE：总分低于 85，只重写扣分段落，重写后重新 init/apply",
    "NEEDS_HUMAN": "NEEDS_HUMAN：已重写 %d 轮仍不达标，输出当前最优版本并转人工介入" % MAX_REWRITE_ROUNDS,
    "HARD_FAIL": "HARD_FAIL：硬指标未通过，任何情况下都不得发布",
}


def render_report(slug, article_rel, hard, soft, total, rows, status, rewrites):
    lines = []
    lines.append("# 质检报告：%s" % slug)
    lines.append("")
    lines.append("- 稿件：`%s`" % article_rel)
    lines.append("- 生成时间：%s" % _now())
    lines.append("- 状态：**%s**" % status)
    if soft:
        lines.append("- 总分：**%s / 100**（阈值 %s）" % (total, int(PASS_THRESHOLD)))
    else:
        lines.append("- 总分：待填写（软指标 PENDING）")
    lines.append("- 硬指标：%s（脚本判定 `quality/check_article.py`，模型不得填写）"
                 % ("PASS" if hard["pass"] else "FAIL"))
    lines.append("- 重写轮次：%d / %d" % (rewrites, MAX_REWRITE_ROUNDS))
    if hard.get("skipped"):
        lines.append("- 未校验项：**%s**（未计入硬指标分数，发布前必须补齐来源或人工确认，不得视为已通过）"
                     % "、".join(hard["skipped"]))
    lines.append("")
    lines.append("## 一、硬指标（脚本判定）")
    lines.append("")
    lines.append("| 项目 | 满分 | 实得 | 判定 | 说明 |")
    lines.append("|---|---|---|---|---|")
    for item in hard["items"]:
        lines.append("| %s | %s | %s | %s | %s |" % (
            item["name"], item["full"], item["got"], item["status"], item["note"]))
    lines.append("| 合计 | %s | %s | %s | 加权 %s |" % (
        hard["full_total"], hard["got_total"],
        "PASS" if hard["pass"] else "FAIL",
        round(hard["score"] * HARD_WEIGHT, 1)))
    lines.append("")
    citations = hard["citations"]
    lines.append("引用来源：%s（%d 个数据段落缺来源标记，需人工补充或确认，不得当作已通过事实核查）"
                 % (citations["status"], citations["count"]))
    lines.append("")
    for item in hard["items"]:
        lines.append("<details>")
        lines.append("<summary>%s 原始输出（check_article.py）</summary>" % item["name"])
        lines.append("")
        lines.append("```text")
        lines.append(item["output"] or "(无输出)")
        if item["error"]:
            lines.append("脚本异常: %s" % item["error"])
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("## 二、软指标（模型评分，逐条留痕）")
    lines.append("")
    if not soft:
        lines.append("PENDING：模型尚未提交评分。运行：")
        lines.append("")
        lines.append("```text")
        lines.append("python quality/qa_report.py apply --slug %s --scores <soft.json>" % slug)
        lines.append("```")
        lines.append("")
        for name in SOFT_DIMENSIONS:
            lines.append("- %s（权重 %d%%）：待评分" % (name, int(DIMENSION_WEIGHT[name] * 100)))
        lines.append("")
        return "\n".join(lines) + "\n"

    for dim in soft["dimensions"]:
        lines.append("### %s（权重 %d%%，得分 %s）" % (
            dim["name"], int(dim["weight"] * 100), _fmt_num(dim["score"])))
        lines.append("")
        lines.append("| 扣分项 | 满分 | 实得 | 扣分理由 |")
        lines.append("|---|---|---|---|")
        for row in dim["deductions"]:
            lines.append("| %s | %s | %s | %s |" % (
                row["item"], _fmt_num(row["full"]), _fmt_num(row["got"]),
                row["reason"].replace("|", "/")))
        lines.append("")
        lines.append("小计 %s/%s → %s 分" % (
            _fmt_num(dim["got_sum"]), _fmt_num(dim["full_sum"]), _fmt_num(dim["score"])))
        lines.append("")
    if soft.get("note"):
        lines.append("模型说明：%s" % soft["note"])
        lines.append("")

    lines.append("## 三、总分")
    lines.append("")
    lines.append("| 维度 | 权重 | 得分 | 加权 |")
    lines.append("|---|---|---|---|")
    for row in rows:
        lines.append("| %s | %d%% | %s | %s |" % (
            row["name"], int(row["weight"] * 100), _fmt_num(row["score"]), _fmt_num(row["weighted"])))
    lines.append("| **总分** | | | **%s** |" % _fmt_num(total))
    lines.append("")
    lines.append("## 四、结论")
    lines.append("")
    lines.append("- %s" % STATUS_TEXT.get(status, status))
    if status == "NEEDS_REWRITE":
        lines.append("- 只重写扣分最多的段落，保留其余内容；重写后重新运行 init 与 apply。")
    if status == "NEEDS_HUMAN":
        lines.append("- 已输出当前最优版本，需人工介入处理卡住的段落。")
    if status == "HARD_FAIL":
        lines.append("- 硬指标 FAIL 项：%s" % "、".join(
            i["name"] for i in hard["items"] if i["status"] == "FAIL"))
    lines.append("")
    return "\n".join(lines) + "\n"


def report_path(slug):
    return ROOT / "articles" / slug / "qa-report.md"


def current_rewrites(slug):
    state = load_state(slug)
    return int(state.get("rewrites", 0)) if state else 0


def bump_rewrites(slug):
    state = load_state(slug)
    if state is None:
        state, _ = init_state(slug)
        state = load_state(slug)
    state["rewrites"] = int(state.get("rewrites", 0)) + 1
    save_state(slug, state)
    return state["rewrites"]


def _add_check_args(parser):
    parser.add_argument("--meta", default=None)
    parser.add_argument("--sources", action="append", default=None)
    parser.add_argument("--banned-words", default=None)
    parser.add_argument("--run-limit", type=int, default=None)
    parser.add_argument("--rate-limit", type=float, default=None)
    parser.add_argument("--skip-dedup", action="store_true")
    parser.add_argument("--skip-banned", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--gate", choices=("auto", "strict", "off"), default="auto")


def _resolve_article(article, slug=None):
    if article:
        return ca.resolve_path(article)
    if slug:
        return ROOT / "articles" / slug / "article.md"
    raise SystemExit("需要 --article 或 --slug")


def _slug_from(article_path, slug=None):
    if slug:
        return slug
    return Path(article_path).resolve().parent.name or "article"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="质检报告：硬指标脚本判定 + 软指标留痕落盘")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="跑硬指标并生成 qa-report.md 骨架")
    p_init.add_argument("--article", required=True)
    p_init.add_argument("--slug", default=None)
    _add_check_args(p_init)

    p_apply = sub.add_parser("apply", help="合并模型软指标评分，校验通过后落盘")
    p_apply.add_argument("--slug", required=True)
    p_apply.add_argument("--scores", required=True, help="模型软指标评分 JSON 文件")
    p_apply.add_argument("--article", default=None)
    _add_check_args(p_apply)

    p_show = sub.add_parser("show", help="打印 qa-report.md")
    p_show.add_argument("--slug", required=True)

    args = parser.parse_args()

    if args.cmd == "show":
        path = report_path(args.slug)
        if not path.exists():
            print("尚未生成质检报告: %s" % path.relative_to(ROOT).as_posix())
            return 1
        print(path.read_text(encoding="utf-8"))
        return 0

    article_path = _resolve_article(getattr(args, "article", None), getattr(args, "slug", None))
    if not article_path.exists():
        print("Article file not found: %s" % article_path, file=sys.stderr)
        return 1
    slug = _slug_from(article_path, getattr(args, "slug", None))
    meta_path = ca.resolve_path(args.meta) if args.meta else default_meta_for(article_path)

    if args.gate != "off":
        gate_require(slug, "qa", strict=(args.gate == "strict"))

    hard = run_hard(
        article_path,
        meta_path=meta_path,
        sources=args.sources,
        banned_words=args.banned_words,
        run_limit=args.run_limit,
        rate_limit=args.rate_limit,
        skip_dedup=args.skip_dedup,
        skip_banned=args.skip_banned,
        skip_images=args.skip_images,
    )
    rewrites = current_rewrites(slug)

    if args.cmd == "init":
        text = render_report(slug, article_path.relative_to(ROOT).as_posix(),
                             hard, None, 0.0, [], "PENDING", rewrites)
        path = report_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print("硬指标: %s（%s/%s 分）" % ("PASS" if hard["pass"] else "FAIL",
                                          hard["got_total"], hard["full_total"]))
        for item in hard["items"]:
            print("  %-8s %-5s %s" % (item["name"], item["status"], item["note"]))
        print("已生成骨架: %s" % path.relative_to(ROOT).as_posix())
        print("下一步：模型按 references/public/quality-score.md 逐条打分后运行")
        print("        python quality/qa_report.py apply --slug %s --scores <soft.json>" % slug)
        return 0 if hard["pass"] else 1

    # apply
    scores_path = Path(args.scores)
    if not scores_path.exists():
        print("soft.json 不存在: %s" % scores_path, file=sys.stderr)
        return 1
    try:
        payload = json.loads(scores_path.read_bytes().decode("utf-8-sig", errors="replace"))
    except ValueError as exc:
        print("soft.json 解析失败: %s" % exc, file=sys.stderr)
        return 1

    soft, errors = validate_soft(payload)
    if errors:
        print("软指标评分被拒绝（未落盘）：", file=sys.stderr)
        for err in errors:
            print("  - %s" % err, file=sys.stderr)
        return 1

    total, rows = compute(hard, soft)
    status = decide(hard, total, rewrites)
    if status == "NEEDS_REWRITE":
        rewrites = bump_rewrites(slug)

    text = render_report(slug, article_path.relative_to(ROOT).as_posix(),
                         hard, soft, total, rows, status, rewrites)
    path = report_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

    print("硬指标: %s（%s 分）" % ("PASS" if hard["pass"] else "FAIL", hard["score"]))
    print("软指标: %s" % " / ".join(
        "%s %s" % (d["name"], _fmt_num(d["score"])) for d in soft["dimensions"]))
    print("总分: %s / 100（阈值 %s）" % (total, int(PASS_THRESHOLD)))
    print("状态: %s" % status)
    print("报告: %s" % path.relative_to(ROOT).as_posix())

    if status == "PASS":
        try:
            gate_confirm(slug, "qa", value="%s 分（%s）" % (total, path.name),
                         note="qa-report.md 已落盘，硬指标 PASS")
            print("阶段闸门: qa 已确认，可进入 publish")
        except SystemExit:
            print("阶段闸门: qa 未能确认（前置阶段未完成），报告已落盘，请先补齐前置阶段", file=sys.stderr)
            return 1
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Regression tests for the stage gate and the two-track QA report.

覆盖：
- state.json 初始化、顺序确认、跳序阻断、重置
- 全自动链路（--auto）直接确认 track/topic/config
- 软指标评分校验：缺维度、多报硬指标、理由过短、分数与明细不一致
- 总分计算、状态判定、报告渲染与热点规则引用
"""

import importlib.util
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "quality"))


def load_module(name, relative):
    path = PROJECT_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_module("test_stage_gate", "quality/stage_gate.py")
qa = load_module("test_qa_report", "quality/qa_report.py")


class GateTest:
    def __init__(self):
        self.failures = []

    def check(self, name, condition, detail=""):
        if condition:
            print(f"PASS {name}")
        else:
            suffix = f": {detail}" if detail else ""
            print(f"FAIL {name}{suffix}")
            self.failures.append(name)

    def blocks(self, name, fn):
        """Assert that fn raises SystemExit (gate blocked)."""
        try:
            fn()
        except SystemExit as exc:
            self.check(name, exc.code not in (0, None), "exit code %s" % exc.code)
            return
        self.check(name, False, "未阻断")


def soft_payload(score_override=None, reason="第 2 节两处数据缺少可核实链接，已在正文标注需核实"):
    dims = [
        {"name": "事实准确", "score": 94, "deductions": [
            {"item": "数据可核实来源", "full": 40, "got": 36, "reason": reason},
            {"item": "案例与来源一致", "full": 30, "got": 30, "reason": "三个案例与来源一致，未发现编造"},
            {"item": "无法核实已标注", "full": 30, "got": 28, "reason": "一处版本号未标注截止时间"},
        ]},
        {"name": "风格规范", "score": 88, "deductions": [
            {"item": "选题价值", "full": 15, "got": 14, "reason": "痛点明确但转发理由略弱"},
            {"item": "标题点击欲", "full": 15, "got": 13, "reason": "标题达标但缺少具体利益数字"},
            {"item": "开头钩子", "full": 10, "got": 9, "reason": "反常识结论出现位置偏晚"},
            {"item": "信息密度", "full": 20, "got": 17, "reason": "第三节存在两段解释性注水内容"},
            {"item": "可执行性", "full": 10, "got": 9, "reason": "步骤完整但缺预期结果说明"},
            {"item": "情绪共鸣", "full": 15, "got": 13, "reason": "共鸣句只有一处且位置靠后"},
            {"item": "排版易读", "full": 10, "got": 9, "reason": "有一段超过四行，移动端偏重"},
            {"item": "配图相关度", "full": 5, "got": 4, "reason": "有一张图与当前段落关联偏弱"},
        ]},
        {"name": "去AI感", "score": 90, "deductions": [
            {"item": "套话开头", "full": 40, "got": 36, "reason": "结尾有一句总结性套话待改写"},
            {"item": "口语频次", "full": 30, "got": 27, "reason": "第四节对话感略密集，需收敛"},
            {"item": "句长变化", "full": 15, "got": 13, "reason": "中段三段长度接近，节奏单一"},
            {"item": "真人通读", "full": 15, "got": 14, "reason": "有一处书面化表达需口语化"},
        ]},
    ]
    if score_override is not None:
        dims[0]["score"] = score_override
    return {"dimensions": dims}


def run_gate_tests(case):
    with tempfile.TemporaryDirectory(prefix="gate-") as tmp:
        root = Path(tmp)
        state, created = gate.init_state("demo", track="AI工具", root=root)
        case.check("init creates state.json", (root / "articles" / "demo" / "state.json").exists())
        case.check("init reports created", created is True)
        case.check("init stage is track", state["stage"] == "track")
        case.check("no stage confirmed yet",
                   not any(s["confirmed"] for s in state["stages"].values()))

        case.check("require track passes without prereqs",
                   gate.require("demo", "track", root=root, quiet=True) is not None)
        case.blocks("require draft blocked before confirm",
                    lambda: gate.require("demo", "draft", root=root, quiet=True))
        case.blocks("confirm topic blocked before track",
                    lambda: gate.confirm("demo", "topic", value="x", root=root))
        case.blocks("require strict blocked without state.json",
                    lambda: gate.require("missing", "qa", strict=True, root=root, quiet=True))
        case.check("require auto passes without state.json",
                   gate.require("missing", "qa", strict=False, root=root, quiet=True) is None)

        for stage, value in (("track", "AI工具"), ("topic", "主题A"), ("config", "1500字"), ("draft", "初稿")):
            gate.confirm("demo", stage, value=value, root=root)
        case.check("require qa passes after confirmations",
                   gate.require("demo", "qa", root=root, quiet=True) is not None)
        case.blocks("require publish blocked before qa",
                    lambda: gate.require("demo", "publish", root=root, quiet=True))

        gate.reset_from("demo", "qa", root=root)
        state = gate.load_state("demo", root=root)
        case.check("reset keeps draft confirmed", state["stages"]["draft"]["confirmed"] is True)
        case.blocks("qa blocked again after reset",
                    lambda: gate.require("demo", "publish", root=root, quiet=True))

        auto_state, _ = gate.init_state("auto-demo", track="AI工具", auto=True, root=root)
        case.check("auto confirms first three stages",
                   all(auto_state["stages"][s]["confirmed"] for s in ("track", "topic", "config")))
        case.check("auto stage advances to draft", auto_state["stage"] == "draft")
        case.check("auto keeps qa unconfirmed", auto_state["stages"]["qa"]["confirmed"] is False)

        existing, created_again = gate.init_state("demo", root=root)
        case.check("init keeps progress when state exists", created_again is False)

        brief = gate.trend_brief()
        case.check("trend brief references trend-tracking.md", "trend-tracking.md" in brief, brief[:60])
        case.check("trend brief lists channels", "微信搜一搜" in brief, brief[:120])


def run_qa_tests(case):
    soft, errors = qa.validate_soft(soft_payload())
    case.check("valid soft scores accepted", soft is not None and not errors, str(errors))
    total, rows = qa.compute({"score": 100.0}, soft)
    expected = round(94 * 0.3 + 88 * 0.3 + 90 * 0.2 + 100 * 0.2, 1)
    case.check("total score matches weights", total == expected, "%s != %s" % (total, expected))
    case.check("rows cover four dimensions", len(rows) == 4)

    _, errors = qa.validate_soft(soft_payload(score_override=99))
    case.check("score/detail mismatch rejected", any("不一致" in e for e in errors), str(errors))

    _, errors = qa.validate_soft(soft_payload(reason="有点问题"))
    case.check("short reason rejected", any("扣分理由" in e for e in errors), str(errors))

    _, errors = qa.validate_soft({"dimensions": [soft_payload()["dimensions"][0]]})
    case.check("missing dimension rejected", any("缺少软指标维度" in e for e in errors), str(errors))

    bad = soft_payload()
    bad["dimensions"].append({"name": "硬指标", "score": 100, "deductions": [
        {"item": "查重", "full": 40, "got": 40, "reason": "脚本已判定通过，模型重复填报"}]})
    _, errors = qa.validate_soft(bad)
    case.check("hard dimension rejected", any("未知维度" in e for e in errors), str(errors))

    no_detail = soft_payload()
    no_detail["dimensions"][2]["deductions"] = []
    _, errors = qa.validate_soft(no_detail)
    case.check("empty deductions rejected", any("至少 1 条扣分明细" in e for e in errors), str(errors))

    _, errors = qa.validate_soft({"dimensions": []})
    case.check("empty payload rejected", bool(errors), str(errors))

    hard_pass = {"score": 100.0, "pass": True, "items": [], "full_total": 100,
                 "got_total": 100, "skipped": [], "citations": {"status": "PASS", "count": 0}}
    hard_fail = dict(hard_pass)
    hard_fail["pass"] = False
    case.check("decide PASS", qa.decide(hard_pass, 88.0, 0) == "PASS")
    case.check("decide NEEDS_REWRITE", qa.decide(hard_pass, 82.0, 0) == "NEEDS_REWRITE")
    case.check("decide NEEDS_HUMAN after 2 rounds", qa.decide(hard_pass, 82.0, 2) == "NEEDS_HUMAN")
    case.check("decide HARD_FAIL", qa.decide(hard_fail, 95.0, 0) == "HARD_FAIL")

    text = qa.render_report("demo", "articles/demo/article.md", hard_pass, soft, total, rows,
                            "PASS", 0)
    case.check("report contains hard section", "## 一、硬指标（脚本判定）" in text)
    case.check("report contains deduction rows", "第 2 节两处数据缺少可核实链接" in text)
    case.check("report contains total", "**%s**" % qa._fmt_num(total) in text)

    text_pending = qa.render_report("demo", "articles/demo/article.md", hard_pass, None, 0.0, [],
                                    "PENDING", 0)
    case.check("pending report asks for soft scores", "PENDING" in text_pending)
    case.check("pending report lists three dimensions",
               all(name in text_pending for name in qa.SOFT_DIMENSIONS))

    skipped_hard = dict(hard_pass, skipped=["配图资产"])
    text_skipped = qa.render_report("demo", "articles/demo/article.md", skipped_hard, soft,
                                    total, rows, "PASS", 0)
    case.check("skipped items flagged", "未校验项" in text_skipped)


def run_tests(case):
    run_gate_tests(case)
    run_qa_tests(case)


def main():
    case = GateTest()
    run_tests(case)
    if case.failures:
        print(f"{len(case.failures)} stage gate test(s) failed")
        return 1
    print("All stage gate tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

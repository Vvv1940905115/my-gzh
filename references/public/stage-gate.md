# 阶段闸门与质检报告

> 核心设计原则：**SKILL 管流程，脚本管判定。**
> 凡是"必须挂起""必须达到 85 分""不得编造"这类要求，只要没有脚本兜底，就只是建议。
> 本文件描述的两个脚本把 SKILL.md 的语言约束换成了确定性判定。

## 一、阶段闸门（quality/stage_gate.py）

状态机（单向，不可跳跃）：

```text
track（赛道） -> topic（主题） -> config（选配） -> draft（初稿） -> qa（质检） -> publish（发布）
```

- 稿件由 `quality/new_article.py` 初始化时生成 `articles/<slug>/state.json`。
- 进入任一阶段前，脚本读取 state.json；**前置阶段只要有一个未确认，直接 exit 1 阻断**。
- `--gate` 策略：`auto`（默认，无 state.json 的遗留稿件只 WARN 放行）、`strict`（无 state.json 也阻断）、`off`（显式跳过，需人工说明理由）。

### 命令

```powershell
python quality/stage_gate.py init    --slug <slug> --track "AI工具"      # 新建时由 new_article.py 自动调用
python quality/stage_gate.py confirm --slug <slug> --stage track   --value "AI工具"
python quality/stage_gate.py confirm --slug <slug> --stage topic   --value "<主题>" --note "热点事件 + 出处"
python quality/stage_gate.py confirm --slug <slug> --stage config  --value "<字数|风格|受众|排版|结尾>"
python quality/stage_gate.py confirm --slug <slug> --stage draft
python quality/stage_gate.py check   --slug <slug> --stage publish  # 只校验不改动，不通过 exit 1
python quality/stage_gate.py show    --slug <slug>
python quality/stage_gate.py reset   --slug <slug> --stage qa        # 改稿后把 qa 及之后置为未确认
python quality/stage_gate.py trend                                   # 选题阶段热点规则摘要
```

### topic 阶段的热点规则

`confirm/check --stage topic` 会强制打印 `references/public/trend-tracking.md` 的渠道清单与融入规则：
相关度 ≥4 星的热点优先于常青选题，必须带时间与出处，无法核实的标「需核实」，超过 7 天的热点只作背景素材。
确认时用 `--note` 登记热点事件与出处，便于事后抽查。

### 已接入闸门的脚本

| 脚本 | 阶段 | 行为 |
| --- | --- | --- |
| `quality/new_article.py` | track | 初始化 state.json（`--auto` 用于 task.json 全自动链路，直接确认 track/topic/config） |
| `quality/check_article.py` | qa | 质检前校验前置四阶段；`--gate off/strict` 可调整 |
| `quality/qa_report.py` | qa | 落盘前校验；PASS 时自动 confirm qa |
| `publish/wechat_push.py` | publish | 推送（含 `--dry-run`）前校验 qa 已确认 |

## 二、质检报告（quality/qa_report.py）

评分双轨，落盘 `articles/<slug>/qa-report.md`：

| 类别 | 维度 | 判定方 | 能否被模型改写 |
| --- | --- | --- | --- |
| 硬指标 | 查重 40 / 违禁词 40 / 配图资产 20（权重 20%） | `quality/check_article.py` | 不能，脚本输出照抄 |
| 软指标 | 事实准确 30% / 风格规范 30% / 去 AI 感 20% | 模型 | 必须逐条留痕，脚本校验一致性 |

### 流程

```powershell
python quality/qa_report.py init  --article articles/<slug>/article.md            # 跑硬指标，生成骨架（软指标 PENDING）
python quality/qa_report.py apply --slug <slug> --scores <soft.json>              # 校验软指标后落盘
python quality/qa_report.py show  --slug <slug>
```

### soft.json 契约

```json
{
  "dimensions": [
    {"name": "事实准确", "score": 94, "deductions": [
      {"item": "数据可核实来源", "full": 40, "got": 36, "reason": "第 2 节两处数据缺来源链接，已标注需核实"}
    ]}
  ],
  "note": "可选说明"
}
```

脚本强制校验（任一不满足即拒绝落盘，报告不会被写入）：

1. 维度必须正好是「事实准确 / 风格规范 / 去AI感」三个，多报硬指标维度直接拒绝；
2. 每个维度至少 1 条 `deductions`，每条必须有 `item`、`full`、`got`、`reason`；
3. `reason` 不少于 10 字——"有点问题""还行"这类无信息理由会被拒；
4. `got` 必须落在 `0-full` 之间；
5. **维度得分必须与扣分明细一致**（允许 0.5 分误差），声明 95 分但明细只有 88 分会被拒；
6. `skipped` 项（如 `--skip-images`）不计入硬指标分数，但在报告顶部单独标注「未校验项」，不得当作已通过。

### 状态与后续

| 状态 | 含义 | 后续 |
| --- | --- | --- |
| `PASS` | 总分 ≥85 且硬指标全 PASS | 自动 confirm qa，可进入 publish |
| `NEEDS_REWRITE` | 总分 <85 | 只重写扣分段落，`rewrites` +1，重写后重新 init/apply |
| `NEEDS_HUMAN` | 已重写 2 轮仍 <85 | 输出当前最优版本，转人工介入 |
| `HARD_FAIL` | 硬指标 FAIL | 任何情况下不得发布 |

## 三、为什么这样设计

模型自评天然虚高：写下分数时它看到的是自己的意图，不是读者的感受。
可核查的做法是把"打分"拆成两半——能算的交给脚本，不能算的强制留痕，
让每一次 85 分都带着一串能被抽查的扣分理由。

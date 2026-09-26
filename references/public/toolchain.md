# 工具链与输出契约

> SKILL.md 的指针文件。所有脚本调用前必须遵守本文件的路径契约。

## 输出契约

- 每篇文章使用独立目录：`articles/<slug>/article.md + articles/<slug>/meta.json`。
- `<slug>` 使用小写短横线，例如 `ai-asking-framework`。`meta.json` 可用 `"slug": "<slug>"` 显式覆盖目录名；未填写时，脚本以文章目录名作为唯一标识。
- meta 字段：title、summary（120 字以内）、author、source、cover（封面图相对路径）、tags（5 个标签的数组）。
- 生成或修改稿件时，命令里显式使用 `--article articles/<slug>/article.md --meta articles/<slug>/meta.json`，不要把文章复制到根目录。

## 排版转换

```powershell
python publish/md_to_wechat.py --article articles/<slug>/article.md --meta articles/<slug>/meta.json
```

- 排版师产物必须是该脚本可直接转换的标准 Markdown，图片用相对路径（`images/xxx.png`）。
- 预览 HTML 输出到 `out/`，按稿件 slug 区分。

## 发布草稿

```powershell
python publish/push_wechat_draft.py --article articles/<slug>/article.md --meta articles/<slug>/meta.json
```

- 首次推送某篇稿件时自动新建草稿；后续推送默认更新同一篇草稿。确要另起一篇时才加 `--new-draft`。
- 草稿 ID 按稿件唯一标识保存在 `out/last-draft-id-<slug>.txt`，多篇文章不会互相覆盖。
- 推送完成后脚本会询问是否删除本次本地推送记录；用户确认删除时才清理，未确认则保留。
- 推送成功后脚本会询问是否将本篇正文归档至 `references/private/archive/` 以丰富查重库；用户确认 y 后归档，n 跳过。
- 未配置 `wechat-config.json` 或推送失败时，输出成稿让用户手动粘贴到草稿箱，并明确说明发布步骤未完成。

## 阶段闸门（先于一切写作动作）

状态机 `track -> topic -> config -> draft -> qa -> publish`，状态写在 `articles/<slug>/state.json`：

```powershell
python quality/new_article.py --slug <slug> --title "..." --track "AI工具"   # 建稿即初始化 state.json
python quality/stage_gate.py confirm --slug <slug> --stage track  --value "AI工具"
python quality/stage_gate.py confirm --slug <slug> --stage topic  --value "<主题>" --note "热点事件+出处"
python quality/stage_gate.py confirm --slug <slug> --stage config --value "<字数|风格|受众|排版|结尾>"
python quality/stage_gate.py confirm --slug <slug> --stage draft
python quality/stage_gate.py show    --slug <slug>
```

- 前置阶段未确认时，`check_article.py`、`qa_report.py`、`wechat_push.py` 直接 exit 1 阻断。
- `--gate auto`（默认）对无 state.json 的遗留稿件只 WARN；`--gate strict` 一律阻断；`--gate off` 显式跳过。
- topic 阶段会打印 `references/public/trend-tracking.md` 的热点渠道清单，热点事件与出处用 `--note` 登记。
- 全自动链路（task.json / workflow）用 `new_article.py --auto`，直接确认 track/topic/config。

## 质检报告（硬指标脚本判定，软指标留痕）

```powershell
python quality/qa_report.py init  --article articles/<slug>/article.md
python quality/qa_report.py apply --slug <slug> --scores <soft.json>
python quality/qa_report.py show  --slug <slug>
```

产物 `articles/<slug>/qa-report.md`。软指标评分契约、拒绝条件和四种状态见 `references/public/stage-gate.md`。

## 查重、违禁词与资产检查

```powershell
python quality/check_article.py --article articles/<slug>/article.md --meta articles/<slug>/meta.json
```

- 查重规则：连续 13 字不与来源重复，13 字片段重复率低于 25%（`--run-limit` / `--rate-limit` 可调）。
- 查重来源默认读 `references/private/archive/`，也可用 `--sources` 指定文件或目录。
- 违禁词硬校验默认读 `references/sensitive/banned-words.txt`（格式：词|级别|建议），扫描正文与 meta 标题/摘要；高风险词命中直接 FAIL，中低风险列入待用户确认。
- 同时校验文章引用的本地图片和 `meta.cover` 是否真实存在。
- 引用来源检查会扫描含百分比、倍数、金额、人数等数据的段落；缺来源标记时输出 WARN，可用 `--skip-citations` 显式跳过。该警告必须人工补充或确认，不得当作已通过事实核查。
- 任何一项 FAIL 都不能进入发布；没有查重来源时只做违禁词与资产检查，并在报告注明。

## 图片生成与抓取

```powershell
python image/make_theme_images.py --list
python image/make_theme_images.py --theme <theme>
python image/fetch_images.py search --query "<keywords>"
python image/fetch_images.py fetch --source commons --spec "<query>::<filename>" --retry 3
python image/fetch_images.py fetch --source pexels --spec "<id>::<filename>"
python image/fetch_images.py crop --input images/<src> --output images/cover.jpg --ratio 1200:510
```

- 主题示意图一律走 `make_theme_images.py` + `image/themes.json`；不得再为单篇文章新建硬编码生成器。
- 抓图、Pexels 下载、封面裁剪、候选联系表统一使用 `image/fetch_images.py`；`--retry` 控制单图重试次数。

## 回归测试与资产扫描

修改路径推断、slug、发布记录或图片解析规则后，先运行：

```powershell
python tests/test_contracts.py
python tests/test_quality_and_render.py
python tests/test_workflow.py
python tests/test_stage_gate.py
python quality/check_assets.py
```

- `tests/test_contracts.py` 覆盖 `articles/<slug>/article.md`、同目录 `meta.json`、slug 覆盖、根目录兜底、哈希唯一键、草稿 ID 文件名和图片相对路径解析。
- `tests/test_quality_and_render.py` 覆盖查重、违禁词分级、引用来源警告、公众号 HTML 渲染结构和推送 API 凭据校验（通过 mock 隔离网络）。
- `tests/test_stage_gate.py` 覆盖阶段闸门（顺序确认、跳序阻断、重置、auto 模式）与软指标评分校验（缺维度、多报硬指标、理由过短、分数与明细不一致、四种状态判定）。
- `quality/check_assets.py` 遍历 `articles/*/article.md`，检查 `meta.json`、封面和正文图片引用，并把缺失清单写入 `out/missing-assets.txt`。
- 缺失资产必须先补齐或在终审报告中明确列为阻塞项，不得假装通过。
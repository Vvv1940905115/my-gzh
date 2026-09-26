# my-gzh 公众号内容工作台

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Dependencies](https://img.shields.io/badge/Markdown-3.11-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

一个本地优先的公众号内容生产工程：选题、写作、质检、配图、转微信 HTML、推送草稿箱。核心转换和推送脚本使用 Python 标准库与 Markdown 3.11；参考文章抓取和部分配图脚本需要可选依赖。

## 核心设计原则

> **SKILL 管流程，脚本管判定。**

「必须挂起等待确认」「必须达到 85 分」「不得编造数据」这类要求，如果只是写进提示词，执行与否全看模型自觉。所以本项目把它们拆成两半：

<img width="1386" height="572" alt="螢幕擷取畫面 2026-09-26 190147" src="https://github.com/user-attachments/assets/fda3c8da-81c5-435c-b58e-b1e9d32bea4a" />
<img width="1302" height="516" alt="螢幕擷取畫面 2026-09-26 191010" src="https://github.com/user-attachments/assets/a0cd09a0-5362-4d7c-9acf-2981ec299df9" />


| 环节 | 由谁负责 | 落地脚本 |
| --- | --- | --- |
| 流程与规范 | `SKILL.md` + `references/` | — |
| 阶段准入（track→topic→config→draft→qa→publish） | 脚本判定，未确认即 exit 1 | `quality/stage_gate.py` |
| 硬指标（查重 / 违禁词 / 配图资产） | 脚本判定 | `quality/check_article.py` |
| 软指标（事实 / 风格 / 去 AI 感） | 模型评分，强制逐条扣分留痕 | `quality/qa_report.py` |
| 发布准入 | 脚本校验 qa 已确认 | `publish/wechat_push.py` |

详见 `references/public/stage-gate.md`。

## 能力概览

| 目录 | 作用 |
| --- | --- |
| `SKILL.md` | 内容生成与质检流程规范 |
| `templates/` | 标题、摘要、正文结构模板 |
| `articles/` | 按稿件 slug 存放正文、元信息、阶段状态与质检报告 |
| `publish/` | Markdown 转微信 HTML、上传图片并推送公众号草稿 |
| `quality/` | 阶段闸门、发布前综合质检、质检报告落盘 |
| `workflow/` | AI 自动化任务编排：生成、质检、配图、预览、推送 |
| `image/` | 抓图、候选图管理、封面裁剪、本地示意图生成 |
| `tools/` | 参考文章抓取与只读分析 |
| `references/` | 公共方法、私密素材、敏感词与平台规则 |
| `learned/` | L2 记忆层：发布数据、热点选题、改写技巧跨篇沉淀 |
| `config/` | 依赖清单和公众号配置模板 |

## 目录结构

```text
my-gzh/
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore
├── articles/
│   └── <slug>/
│       ├── article.md
│       ├── meta.json
│       ├── state.json        # 阶段闸门状态
│       └── qa-report.md      # 质检报告（硬指标脚本判定 + 软指标留痕）
├── config/
│   └── requirements.txt
├── lib/
│   └── common.py
├── learned/
│   ├── hot-topics.md          # 热门选题记录（选题阶段读取）
│   ├── performance.md         # 文章数据表现（发布后自动追加）
│   └── rewrite-patterns.md    # 改写技巧与爆款结构（写作阶段读取）
├── publish/
│   ├── md_to_wechat.py
│   ├── wechat_render.py
│   ├── wechat_api.py          # 微信 API 网络层（token 缓存 + 重试）
│   ├── wechat_upload.py       # 图片 / 视频上传
│   ├── wechat_push.py         # 推送业务流
│   └── push_wechat_draft.py
├── quality/
│   ├── init_article.py        # 从模板初始化稿件目录
│   ├── new_article.py        # 建稿并初始化 state.json
│   ├── stage_gate.py         # 阶段闸门：track→topic→config→draft→qa→publish
│   ├── check_article.py      # 查重、违禁词、配图资产硬校验
│   ├── qa_report.py          # 质检报告落盘（评分双轨）
│   ├── post_publish.py        # 发布后数据沉淀到 learned/performance.md
│   ├── format.py              # Markdown 转微信 HTML（独立入口）
│   ├── token_count.py         # 字数 / 段落长度检查
│   └── check_assets.py
├── workflow/
│   ├── run_ai_workflow.py
│   ├── content_generator.py
│   └── cover_generator.py
├── tests/
│   ├── conftest.py
│   ├── test_contracts.py
│   ├── test_quality_and_render.py
│   ├── test_stage_gate.py
│   └── test_workflow.py
├── image/           # 图片工具与主题定义；本地素材放 images/
│   ├── themes.json
│   ├── make_theme_images.py
│   ├── fetch_images.py
│   └── ocr-crops.ps1
├── tools/
│   ├── fetch_reference.py
│   └── analyze_reference.py
├── references/
│   ├── public/
│   ├── private/
│   └── sensitive/
├── templates/
│   ├── viral-titles.md
│   ├── viral-summary.md
│   └── viral-copy.md
├── images/          # 本地素材，不入库
├── out/             # 本地预览与推送记录，不入库
└── private/         # 本地私密数据，不入库
```

> `articles/` 里的 `<slug>` 是稿件标识，例如 `ai-asking-framework`。每个稿件目录必须有一对 `article.md` 和 `meta.json`。`image/` 是脚本与主题定义目录，`images/` 才是本地图片素材目录。

## 环境准备

安装 Python 3.11 或更高版本。Windows 安装时勾选 `Add python.exe to PATH`。

```text
python --version
```

推荐使用虚拟环境隔离依赖（一条命令完成创建 + 安装）：

```text
python -m venv venv
venv\Scripts\activate
pip install -r config/requirements.lock
```

如果你不想用虚拟环境，也可以全局安装：

```text
pip install -r config/requirements.lock
```

核心转换需要 Markdown 3.11。以下任务按需安装：

| 任务 | 命令 |
| --- | --- |
| Markdown 转换 | `python -m pip install markdown==3.11` |
| 抓取参考文章 | `python -m pip install requests trafilatura` |
| 生成或裁剪本地图片 | `python -m pip install pillow` |
| 一次性安装可选依赖 | `python -m pip install -r config/requirements.txt` |

## 配置公众号接口

只在把文章同步到公众号草稿箱时需要配置。手动复制正文可跳过。

1. 设置环境变量（推荐，凭证不落盘）：

```powershell
$env:WECHAT_APP_ID = '你的AppID'
$env:WECHAT_APP_SECRET = '你的AppSecret'
```

2. 在公众号后台「设置与开发」->「基本配置」->「IP 白名单」加入当前公网 IP。

推送脚本优先读取环境变量 `WECHAT_APP_ID` 和 `WECHAT_APP_SECRET`。如果环境变量未设置，会按以下顺序查找配置文件（不推荐）：

1. `$CODEX_HOME/skills/wechat-publisher/config.json`
2. 项目根目录的 `wechat-config.json`

也可以显式指定：

```text
python publish/push_wechat_draft.py --config 路径/config.json
```

> 不要将凭证写入文件、提交到 git、截图或分享。如怀疑泄露，立即在公众号后台重置 AppSecret。

## 稿件结构

推荐每篇文章独立放在 `articles/<slug>/`：

```text
articles/
└── my-new-post/
    ├── article.md
    └── meta.json
```

`meta.json` 示例：

```json
{
  "title": "文章标题",
  "summary": "120 字以内的摘要",
  "author": "作者名",
  "source": "公众号：公众号名",
  "cover": "images/cover.jpg",
  "tags": ["AI", "职场"],
  "video_vid": ""
}
```

封面路径应指向 `images/` 下真实存在的文件。正文里的本地图片也建议使用相对路径，例如 `images/example.jpg`。

## 写作与排版

正文使用标准 Markdown（由 `markdown==3.11` 解析），转换器额外支持公众号特有块：

- `#`、`##`、`###` 标题
- 第一段作为导语
- 图片：`![说明](images/example.jpg)`
- 图注：紧跟图片下一行写 `图注：xxx`
- 引用：`> 内容`
- 高亮框：

```markdown
:::highlight
这里是重点提示。
:::
```

- 笔记框、金句框、卡片框分别使用 `:::note`、`:::quote`、`:::card`
- 表格使用标准 Markdown 表格
- 视频占位：`@video[images/xxx.mp4]`

写作前先读 `SKILL.md` 和 `templates/`。质量评分以 `quality/check_article.py` 的硬指标输出为准，结合 `references/public/quality-score.md` 的四维权重评估，最终落盘到 `articles/<slug>/qa-report.md`。

## 阶段闸门

新稿件必须由 `quality/new_article.py` 创建，它会一并生成 `articles/<slug>/state.json`：

```text
python quality/new_article.py --slug my-new-post --title "文章标题" --track "AI工具"
python quality/stage_gate.py confirm --slug my-new-post --stage track --value "AI工具"
python quality/stage_gate.py confirm --slug my-new-post --stage topic --value "<主题>" --note "热点事件+出处"
python quality/stage_gate.py confirm --slug my-new-post --stage config --value "1500-2000字|深度干货"
python quality/stage_gate.py confirm --slug my-new-post --stage draft
python quality/stage_gate.py show --slug my-new-post
```

前置阶段未确认时，`check_article.py`、`qa_report.py`、`wechat_push.py` 会直接退出并提示缺哪个阶段。
`--gate strict` 连「没有 state.json 的遗留稿件」也一起阻断；`--gate off` 显式跳过。
全自动链路（task.json / workflow）用 `quality/new_article.py --auto`，直接确认 track/topic/config。

## 生成预览 HTML

从项目根目录运行：

```text
python publish/md_to_wechat.py --article articles/my-new-post/article.md --meta articles/my-new-post/meta.json
```

默认输出：

```text
out/<slug>.wechat.html
out/<slug>.wechat.fragment.html
```

`<slug>` 是稿件唯一标识：优先读取 `meta.json` 的 `slug` 字段，缺省时用 `articles/` 下的目录名。脚本仍兼容旧入口：根目录存在 `article.md` 和 `meta.json` 时，可直接运行 `python publish/md_to_wechat.py`，输出为 `out/article.wechat.html`。

浏览器打开预览 HTML，点页面顶部的「复制正文」，再粘贴到公众号后台。

## 开发者设置

启用 pre-commit hook（每次 commit 自动跑测试）：

```text
git config core.hooksPath .githooks
```

只需要在新 clone 的环境里执行一次。CI 会在 GitHub Actions 上自动运行，不受本地配置影响。

## 发布前质检

```text
python quality/check_article.py --article articles/my-new-post/article.md
```

该脚本会检查：

- 违禁词：默认读取 `references/sensitive/banned-words.txt`
- 文本重复：13 字连续查重和 shingle 重复率
- 配图资产：`article.md` 与 `meta.json` 引用的本地图片是否存在
- 引用来源：含百分比、倍数、金额、人数等数据的段落没有来源标记时输出 WARN

详细规则、阈值和输出契约见 `references/public/toolchain.md`。引用来源检查只提示人工补充，可用 `--skip-citations` 显式跳过。

运行 python quality/check_assets.py 可全量扫描所有稿件，检查缺失 meta、封面和正文图片，并将清单写入 out/missing-assets.txt。

### 质检报告（评分双轨 + 留痕）

```text
python quality/qa_report.py init  --article articles/my-new-post/article.md
python quality/qa_report.py apply --slug my-new-post --scores soft.json
python quality/qa_report.py show  --slug my-new-post
```

- 硬指标（查重 / 违禁词 / 配图资产）由脚本判定，模型不得填写。
- 软指标（事实准确 / 风格规范 / 去 AI 感）由模型评分，但必须逐条给出扣分明细；理由少于 10 字、或维度得分与明细合计不一致时，脚本拒绝落盘。
- 报告写入 `articles/my-new-post/qa-report.md`，总分 ≥85 且硬指标全 PASS 时才自动确认 qa 阶段，发布脚本才放行。
- `soft.json` 契约见 `references/public/stage-gate.md`。

可用参数：

```text
--meta articles/my-new-post/meta.json
--sources references/private/archive
--banned-words references/sensitive/banned-words.txt
--skip-dedup
--skip-banned
--skip-images
```

## 推送到公众号草稿箱

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md
```

脚本会：

1. 解析 `--article` 指定的 Markdown；当文件名是 `article.md` 时，自动读取同目录 `meta.json`。
2. 上传封面和正文本地图片。
3. 生成微信兼容 HTML。
4. 调用公众号草稿接口，写入草稿箱。
5. 在公众号后台检查完成后询问是否删除本地推送记录。

本地推送记录按稿件唯一标识分文件保存：

```text
out/last-draft-id-<slug>.txt
out/<slug>.wechat.html
out/<slug>.wechat.fragment.html
out/<slug>.wechat.uploaded.html
```

推送脚本最后会提示：

- 输入 `y`：确认已检查草稿，删除本地推送记录。
- 输入 `n`：保留本地推送记录。
- 无输入或 EOF：保留记录。

强制新建草稿：

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md --new-draft
```

更新指定草稿：

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md --draft-media-id 草稿ID
```

> 草稿 ID 与本地记录按稿件唯一标识（`meta.json` 的 `slug` 字段，缺省时为 `articles/` 下的目录名）分文件保存，多篇文章互不覆盖；路径异常时会用路径哈希兜底，保证 key 唯一。

## 图片方案

### Wikimedia Commons

适合科技、器物、公开照片类素材：

```text
python image/fetch_images.py search --query "humanoid robot"
python image/fetch_images.py fetch --source commons --spec "humanoid robot::real_robot.jpg" --retry 3
```

### Pexels

适合人像、校园、生活场景：

```text
python image/fetch_images.py fetch --source pexels --spec "10498787::p01_group.jpg"
python image/fetch_images.py sheet --input-dir images/_candidates --output images/sheet.png
```

流程是先搜索或下载候选图，必要时生成联系表，人工挑选后用图片 ID 或 Commons 查询词下载高清图。

### 本地生成

```text
python image/make_theme_images.py --list
python image/make_theme_images.py --theme article
python image/fetch_images.py crop --input images/p01_group.jpg --output images/cover.jpg --ratio 1200:510
```

生成图片依赖 Pillow。生成的封面建议裁剪为 1200×510，符合公众号 2.35:1 首图比例。

### 手动准备

把图片放入 `images/`，在 `article.md` 引用：

```markdown
![图片说明](images/example.jpg)
```

## 参考素材

抓取网页或文章：

```text
python tools/fetch_reference.py "https://example.com/article"
```

只读分析素材和稿件：

```text
python tools/analyze_reference.py --slug my-new-post
```

`references/` 分层如下：

| 目录 | 用途 | 是否入库 |
| --- | --- | --- |
| `references/public/` | 风格、评分、热点、爆款分析方法 | 入库 |
| `references/private/` | 知识库、选题库、历史归档 | 不入库 |
| `references/sensitive/` | 违禁词、平台规则 | 不入库 |

## L2 记忆层（learned/）

`learned/` 是跨篇文章的经验沉淀层，让系统越用越懂你的赛道和受众。

| 文件 | 写入时机 | 读取时机 |
| --- | --- | --- |
| `performance.md` | 发布成功后由 `quality/post_publish.py` 自动追加 | 选题阶段：读最近 10 条，参考历史数据 |
| `hot-topics.md` | 选题阶段由 Agent 或人工追加 | 选题阶段：扫最近热点，避免重复选题 |
| `rewrite-patterns.md` | 查重改写阶段由 Agent 或人工追加 | 写作阶段：参考已验证的改写技巧和爆款结构 |

发布闭环：`push_wechat_draft.py` 推送成功后自动调用 `post_publish.py --slug <slug>`，把发布日期、标题、赛道写入 `performance.md`。初始阅读量为 0，后续可手动更新真实数据。

## 数据备份

`references/private/` 与 `references/sensitive/` 不入库，只存在于本机磁盘；磁盘一旦损坏，归档、选题库和知识库会直接丢失。请定期执行：

```text
powershell -File backup_private.ps1  # Windows 打包方案（用系统自带 tar）
```

生成后把归档复制到云盘、私有 Git 仓库或另一台机器。`backups/` 已在 .gitignore 中排除，建议每周至少备份一次，发布重要文章后立即备份。

## AI 自动化工作流

`workflow/` 把稿件脚手架、AI 写作、本地封面和示意图、质检、HTML 预览和草稿推送串成一条可审计流程。它只创建草稿，不会群发。

### 运行方式

先生成内容和预览，停在人工复核：

```text
python workflow/run_ai_workflow.py --task examples/workflow-task.json --force
```

推送前离线演练，渲染 HTML 并校验图片，但不调用公众号接口：

```text
python workflow/run_ai_workflow.py --task examples/workflow-task.json --push --dry-run --force
```

确认无误后推送到公众号草稿箱：

```text
python workflow/run_ai_workflow.py --task examples/workflow-task.json --push --new-draft --force
```

也可以用标准输入传入任务：

```text
type examples\workflow-task.json | python workflow/run_ai_workflow.py --task -
```

### 任务 JSON

```json
{
  "slug": "ai-workflow-example",
  "title": "用 AI 工作流稳定产出公众号内容",
  "brief": "一句话说明选题。",
  "audience": "目标读者",
  "tone": "务实、具体",
  "keywords": ["AI", "自动化"],
  "requirements": ["不编造数据", "保留行动建议"],
  "tags": ["AI"],
  "diagram": {
    "title": "流程标题",
    "items": ["接收任务", "调用 Skill", "自动执行", "输出结果", "复核归档"]
  }
}
```

如果任务里没有 `content_markdown`，工作流会调用 OpenAI 兼容接口，需要先设置：

```text
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

`content_markdown` 适合离线测试或由外部 Agent 提供正文；`content_file` 可以指向已有 Markdown 文件。工作流会从正文提取摘要，生成 `articles/<slug>/` 脚手架、`images/ai-<slug>-cover.png` 和可选流程图，并执行违禁词、图片、引用来源和查重检查。

### 结果与触发器

默认输出：

```text
articles/<slug>/article.md
articles/<slug>/meta.json
out/<slug>.workflow.html
out/workflow-logs/<run_id>.json
```

`review_required` 表示已生成但未推送；`dry_run` 表示推送演练成功；`draft_created` 表示已进入公众号草稿箱。每次失败也会写审计日志，包含阶段和 traceback。

定时器、公众号菜单回调或消息适配器只需要生成同一个任务 JSON，然后调用 `python workflow/run_ai_workflow.py --task <任务文件> --push`。无人工值守时建议默认 `--dry-run`，再由人工确认后二次执行真实推送。

## 常用流程

```text
1) python quality/new_article.py --slug <slug> --title "标题" --track "赛道"
2) 依次确认 track / topic / config（quality/stage_gate.py confirm）
3) 读 SKILL.md、templates/ 和 references/public/（topic 阶段必读 trend-tracking.md）
4) 写 articles/<slug>/article.md 与 articles/<slug>/meta.json
5) python quality/stage_gate.py confirm --slug <slug> --stage draft
6) 准备或确认 images/ 下的图片
7) python quality/check_article.py --article articles/<slug>/article.md
8) python quality/qa_report.py init --article articles/<slug>/article.md
9) python quality/qa_report.py apply --slug <slug> --scores soft.json
10) python quality/check_assets.py
11) python publish/md_to_wechat.py --article articles/<slug>/article.md --meta articles/<slug>/meta.json
12) 浏览器检查 out/<slug>.wechat.html
13) python publish/push_wechat_draft.py --article articles/<slug>/article.md
14) 到公众号后台人工确认草稿
15) 确认无误后，在终端输入 y 清理本地推送记录
```

## 常见问题

### `python` 不是内部或外部命令

重新安装 Python，勾选 `Add python.exe to PATH`，然后新开终端。

### 找不到 `No WeChat config found`

确认 `wechat-config.json` 在项目根目录，或用 `--config` 显式指定配置文件。

### `Config found but incomplete`

`app_id` 或 `app_secret` 为空，或仍保留 `YOUR_*` 占位符。

### `errcode 40164`

当前公网 IP 不在公众号 IP 白名单内。

### `No local images found to upload.`

`article.md` 或 `meta.json` 引用的图片不存在。先补齐 `images/` 下的文件。

### 预览页图片不显示

确认图片相对路径正确，并从项目根目录运行转换脚本。

### 推送后找不到预览 HTML

检查 `out/`。如果推送后输入了 `y`，本地预览和推送记录会被删除；这是确认后的预期行为。

## 安全提醒

- 不要提交或分享 `wechat-config.json`。
- 不要提交 `private/`、`references/private/`、`references/sensitive/`、`images/`、`out/`。
- 公众号文章必须经过人工事实核查、违禁词审查和后台预览。
- 推送脚本只写入公众号草稿箱，不会群发。

## License

MIT。

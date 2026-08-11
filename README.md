# my-gzh 公众号文章工程

一个本地的公众号文章生产流水线：用 Markdown 写正文，转成带内联样式的微信兼容 HTML，可以手动复制进后台，也可以通过接口同步到公众号草稿箱。

## 安全声明

本项目会调用公众号接口，使用前请先了解以下安全规则：

- `wechat-config.json` 是本地凭据文件，包含 AppID 和 AppSecret，已被 `.gitignore` 忽略，禁止提交到 Git 仓库。
- 不要把 `wechat-config.json` 发给别人、发到群聊、截图展示或粘贴到任何公开渠道。
- 开源仓库中只应保留 `wechat-config.example.json`，绝不应出现 `wechat-config.json`。
- 克隆或下载项目后，先复制模板再配置：
  - 把 `wechat-config.example.json` 复制为 `wechat-config.json`。
  - 把 `YOUR_APP_ID_HERE` 替换成自己的 AppID。
  - 把 `YOUR_APP_SECRET_HERE` 替换成自己的 AppSecret。
- 如果怀疑 AppSecret 已经泄露，请立即登录公众号后台重置 AppSecret。
- `images/`、`references/`、`out/` 属于本地素材和生成结果，同样已被忽略，不要强制提交。

## 目录结构

```text
my-gzh/
├── article.md                    # 正文，用标准 Markdown 写
├── meta.json                     # 标题、摘要、作者、来源、封面
├── README.md                     # 本教程
├── .gitignore                    # 忽略 wechat-config.json，避免泄露凭据
├── wechat-config.example.json    # 配置模板
├── wechat-config.json            # 本地公众号凭据，不要提交到仓库
├── images/
│   ├── cover.png                 # 封面原图
│   ├── pic1.png                  # 正文配图
│   ├── pic2.png                  # 正文配图
│   ├── pic3.png                  # 正文配图
│   └── wechat-urls.json          # 手动传图时填微信图片链接
├── tools/
│   ├── md_to_wechat.py           # Markdown 转微信兼容 HTML
│   ├── make_article_images.py    # 用 Pillow 生成封面和配图
│   └── push_wechat_draft.py      # 上传图片并同步到公众号草稿箱
└── out/
    ├── article.wechat.html       # 本地预览页，可点「复制正文」
    ├── article.wechat.fragment.html
    ├── article.wechat.uploaded.html
    └── last-draft-id.txt         # 记录上次草稿 ID，用于自动更新
```

## 一、需要安装什么

### 1. Python 3.10 或更高版本

这个工程的核心脚本都是 Python 写的，需要本机有 Python。

安装步骤：

1. 打开 Python 官网 `https://www.python.org/downloads/`。
2. 下载 3.10 或更高版本，建议 3.12。
3. 安装时**必须勾选 `Add python.exe to PATH`**。
4. 安装完成后，新开一个终端窗口，运行：

```text
python --version
```

能看到版本号就说明装好了。如果提示 `python 不是内部或外部命令`，通常是没勾选 PATH，重新安装一次，或者手动把 Python 安装目录加入系统环境变量。

### 2. Pillow（可选，只有重新生成图片时需要）

转换 HTML 和推送草稿都不需要第三方库。只有运行 `make_article_images.py` 重新生成封面、配图时才需要 Pillow。

安装：

```text
python -m pip install pillow
```

如果电脑里已经生成了 `images/` 下的图片，也可以先不装，直接跳过这步。

### 3. FFmpeg（可选，只有真正跑视频自动化剪辑时需要）

这个工程本身不调用 FFmpeg，FFmpeg 是文章里提到的自动化剪辑工具链。如果你后面想让 Codex 帮你写视频批处理脚本，才需要装。

安装步骤：

1. 到 FFmpeg 官网或 Windows 构建站下载压缩包。
2. 解压到一个固定目录，例如 `C:\ffmpeg`。
3. 把 `C:\ffmpeg\bin` 加入系统环境变量 `Path`。
4. 新开终端运行：

```text
ffmpeg -version
```

能显示版本就说明配置好了。

## 二、配置公众号接口

### 1. 获取 AppID 和 AppSecret

登录公众号后台 `https://mp.weixin.qq.com/`：

1. 进入「设置与开发」→「基本配置」。
2. 复制 `AppID`。
3. 查看或重置 `AppSecret`。

AppSecret 只显示一次，重置后旧值会失效，注意保存好。

### 2. 填写本地配置文件

把这个文件复制一份：

```text
wechat-config.example.json
```

命名为：

```text
wechat-config.json
```

然后填入：

```json
{
  "app_id": "你的 AppID",
  "app_secret": "你的 AppSecret"
}
```

这个工程里的 `wechat-config.json` 已经存在，并且被 `.gitignore` 忽略，不会提交到仓库。如果你在别的电脑上克隆项目，就需要重新创建并填写。

也可以把配置放在这个位置，脚本会优先读取：

```text
~/.codex/skills/wechat-publisher/config.json
```

### 3. 配置 IP 白名单

在公众号后台「设置与开发」→「基本配置」→「IP 白名单」里，添加当前电脑的公网 IP。

怎么知道公网 IP：

```text
curl https://ipinfo.io/ip
```

或者打开 `https://ipinfo.io/ip` 查看。

如果运行推送时微信返回：

```text
errcode 40164, invalid ip xxx.xxx.xxx.xxx, not in whitelist
```

就把报错里的 `xxx.xxx.xxx.xxx` 加进白名单。

注意：如果电脑用的是动态 IP，或者换过 WiFi、热点，白名单可能又要重新加一次。

## 三、写文章

### 1. 编辑正文

打开 `article.md`，用标准 Markdown 写：

```text
## 小标题

正文内容。

![配图说明](images/pic1.png)
```

规则：

- 标题只用 Markdown 的 `#` 到 `###`。
- 图片用相对路径，例如 `images/pic1.png`。
- 不写 `<div class="...">`，不引入外部 CSS/JS。
- 代码块用 ``` 包裹。
- 重要提醒用 `>` 引用块，转换后会变成浅灰底、左侧蓝线的微信兼容提示框。

### 2. 编辑元信息

打开 `meta.json`，修改：

```json
{
  "title": "文章标题",
  "summary": "文章摘要",
  "author": "作者名",
  "source": "公众号：公众号名",
  "cover": "images/cover.png"
}
```

### 3. 准备图片

把封面放在 `images/cover.png`，正文配图放在 `images/` 下，并在 `article.md` 里按相对路径引用。

如果要重新生成默认配图，运行：

```text
python tools/make_article_images.py
```

## 四、本地预览 HTML

运行转换脚本：

```text
python tools/md_to_wechat.py
```

成功后生成：

```text
out/article.wechat.html
```

用浏览器打开这个文件，页面里有点「复制正文」按钮，点一下就能复制带内联样式的微信 HTML。

## 五、两种发布方式

### 方式 A：手动复制到公众号后台

适合偶尔写、不想配接口的情况。

1. 到公众号后台「素材管理」上传 `images/` 里的图片。
2. 复制每张图返回的 `https://mmbiz.qpic.cn/...` 链接。
3. 打开 `images/wechat-urls.json`，把链接填到对应图片路径后面。
4. 重新运行：

```text
python tools/md_to_wechat.py
```

5. 打开 `out/article.wechat.html`，点「复制正文」。
6. 到公众号后台新建图文，粘贴正文。
7. 上传封面、填标题和摘要，存草稿，人工确认后发布。

### 方式 B：接口同步到草稿箱

适合已经配好 AppID、AppSecret 和 IP 白名单的情况。

运行：

```text
python tools/push_wechat_draft.py
```

脚本会依次做这些事：

1. 获取 access_token。
2. 把 `images/cover.png` 作为永久素材上传，拿到封面 `media_id`。
3. 把正文里的配图通过 `media/uploadimg` 上传，拿到 `https://mmbiz.qpic.cn/...` 链接。
4. 用链接替换正文里的本地图片路径。
5. 调用微信草稿接口同步标题、摘要、正文和封面到草稿箱。

第一次运行会新建草稿，并把草稿 `media_id` 保存到：

```text
out/last-draft-id.txt
```

之后再运行，会自动更新同一篇草稿，不会重复创建。

如果确实想新建一篇，运行：

```text
python tools/push_wechat_draft.py --new-draft
```

如果只想更新指定草稿，运行：

```text
python tools/push_wechat_draft.py --draft-media-id 草稿ID
```

推送完成后，刷新公众号后台「草稿箱」就能看到最新版本。

## 六、常见问题

### `python` 不是内部或外部命令

重新安装 Python，安装时勾选 `Add python.exe to PATH`，然后新开终端窗口。

### `ModuleNotFoundError: No module named 'PIL'`

运行：

```text
python -m pip install pillow
```

### `No WeChat config found`

没有找到 `wechat-config.json`，或没有放到脚本能读取的位置。按「二、配置公众号接口」创建并填写。

### `Config found but incomplete`

配置文件的 `app_id` 或 `app_secret` 为空，或者还留着“你的 AppID”这类占位文字，改成真实值。

### `errcode 40164, invalid ip`

当前公网 IP 不在公众号后台白名单，把报错里的 IP 加到「设置与开发」→「基本配置」→「IP 白名单」。

### `errcode 40001 invalid credential`

`app_secret` 填错了，或者 AppSecret 被重置过，重新确认。

### 本地预览里图片不显示

先运行：

```text
python tools/md_to_wechat.py
```

预览页里的图片路径应该是 `../images/xxx.png`。如果还是看不到，检查图片是否真的在 `images/` 目录下。

### 复制到公众号后台后图片还是本地路径

手动发布时，要先在公众号「素材管理」上传图片，并把 `mmbiz.qpic.cn` 链接填进 `images/wechat-urls.json`，再重新转换。

接口发布不需要手动填，`push_wechat_draft.py` 会自动上传并替换。

## 七、常用命令速查

```text
python tools/make_article_images.py     # 重新生成默认配图
python tools/md_to_wechat.py            # 本地转换并生成预览
python tools/push_wechat_draft.py       # 上传图片并同步草稿箱
python tools/push_wechat_draft.py --new-draft
python tools/push_wechat_draft.py --draft-media-id 草稿ID
```

## 八、安全提醒

- `wechat-config.json` 里有 AppSecret，不要发到群里，不要提交到公开仓库。
- 本工程已经用 `.gitignore` 忽略它，但如果你把整个文件夹复制到别处，要注意别把配置文件一起分享出去。
- 所有接口调用都使用微信官方接口，图片必须来自 `media/uploadimg` 返回的链接，外部图片链接会被微信过滤。
- 推送成功后仍然建议到公众号后台人工确认一遍再发布。

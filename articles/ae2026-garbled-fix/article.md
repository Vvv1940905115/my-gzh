# AE 2026.2 插件中文乱码？一个补丁文件搞定

升级 After Effects 2026.2 之后，打开常用的汉化插件，界面里的中文可能突然变成一串看不懂的符号。别急着重装插件，它没坏，是 AE 读文字的方式变了。

这篇只讲一件事：用 `GBK_UTF8_HOOK.aex` 这个补丁文件，3 步把插件中文救回来。

我是自学实操研究的，AI 应用落地复合背景。遇到这种升级后突然翻车的小坑，我习惯先看补丁仓库说明，再用真实截图记录安装和修复结果。

## 乱码不是插件坏了，是编码读错了

汉化插件里的中文，很多还停留在 GBK 编码。补丁仓库的 README 说，AE 2026.2 开始会按 UTF-8 去解析这类文本，两套编码一撞车，界面自然就乱码了。

一句话说：插件还是原来的插件，AE 却换了另一本“密码本”。

![修复工具仓库](images/fig1-ae2026-garbled-repo.png)

图注：GitHub 仓库的 README 直接写明了乱码成因

## 方案只有一个 aex 文件

修复工具叫 `ae-pr-2026.2-plugin-chinese-garbled-fix-tool`，核心文件就是 `GBK_UTF8_HOOK.aex`。它不重装插件，也不改系统区域，只在 AE 加载插件时把编码解析对上。

补丁只有 1.14MB，省下的是你重装十遍插件的一晚上。

## 手把手安装，3 步

### 第 1 步：下载解压

在 GitHub 搜仓库名 `ae-pr-2026.2-plugin-chinese-garbled-fix-tool`，下载压缩包后解压。里面能看到 `GBK_UTF8_HOOK.aex`、`README.md` 和安装说明，一共 3 个文件。

![解压后的文件](images/fig2-ae2026-garbled-files.png)

图注：解压后只关心这个 aex 文件就够了

### 第 2 步：复制到 MediaCore

把 `GBK_UTF8_HOOK.aex` 复制到 Adobe 的公共插件目录，默认路径：

```text
C:\Program Files\Adobe\Common\Plug-ins\7.0\MediaCore\
```

这个目录里通常已经有 BorisFX、Digital Anarchy、Twixtor8AE 这类插件。如果你的 Adobe 装在别的盘，就按实际存在的 `Adobe\Common\Plug-ins\7.0\MediaCore` 路径放。

![MediaCore 目录](images/fig3-ae2026-garbled-mediacore.png)

图注：把 aex 放进 MediaCore，和其它插件一起

### 第 3 步：完全退出并重启 AE

先确认 AE 真的退干净了，再重新打开。我这里启动画面已经到 AE 26.3.0（Build 87），正在加载 2457 个增效工具，说明插件列表会重新走一遍。

## 修复前后对比

乱码时，Deep Glow 2 的参数名和选项都会挤成一串看不懂的符号，很多项只能靠猜。

![修复前：Deep Glow 2 参数乱码](images/fig4-ae2026-garbled-before.png)

图注：修复前，Deep Glow 2 的参数界面乱码

同一个 LOOKAE 悬浮车模板里，Beauty Box 能正常加载，Deep Glow 2 的效果控件也从乱码变回中文。辉光强度、混合模式、色彩映射、镜头污垢这些参数名都能直接看懂。

![修复后：Deep Glow 2 中文界面](images/fig5-ae2026-garbled-after.png)

图注：修复后，Deep Glow 2 的中文效果控件

这是第三方上传的补丁，介意来源的话，先在备用机或虚拟机里试一遍，再上主力机。

## 什么情况它救不了

- 只治“GBK 被当 UTF-8 解析”这一类乱码，插件崩溃、缺文件、授权问题不归它管；
- AE 2026.2 之前的版本没有这个毛病，不用装；
- Adobe 后续版本可能继续改行为，每次大版本升级后先开插件看一眼。

## 写在最后

整个修复就是 3 步：下载、复制到 MediaCore、重启 AE。比重装一遍 Adobe 全家桶体面多了。

乱码不是玄学，是编码在打架。找对打架的原因，补丁就能拍上去。

你的 AE 里还有哪些升级后翻车的插件？评论区说一声，下一篇拆给你。

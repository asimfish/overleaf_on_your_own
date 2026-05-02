# Overleaf on Your Own

在 Cursor / VSCode / Windsurf 中实现类 Overleaf 的 LaTeX 实时编译预览体验。

**功能特性：**

**实时预览**
- `Ctrl+S` 自动保存 + 编译 + 打开 PDF 预览
- PDF 双击任意位置 → 跳转到对应 tex 源码行（反向 SyncTeX）
- tex 行光标 → 高亮 PDF 对应位置（正向 SyncTeX，`Ctrl+Alt+J`）
- 编译错误行内红色波浪线提示
- 编译状态栏实时显示
- 文件变化自动编译（500ms 防抖）
- LaTeX 自动按视图宽度换行，默认关闭 minimap 和横向滚动条

**自动调页数**
- 一键将论文压缩/扩展到指定页数
- 自动应用排版策略（图片间距、microtype、vspace 等）
- 每轮自动备份，编译失败自动恢复

**自动迭代改稿**
- Claude API 模拟学术审稿人，多轮审稿+修改循环
- 支持 ICML / ICLR / NeurIPS / CVPR / ECCV / AAAI
- 断点续跑，每轮保存状态和备份 PDF
- 灵感来源：[ARIS](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)

## 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/asimfish/overleaf_on_your_own/main/install.sh | bash
```

或手动安装：

```bash
git clone https://github.com/asimfish/overleaf_on_your_own.git
cd overleaf_on_your_own
bash install.sh
```

## 环境要求

- Linux / macOS
- [Cursor](https://cursor.sh)、VSCode 或 Windsurf（含 Remote / Server 环境）
- [LaTeX Workshop 扩展](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)（扩展 ID：`James-Yu.latex-workshop`）

## 安装步骤详解

### 第一步：安装 TeX Live

**Ubuntu / Debian：**
```bash
# 精简版（推荐，~1GB）
sudo apt install texlive-latex-extra texlive-science texlive-fonts-recommended latexmk -y

# 完整版（~5GB，最稳定）
sudo apt install texlive-full latexmk -y
```

**macOS：**
```bash
brew install --cask mactex
```

### 第二步：安装 LaTeX Workshop 扩展

在 Cursor / VSCode / Windsurf 中：
- 按 `Ctrl+Shift+X` 打开扩展面板
- 搜索 `LaTeX Workshop`（James Yu 发布）
- 点击安装

或命令行安装：
```bash
cursor --install-extension James-Yu.latex-workshop
# 或 VSCode：
code --install-extension James-Yu.latex-workshop
```

Windsurf Remote / Server 环境中，`install.sh` 会优先尝试调用
`~/.windsurf-server/bin/*/bin/windsurf-server --install-extension` 自动安装扩展。
如果远程编辑器配置了代理，请先确认代理端口可用。

### 第三步：运行安装脚本

```bash
bash install.sh
```

脚本会自动：
1. 将 LaTeX Workshop 配置写入你的工作区 `.vscode/settings.json`
2. 将 PDF viewer / SyncTeX / 自动换行等用户级设置写入编辑器 `settings.json`
3. 将快捷键配置写入 Cursor/VSCode/Windsurf 用户 `keybindings.json`
4. 验证 `latexmk`、`pdflatex`、`bibtex` 和 `synctex` 是否可用
5. 自动安装 `James-Yu.latex-workshop` 扩展（可用 `--skip-extension` 跳过）

常用参数：

```bash
# 配置当前目录
bash install.sh

# 配置指定论文目录
bash install.sh /path/to/paper

# 只写配置，不安装扩展
bash install.sh --skip-extension

# 预览将要执行的操作
bash install.sh --dry-run
```

## 使用方式

1. 用 Cursor/VSCode/Windsurf 打开包含 `.tex` 文件的项目文件夹
2. 打开主 `.tex` 文件
3. 按 `Ctrl+S` → 自动编译，PDF 在 LaTeX Workshop 的 PDF tab 中打开
4. 在 PDF 中**双击**任意文字 → 左侧编辑器跳转到对应 tex 行
5. 在 tex 文件中按 `Ctrl+Alt+J` → PDF 滚动到对应段落

## 快捷键一览

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 保存 + 编译 + 打开 PDF |
| 双击 PDF | 跳转到对应 tex 行（反向 SyncTeX）|
| `Ctrl+Alt+J` | 正向 SyncTeX（tex → PDF）|
| `Ctrl+Alt+B` | 手动触发编译 |

## 高级功能

### 自动调页数

```bash
# 压缩论文到 8 页
python3 tools/auto_page_fit.py paper/main.tex --target 8

# 先试运行，不修改文件
python3 tools/auto_page_fit.py paper/main.tex --target 8 --dry-run
```

**可选依赖（页数读取更准确）：**
```bash
sudo apt install poppler-utils
```

详细说明见 [skills/page-fit/SKILL.md](skills/page-fit/SKILL.md)

---

### 自动迭代改稿

**前置要求：**
```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_api_key_here
```

```bash
# 针对 ICML 自动改稿（最多 4 轮）
python3 tools/auto_revise.py paper/main.tex --venue ICML

# 人工确认模式（每轮审稿后暂停）
python3 tools/auto_revise.py paper/main.tex --venue ICML --human-checkpoint

# 从上次中断处继续
python3 tools/auto_revise.py paper/main.tex --venue ICML --resume

# 只审稿，不修改论文
python3 tools/auto_revise.py paper/main.tex --venue ICLR --dry-run
```

**组合使用：**
```bash
# 先改稿，再调页数
python3 tools/auto_revise.py paper/main.tex --venue ICML
python3 tools/auto_page_fit.py paper/main.tex --target 8
```

详细说明见 [skills/auto-revise/SKILL.md](skills/auto-revise/SKILL.md)

---

## 项目结构

```
overleaf_on_your_own/
├── install.sh                        # 一键安装脚本
├── configs/
│   ├── workspace_settings.json       # LaTeX Workshop 工作区配置
│   └── keybindings_patch.json        # 快捷键配置
├── tools/
│   ├── auto_page_fit.py              # 自动调页数
│   └── auto_revise.py                # 自动迭代改稿
└── skills/
    ├── page-fit/SKILL.md             # page-fit 使用说明
    └── auto-revise/SKILL.md          # auto-revise 使用说明
```

## 配置说明

所有配置位于 `configs/` 目录：

- `configs/workspace_settings.json` — 工作区 LaTeX Workshop 设置
- `configs/keybindings_patch.json` — 需要添加到用户 keybindings 的快捷键

如需手动配置，参考这两个文件的内容。

## 常见问题

**Q: PDF 预览模糊？**
A: 已通过 `zoom: page-width` 修复，重载窗口（`Ctrl+Shift+P` → `Reload Window`）后生效。

**Q: 双击 PDF 没有跳转？**
A: 确认 `synctex` 已安装（`which synctex`），且编译时使用了 `-synctex=1` 参数（已内置）。还要确认 PDF 是通过 LaTeX Workshop 打开的：在 `.tex` 中按 `Ctrl+S`，或使用命令面板 `LaTeX Workshop: View LaTeX PDF`。直接从文件树打开 `.pdf` 通常不支持源码跳转。

**Q: tex 太长，需要左右滚动？**
A: 安装脚本会启用 `editor.wordWrap: on`，并对 `[latex]` / `[tex]` 单独开启自动换行。若旧窗口未生效，请执行 `Ctrl+Shift+P` → `Reload Window`，或按 `Alt+Z` 临时切换 word wrap。

**Q: conda 环境中的 `pdflatex` 报 `pdflatex.fmt` 缺失？**
A: 安装脚本会给 LaTeX Workshop 工具配置写入 PATH，并优先使用 `/usr/bin/pdflatex`、`/usr/bin/bibtex`、`/usr/bin/synctex`，避免远程 conda TeX Live 不完整导致编译失败。

**Q: 编译没有自动触发？**
A: 确认在 Cursor/VSCode 打开的是项目**根目录**（含 `.vscode/` 文件夹的目录），而非直接打开单个 `.tex` 文件。

**Q: 与现有配置冲突？**
A: `install.sh` 会合并配置而非覆盖，原有设置不会丢失。

## License

MIT

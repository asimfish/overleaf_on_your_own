# Overleaf on Your Own

在 Cursor/VSCode 中实现类 Overleaf 的 LaTeX 实时编译预览体验。

**功能特性：**
- `Ctrl+S` 自动保存 + 编译 + 打开 PDF 预览
- PDF 双击任意位置 → 跳转到对应 tex 源码行（反向 SyncTeX）
- tex 行光标 → 高亮 PDF 对应位置（正向 SyncTeX，`Ctrl+Alt+J`）
- 编译错误行内红色波浪线提示
- 编译状态栏实时显示
- 文件变化自动编译（500ms 防抖）

## 快速安装

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/overleaf_on_your_own/main/install.sh | bash
```

或手动安装：

```bash
git clone https://github.com/YOUR_USERNAME/overleaf_on_your_own.git
cd overleaf_on_your_own
bash install.sh
```

## 环境要求

- Linux / macOS
- [Cursor](https://cursor.sh) 或 VSCode
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

在 Cursor / VSCode 中：
- 按 `Ctrl+Shift+X` 打开扩展面板
- 搜索 `LaTeX Workshop`（James Yu 发布）
- 点击安装

或命令行安装：
```bash
cursor --install-extension James-Yu.latex-workshop
# 或 VSCode：
code --install-extension James-Yu.latex-workshop
```

### 第三步：运行安装脚本

```bash
bash install.sh
```

脚本会自动：
1. 将 LaTeX Workshop 配置写入你的工作区 `.vscode/settings.json`
2. 将快捷键配置写入 Cursor/VSCode 用户 `keybindings.json`
3. 验证 `latexmk` 和 `synctex` 是否可用

## 使用方式

1. 用 Cursor/VSCode 打开包含 `.tex` 文件的项目文件夹
2. 打开主 `.tex` 文件
3. 按 `Ctrl+S` → 自动编译，PDF 在右侧 tab 打开
4. 在 PDF 中**双击**任意文字 → 左侧编辑器跳转到对应 tex 行
5. 在 tex 文件中按 `Ctrl+Alt+J` → PDF 滚动到对应段落

## 快捷键一览

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+S` | 保存 + 编译 + 打开 PDF |
| 双击 PDF | 跳转到对应 tex 行（反向 SyncTeX）|
| `Ctrl+Alt+J` | 正向 SyncTeX（tex → PDF）|
| `Ctrl+Alt+B` | 手动触发编译 |

## 配置说明

所有配置位于 `configs/` 目录：

- `configs/workspace_settings.json` — 工作区 LaTeX Workshop 设置
- `configs/keybindings_patch.json` — 需要添加到用户 keybindings 的快捷键

如需手动配置，参考这两个文件的内容。

## 常见问题

**Q: PDF 预览模糊？**
A: 已通过 `zoom: page-width` 修复，重载窗口（`Ctrl+Shift+P` → `Reload Window`）后生效。

**Q: 双击 PDF 没有跳转？**
A: 确认 `synctex` 已安装（`which synctex`），且编译时使用了 `-synctex=1` 参数（已内置）。

**Q: 编译没有自动触发？**
A: 确认在 Cursor/VSCode 打开的是项目**根目录**（含 `.vscode/` 文件夹的目录），而非直接打开单个 `.tex` 文件。

**Q: 与现有配置冲突？**
A: `install.sh` 会合并配置而非覆盖，原有设置不会丢失。

## License

MIT

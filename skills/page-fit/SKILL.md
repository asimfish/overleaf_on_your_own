---
name: page-fit
description: 自动调整 LaTeX 论文页数到目标值
usage: /page-fit <tex文件路径> --target <目标页数>
examples:
  - /page-fit paper/main.tex --target 8
  - /page-fit paper/icml2026.tex --target 9 --max-rounds 5 --dry-run
---

# Page Fit — 自动调整论文页数

## 功能

自动将 LaTeX 论文压缩或扩展到指定页数。通过迭代应用排版策略并重新编译，直到达到目标页数或超过最大轮次。

## 使用方法

```
/page-fit <tex文件路径> --target <目标页数> [选项]
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `tex文件路径` | 主 .tex 文件路径（必需） | — |
| `--target` / `-t` | 目标页数（必需） | — |
| `--max-rounds` / `-r` | 最大调整轮次 | 5 |
| `--dry-run` | 仅分析，不修改文件 | false |

### 示例

```bash
# 压缩到 8 页
python3 tools/auto_page_fit.py paper/main.tex --target 8

# 先试运行，看会应用哪些策略
python3 tools/auto_page_fit.py paper/main.tex --target 8 --dry-run

# 最多尝试 10 轮
python3 tools/auto_page_fit.py paper/main.tex --target 8 --max-rounds 10
```

## 工作原理

### 压缩策略（页数过多时）
1. 压缩图片上下间距（abovecaptionskip / belowcaptionskip）
2. 压缩列表间距（itemsep）
3. 启用 microtype 字体微调（自动压缩约 0.5 页）
4. 缩小 vspace 间距

### 扩展策略（页数不足时）
1. 放大图片间距
2. 放大 vspace 间距

### 安全机制
- 每轮修改前自动备份（`main_round1.tex`、`main_round2.tex`...）
- 编译失败时自动恢复备份
- 防止过冲（如目标 8 页，压到 7 页时自动回退）
- 生成 `PAGE_FIT_LOG.json` 记录每轮调整详情

## 输出文件

- `{stem}_round1.tex`、`{stem}_round2.tex`... — 每轮备份
- `PAGE_FIT_LOG.json` — 调整日志

## 当自动策略不足时

如果自动策略用完后仍未达到目标，脚本会给出手动建议：
- 缩短段落或删减冗余句子
- 调整图表大小（`[width=0.45\linewidth]` 等）
- 修改 `\vspace` / `\hspace` 数值
- 使用 `\small` 或 `\footnotesize` 缩小表格字体

## 安装依赖

```bash
# 页数读取（推荐安装）
sudo apt install poppler-utils   # 提供 pdfinfo
# 或
sudo apt install ghostscript     # 提供 gs
```

如果两者都没有，脚本会从 .log 文件中估算页数（精度稍低）。

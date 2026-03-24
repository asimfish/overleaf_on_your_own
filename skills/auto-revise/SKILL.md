---
name: auto-revise
description: 自动迭代改稿 — Claude 审稿 + 修改循环，直到达到目标分数
usage: /auto-revise <tex文件路径> --venue <会议名> [选项]
examples:
  - /auto-revise paper/main.tex --venue ICML
  - /auto-revise paper/main.tex --venue ECCV --rounds 3 --human-checkpoint
  - /auto-revise paper/main.tex --venue ICLR --resume
---

# Auto Revise — 自动迭代改稿

## 功能

使用 Claude API 模拟学术审稿人，对 LaTeX 论文进行多轮审稿+修改循环，直到评分达到目标（默认 7/10）或完成指定轮次。

**灵感来源：** [ARIS (Auto-Research-In-Sleep)](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep)

## 前置要求

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your_api_key_here
```

## 使用方法

```
/auto-revise <tex文件路径> --venue <会议> [选项]
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `tex文件路径` | 主 .tex 文件路径（必需） | — |
| `--venue` / `-v` | 目标会议（必需） | — |
| `--rounds` / `-r` | 最大改稿轮次 | 4 |
| `--resume` | 从上次中断处继续 | false |
| `--human-checkpoint` | 每轮审稿后等待人工确认 | false |
| `--dry-run` | 只审稿不修改 | false |

### 支持的会议

| 会议 | 页数限制 |
|------|----------|
| ICML | 8 页 |
| ICLR | 8 页 |
| NeurIPS | 9 页 |
| CVPR | 8 页 |
| ECCV | 14 页 |
| AAAI | 7 页 |
| CUSTOM | 8 页 |

### 示例

```bash
# 基础用法：ICML 4 轮改稿
python3 tools/auto_revise.py paper/main.tex --venue ICML

# 人工确认模式（每轮审稿后暂停）
python3 tools/auto_revise.py paper/main.tex --venue ECCV --human-checkpoint

# 从上次中断处继续
python3 tools/auto_revise.py paper/main.tex --venue ICML --resume

# 只审稿，不修改论文
python3 tools/auto_revise.py paper/main.tex --venue ICLR --dry-run
```

## 工作流程（每轮）

```
A. 审稿  → Claude 模拟 reviewer，输出评分 + 问题列表
B. 改稿  → Claude 根据审稿意见修改 .tex 源文件
C. 编译  → latexmk 验证修改后能正常编译
D. 记录  → 写入 AUTO_REVIEW.md 和 REVIEW_STATE.json
```

### 通过条件

- 分数 ≥ 7/10，**或**
- 评级包含 "accept" / "ready" / "submission ready" / "strong accept"

## 输出文件

| 文件 | 内容 |
|------|------|
| `AUTO_REVIEW.md` | 每轮审稿意见 + 修改记录 |
| `REVIEW_STATE.json` | 当前状态（支持断点续跑）|
| `{stem}_round1_before.tex` | 每轮修改前备份 |
| `{stem}_round1.pdf` | 每轮编译结果 PDF |

## 断点续跑

脚本自动保存状态到 `REVIEW_STATE.json`。如果中途中断（断网、关机等），加 `--resume` 参数即可从上次轮次继续：

```bash
python3 tools/auto_revise.py paper/main.tex --venue ICML --resume
```

> 超过 24 小时未完成的任务会自动重新开始。

## 安全机制

- 每轮修改前自动备份 `.tex` 文件
- 编译失败时自动恢复备份，不丢失任何内容
- 不伪造引用 — 只使用 .bib 文件中已有的文献
- 保留原有 `\documentclass` 和 `\usepackage` 配置

## 结合 page-fit 使用

```bash
# 先改稿到达标分数
python3 tools/auto_revise.py paper/main.tex --venue ICML

# 再压缩到目标页数
python3 tools/auto_page_fit.py paper/main.tex --target 8
```

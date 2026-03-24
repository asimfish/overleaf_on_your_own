#!/usr/bin/env python3
"""
auto_revise.py — 自动迭代改稿（Claude API 审稿 + 修改循环）

用法：
    python3 tools/auto_revise.py paper/main.tex --venue ICML --rounds 3
    python3 tools/auto_revise.py paper/main.tex --venue ICML --rounds 3 --resume

环境变量：
    ANTHROPIC_API_KEY  — Claude API Key（必需）

工作流程（每轮）：
    A. Claude 审稿  → 评分 + 问题列表
    B. Claude 改稿  → 修改 .tex 文件
    C. 编译验证     → 确保编译通过
    D. 记录日志     → AUTO_REVIEW.md + REVIEW_STATE.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("[错误] 请先安装 anthropic SDK：pip install anthropic")
    sys.exit(1)


MAX_ROUNDS = 4
PASS_THRESHOLD = 7.0          # 达到此分数视为通过
PASS_KEYWORDS = ["accept", "ready", "submission ready", "strong accept"]
MODEL = "claude-opus-4-6"

VENUE_INFO = {
    "ICML":  {"pages": 8,  "style": "ICML 2026", "blind": True},
    "ICLR":  {"pages": 8,  "style": "ICLR 2026", "blind": True},
    "NeurIPS":{"pages": 9, "style": "NeurIPS 2025", "blind": True},
    "CVPR":  {"pages": 8,  "style": "CVPR 2026", "blind": True},
    "ECCV":  {"pages": 14, "style": "ECCV 2026", "blind": True},
    "AAAI":  {"pages": 7,  "style": "AAAI 2026", "blind": True},
    "CUSTOM":{"pages": 8,  "style": "custom venue", "blind": False},
}


REVIEW_PROMPT = """
You are a senior {venue} reviewer with expertise in machine learning and robotics.
Review the following LaTeX paper and provide structured feedback.

Venue: {venue} ({style}), page limit: {pages} pages

Paper content:
<paper>
{paper_content}
</paper>

Provide your review in the following EXACT format:

SCORE: <integer 1-10>
VERDICT: <one of: reject / weak reject / borderline / weak accept / accept / strong accept>

CRITICAL WEAKNESSES:
1. [Issue title]: [Detailed description and why it matters]
2. [Issue title]: [Detailed description and why it matters]
(list all critical issues)

MAJOR WEAKNESSES:
1. [Issue title]: [Description]
(list all major issues)

MINOR WEAKNESSES:
1. [Issue title]: [Description]
(list all minor issues)

STRENGTHS:
1. [Strength]
(list key strengths)

REQUIRED FIXES (in priority order):
1. [Specific actionable fix for critical issue 1]
2. [Specific actionable fix for critical issue 2]
...

Be rigorous. Focus on novelty, technical soundness, experimental validation, and clarity.
Do not hallucinate citations or results not present in the paper.
"""

REVISE_PROMPT = """
You are an expert researcher revising a LaTeX paper based on reviewer feedback.

Venue: {venue}, target: improve from score {score}/10 to at least {threshold}/10

Reviewer feedback:
<review>
{review}
</review>

Current paper (LaTeX source):
<paper>
{paper_content}
</paper>

Instructions:
1. Address ALL required fixes from the review, in priority order
2. Modify the LaTeX source directly — output the COMPLETE revised .tex content
3. Do NOT change \\documentclass, \\usepackage lines, or style settings
4. Do NOT fabricate citations — only use references already in the .bib file
5. Mark each change with a comment: % [REVISED: reason]
6. Focus on the highest-impact changes first
7. Preserve the overall structure and length (stay within page limit)

Output ONLY the complete revised LaTeX content, starting with \\documentclass.
Do not include any explanation outside the LaTeX source.
"""


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {"status": "new", "round": 0}
    data = json.loads(state_file.read_text())
    # 超过 24h 的 in_progress 视为过期
    if data.get("status") == "in_progress":
        ts = data.get("timestamp", 0)
        if time.time() - ts > 86400:
            return {"status": "new", "round": 0}
    if data.get("status") == "completed":
        return {"status": "new", "round": 0}
    return data


def save_state(state_file: Path, state: dict):
    state["timestamp"] = time.time()
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def compile_pdf(tex_file: Path) -> bool:
    result = subprocess.run(
        ["latexmk", "-pdf", "-synctex=1", "-interaction=nonstopmode",
         "-file-line-error", str(tex_file)],
        cwd=tex_file.parent,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def parse_score(review_text: str) -> float:
    m = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", review_text)
    return float(m.group(1)) if m else 0.0


def parse_verdict(review_text: str) -> str:
    m = re.search(r"VERDICT:\s*(.+)", review_text)
    return m.group(1).strip().lower() if m else ""


def is_passing(score: float, verdict: str) -> bool:
    if score >= PASS_THRESHOLD:
        return True
    return any(kw in verdict for kw in PASS_KEYWORDS)


def extract_latex(response_text: str, original: str) -> str:
    """从模型回复中提取 LaTeX 内容。"""
    # 尝试提取代码块
    m = re.search(r"```(?:latex|tex)?\n([\s\S]+?)\n```", response_text)
    if m:
        return m.group(1)
    # 若回复以 \documentclass 开头
    if "\\documentclass" in response_text:
        idx = response_text.index("\\documentclass")
        return response_text[idx:]
    # 兜底：返回原始内容
    print("  [警告] 无法提取 LaTeX 内容，保留原文")
    return original


def append_review_log(log_file: Path, round_num: int, score: float,
                      verdict: str, review: str, changes: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"""
## Round {round_num} — {timestamp}

**Score:** {score}/10  |  **Verdict:** {verdict}

<details>
<summary>Full Reviewer Response</summary>

{review}

</details>

**Changes Applied:**
{changes}

---
"""
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(entry)


def run(tex_file: Path, venue: str, max_rounds: int, resume: bool,
        human_checkpoint: bool, dry_run: bool):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[错误] 请设置环境变量 ANTHROPIC_API_KEY")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    venue_meta = VENUE_INFO.get(venue.upper(), VENUE_INFO["CUSTOM"])
    paper_dir = tex_file.parent
    state_file = paper_dir / "REVIEW_STATE.json"
    log_file = paper_dir / "AUTO_REVIEW.md"

    state = load_state(state_file) if resume else {"status": "new", "round": 0}
    start_round = state.get("round", 0) + 1

    if not log_file.exists():
        log_file.write_text(
            f"# Auto Review Log — {venue}\n\nStarted: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n"
        )

    print(f"\n{'═'*60}")
    print(f"  Auto Revise  |  venue: {venue}  |  目标分数: {PASS_THRESHOLD}/10")
    print(f"  轮次: {start_round} ~ {max_rounds}  |  模型: {MODEL}")
    print(f"{'═'*60}\n")

    current_score = state.get("last_score", 0.0)

    for round_num in range(start_round, max_rounds + 1):
        print(f"\n── Round {round_num}/{max_rounds} ──────────────────────────────────")

        # 读取当前论文
        paper_content = tex_file.read_text(encoding="utf-8")

        # ── Phase A: 审稿 ────────────────────────────────────────
        print("[A] 审稿中...")
        review_prompt = REVIEW_PROMPT.format(
            venue=venue,
            style=venue_meta["style"],
            pages=venue_meta["pages"],
            paper_content=paper_content,
        )
        review_response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": review_prompt}],
        )
        review_text = review_response.content[0].text
        current_score = parse_score(review_text)
        verdict = parse_verdict(review_text)

        print(f"  分数: {current_score}/10  |  评级: {verdict}")

        # 保存备份
        backup = tex_file.with_name(f"{tex_file.stem}_round{round_num}_before.tex")
        shutil.copy2(tex_file, backup)
        print(f"  备份: {backup.name}")

        # 检查是否已通过
        if is_passing(current_score, verdict):
            print(f"\n[通过] 分数 {current_score}/10 达到目标 {PASS_THRESHOLD}/10！")
            append_review_log(log_file, round_num, current_score, verdict,
                              review_text, "_无需修改，已达标_")
            state.update({"status": "completed", "round": round_num,
                          "last_score": current_score, "last_verdict": verdict})
            save_state(state_file, state)
            break

        # Human checkpoint
        if human_checkpoint:
            print(f"\n[人工审核] 分数 {current_score}/10，审稿意见如下：")
            print(review_text[:1500] + "..." if len(review_text) > 1500 else review_text)
            ans = input("\n继续修改？[Y/n/stop]: ").strip().lower()
            if ans in ("n", "stop", "q"):
                print("[停止] 用户中止")
                break

        if dry_run:
            print("[dry-run] 跳过修改")
            continue

        # ── Phase B: 改稿 ────────────────────────────────────────
        print("[B] 改稿中...")
        revise_prompt = REVISE_PROMPT.format(
            venue=venue,
            score=current_score,
            threshold=PASS_THRESHOLD,
            review=review_text,
            paper_content=paper_content,
        )
        revise_response = client.messages.create(
            model=MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": revise_prompt}],
        )
        revised_latex = extract_latex(revise_response.content[0].text, paper_content)

        # 写入修改后的 .tex
        tex_file.write_text(revised_latex, encoding="utf-8")

        # ── Phase C: 编译验证 ─────────────────────────────────────
        print("[C] 编译验证...")
        if not compile_pdf(tex_file):
            print("  [错误] 编译失败，恢复备份")
            shutil.copy2(backup, tex_file)
            compile_pdf(tex_file)
            changes_summary = "编译失败，已恢复备份"
        else:
            pdf_backup = tex_file.with_name(f"{tex_file.stem}_round{round_num}.pdf")
            shutil.copy2(tex_file.with_suffix(".pdf"), pdf_backup)
            print(f"  PDF 备份: {pdf_backup.name}")
            changes_summary = f"已应用修改（见 {backup.name}）"

        # ── Phase D: 记录日志 ─────────────────────────────────────
        append_review_log(log_file, round_num, current_score, verdict,
                          review_text, changes_summary)
        state.update({"status": "in_progress", "round": round_num,
                      "last_score": current_score, "last_verdict": verdict})
        save_state(state_file, state)
        print(f"  日志已写入 AUTO_REVIEW.md")

    else:
        print(f"\n[结束] 达到最大轮次 {max_rounds}，最终分数 {current_score}/10")
        state.update({"status": "completed", "round": max_rounds,
                      "last_score": current_score})
        save_state(state_file, state)

    print(f"\n{'═'*60}")
    print(f"
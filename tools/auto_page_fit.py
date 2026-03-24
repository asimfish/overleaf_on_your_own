#!/usr/bin/env python3
"""
auto_page_fit.py — 自动调整 LaTeX 论文页数到目标值

用法：
    python3 tools/auto_page_fit.py paper/main.tex --target 8
    python3 tools/auto_page_fit.py paper/main.tex --target 8 --max-rounds 5

工作原理：
    1. 编译当前 .tex，统计实际页数
    2. 若页数超出目标 → 应用压缩策略
    3. 若页数不足目标 → 应用扩展策略
    4. 重复直到达标或超过最大轮次
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ── 压缩策略（页数过多时依次尝试）──────────────────────────────────
COMPRESS_STRATEGIES = [
    # (描述, 搜索正则, 替换内容)
    ("压缩图片间距 abovecaptionskip",
     r"\\setlength\{\\abovecaptionskip\}\{[^}]+\}",
     r"\\setlength{\\abovecaptionskip}{2pt}"),
    ("压缩图片间距 belowcaptionskip",
     r"\\setlength\{\\belowcaptionskip\}\{[^}]+\}",
     r"\\setlength{\\belowcaptionskip}{2pt}"),
    ("压缩 itemsep",
     r"\\setlength\{\\itemsep\}\{[^}]+\}",
     r"\\setlength{\\itemsep}{0pt}"),
    ("启用 microtype 压缩",
     r"% *\\usepackage\{microtype\}",
     r"\\usepackage[protrusion=true,expansion=true]{microtype}"),
    ("vspace 缩小 10pt → 4pt",
     r"\\vspace\{10pt\}",
     r"\\vspace{4pt}"),
    ("vspace 缩小 8pt → 2pt",
     r"\\vspace\{8pt\}",
     r"\\vspace{2pt}"),
    ("vspace 缩小 6pt → 2pt",
     r"\\vspace\{6pt\}",
     r"\\vspace{2pt}"),
]

# ── 扩展策略（页数不足时依次尝试）──────────────────────────────────
EXPAND_STRATEGIES = [
    ("放大图片间距 abovecaptionskip",
     r"\\setlength\{\\abovecaptionskip\}\{[^}]+\}",
     r"\\setlength{\\abovecaptionskip}{8pt}"),
    ("放大图片间距 belowcaptionskip",
     r"\\setlength\{\\belowcaptionskip\}\{[^}]+\}",
     r"\\setlength{\\belowcaptionskip}{6pt}"),
    ("扩展 vspace 2pt → 6pt",
     r"\\vspace\{2pt\}",
     r"\\vspace{6pt}"),
    ("扩展 vspace 4pt → 8pt",
     r"\\vspace\{4pt\}",
     r"\\vspace{8pt}"),
]


def compile_pdf(tex_file: Path) -> bool:
    """编译 .tex 文件，返回是否成功。"""
    result = subprocess.run(
        ["latexmk", "-pdf", "-synctex=1", "-interaction=nonstopmode",
         "-file-line-error", str(tex_file)],
        cwd=tex_file.parent,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_page_count(pdf_file: Path) -> int:
    """获取 PDF 页数，优先用 pdfinfo，备用 ghostscript。"""
    # 尝试 pdfinfo
    try:
        out = subprocess.check_output(["pdfinfo", str(pdf_file)],
                                      stderr=subprocess.DEVNULL, text=True)
        for line in out.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[1])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 尝试 gs
    try:
        out = subprocess.check_output(
            ["gs", "-q", "-dNODISPLAY", "-dNOSAFER",
             f"-sFileName={pdf_file}",
             "-c", "FileName (r) file runpdfbegin pdfpagecount = quit"],
            stderr=subprocess.DEVNULL, text=True)
        return int(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 用 synctex 日志估算（兜底）
    log_file = pdf_file.with_suffix(".log")
    if log_file.exists():
        content = log_file.read_text(errors="ignore")
        m = re.search(r"Output written on .+ \((\d+) page", content)
        if m:
            return int(m.group(1))

    raise RuntimeError(f"无法读取 {pdf_file} 的页数，请安装 pdfinfo（sudo apt install poppler-utils）")


def apply_strategy(tex_content: str, pattern: str, replacement: str) -> tuple[str, bool]:
    """应用单条策略，返回 (新内容, 是否有实际修改)。"""
    new_content, n = re.subn(pattern, replacement, tex_content)
    return new_content, n > 0


def backup_tex(tex_file: Path, round_num: int) -> Path:
    """备份当前 .tex 文件。"""
    backup = tex_file.with_name(f"{tex_file.stem}_round{round_num}.tex")
    shutil.copy2(tex_file, backup)
    return backup


def run(tex_file: Path, target_pages: int, max_rounds: int, dry_run: bool):
    pdf_file = tex_file.with_suffix(".pdf")
    log_entries = []

    print(f"\n目标：{target_pages} 页  |  tex：{tex_file}")
    print("═" * 60)

    # 初始编译
    print("[编译] 初始编译...")
    if not compile_pdf(tex_file):
        print("[错误] 初始编译失败，请检查 .tex 文件")
        sys.exit(1)

    current_pages = get_page_count(pdf_file)
    print(f"[当前] {current_pages} 页")

    if current_pages == target_pages:
        print("[完成] 已经是目标页数，无需调整。")
        return

    for round_num in range(1, max_rounds + 1):
        direction = "压缩" if current_pages > target_pages else "扩展"
        delta = abs(current_pages - target_pages)
        print(f"\n── Round {round_num}/{max_rounds}  [{direction}]  差距：{delta} 页 ──")

        strategies = COMPRESS_STRATEGIES if current_pages > target_pages else EXPAND_STRATEGIES
        tex_content = tex_file.read_text(encoding="utf-8")
        original_content = tex_content
        applied_any = False

        for desc, pattern, replacement in strategies:
            new_content, changed = apply_strategy(tex_content, pattern, replacement)
            if changed:
                print(f"  [策略] {desc}")
                tex_content = new_content
                applied_any = True

        if not applied_any:
            print("  [警告] 无可用自动策略，需要手动调整。")
            break

        if dry_run:
            print("  [dry-run] 未写入文件")
            break

        # 备份并写入
        backup = backup_tex(tex_file, round_num)
        print(f"  [备份] → {backup.name}")
        tex_file.write_text(tex_content, encoding="utf-8")

        # 重新编译
        print("  [编译] 重新编译...")
        if not compile_pdf(tex_file):
            print("  [错误] 编译失败，恢复备份")
            shutil.copy2(backup, tex_file)
            compile_pdf(tex_file)
            break

        new_pages = get_page_count(pdf_file)
        log_entries.append({
            "round": round_num,
            "before": current_pages,
            "after": new_pages,
            "direction": direction,
        })
        print(f"  [结果] {current_pages} 页 → {new_pages} 页")
        current_pages = new_pages

        if current_pages == target_pages:
            print(f"\n[完成] 达到目标 {target_pages} 页！")
            break
        elif (direction == "压缩" and current_pages < target_pages) or \
             (direction == "扩展" and current_pages > target_pages):
            print(f"  [提示] 已过冲，回退到上一版本")
            shutil.copy2(backup, tex_file)
            compile_pdf(tex_file)
            current_pages = get_page_count(pdf_file)
            break
    else:
        print(f"\n[结束] 已达最大轮次 {max_rounds}，当前 {current_pages} 页（目标 {target_pages} 页）")
        print("建议手动调整以下内容：")
        print("  • 缩短段落或删减冗余句子")
        print("  • 调整图表大小")
        print("  • 修改 \\vspace / \\hspace 数值")

    # 写日志
    log_file = tex_file.parent / "PAGE_FIT_LOG.json"
    log_data = {
        "tex": str(tex_file),
        "target": target_pages,
        "final_pages": current_pages,
        "rounds": log_entries,
    }
    log_file.write_text(json.dumps(log_data, indent=2, ensure_ascii=False))
    print(f"\n[日志] 写入 {log_file}")
    print("═" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="自动调整 LaTeX 论文页数到目标值")
    parser.add_argument("tex_file", help="主 .tex 文件路径")
    parser.add_argument("--target", "-t", type=int, required=True,
                        help="目标页数")
    parser.add_argument("--max-rounds", "-r", type=int, default=5,
                        help="最大调整轮次（默认 5）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只分析不修改文件")
    args = parser.parse_args()

    tex_file = Path(args.tex_file).resolve()
    if not tex_file.exists():
        print(f"[错误] 文件不存在：{tex_file}")
        sys.exit(1)

    run(tex_file, args.target, args.max_rounds, args.dry_run)


if __name__ == "__main__":
    main()

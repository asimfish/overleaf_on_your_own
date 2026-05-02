#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

command -v python3 >/dev/null 2>&1 || error "未找到 python3，请先安装 Python 3。"

info "配置 Overleaf-like LaTeX 编辑体验..."

python3 - "$@" <<'PY'
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

LATEX_WORKSHOP_EXTENSION = "James-Yu.latex-workshop"

KEYBINDING = {
    "key": "ctrl+s",
    "command": "runCommands",
    "args": {
        "commands": [
            "workbench.action.files.save",
            "latex-workshop.build",
            "latex-workshop.view",
        ]
    },
    "when": "editorTextFocus && editorLangId == 'latex'",
}

USER_SETTINGS = {
    "latex-workshop.view.pdf.viewer": "tab",
    "latex-workshop.view.pdf.internal.synctex.keybinding": "double-click",
    "latex-workshop.synctex.afterBuild.enabled": True,
    "latex-workshop.view.pdf.zoom": "page-width",
    "latex-workshop.latex.rootFile.doNotPrompt": True,
    "editor.minimap.enabled": False,
    "editor.wordWrap": "on",
    "editor.wrappingStrategy": "advanced",
    "editor.wrappingIndent": "same",
    "editor.scrollbar.horizontal": "hidden",
    "[latex]": {
        "editor.wordWrap": "on",
        "editor.wrappingStrategy": "advanced",
        "editor.wrappingIndent": "same",
        "editor.scrollbar.horizontal": "hidden",
    },
    "[tex]": {
        "editor.wordWrap": "on",
        "editor.wrappingStrategy": "advanced",
        "editor.wrappingIndent": "same",
        "editor.scrollbar.horizontal": "hidden",
    },
}

DEFAULT_PATH_PREFIX = ":".join([
    "/usr/bin",
    "/opt/conda/bin",
    "/Library/TeX/texbin",
    "/usr/local/texlive/2024/bin/universal-darwin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
])


def strip_json_comments(text: str) -> str:
    output = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            i += 1
            continue
        if char == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue
        if char == "/" and nxt == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        output.append(char)
        i += 1
    return "".join(output)


def load_jsonc(path: Path, default):
    if not path.exists() or not path.read_text().strip():
        return default
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(strip_json_comments(text))


def dump_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=4, ensure_ascii=False) + "\n")


def backup(path: Path):
    if path.exists():
        backup_path = path.with_suffix(path.suffix + ".bak_latexworkshop")
        backup_path.write_text(path.read_text())


def merge_dict(dst, src):
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            merge_dict(dst[key], value)
        else:
            dst[key] = value
    return dst


def first_existing(paths):
    for item in paths:
        if item and Path(item).exists():
            return str(Path(item))
    return None


def resolve_tools(path_prefix: str):
    env_path = path_prefix + os.pathsep + os.environ.get("PATH", "")
    latexmk = first_existing([shutil.which("latexmk", path=env_path), "/opt/conda/bin/latexmk"])
    pdflatex = first_existing(["/usr/bin/pdflatex", shutil.which("pdflatex", path=env_path)])
    bibtex = first_existing(["/usr/bin/bibtex", shutil.which("bibtex", path=env_path)])
    synctex = first_existing(["/usr/bin/synctex", shutil.which("synctex", path=env_path)])
    missing = [
        name
        for name, value in {
            "latexmk": latexmk,
            "pdflatex": pdflatex,
            "bibtex": bibtex,
            "synctex": synctex,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(
            "Missing LaTeX tools: "
            + ", ".join(missing)
            + "\nUbuntu/Debian: sudo apt install texlive-latex-extra texlive-science texlive-fonts-recommended latexmk -y"
        )
    return latexmk, pdflatex, bibtex, synctex, env_path


def workspace_settings(latexmk: str, pdflatex: str, bibtex: str, env_path: str):
    return {
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 500,
        "editor.minimap.enabled": False,
        "editor.wordWrap": "on",
        "editor.wrappingStrategy": "advanced",
        "editor.wrappingIndent": "same",
        "editor.scrollbar.horizontal": "hidden",
        "[latex]": USER_SETTINGS["[latex]"],
        "[tex]": USER_SETTINGS["[tex]"],
        "latex-workshop.latex.tools": [
            {
                "name": "latexmk",
                "command": latexmk,
                "args": [
                    "-synctex=1",
                    "-interaction=nonstopmode",
                    "-file-line-error",
                    "-pdf",
                    "-outdir=%OUTDIR%",
                    "%DOC%",
                ],
                "env": {"PATH": env_path},
            },
            {
                "name": "pdflatex",
                "command": pdflatex,
                "args": [
                    "-synctex=1",
                    "-interaction=nonstopmode",
                    "-file-line-error",
                    "%DOC%",
                ],
                "env": {"PATH": env_path},
            },
            {
                "name": "bibtex",
                "command": bibtex,
                "args": ["%DOCFILE%"],
                "env": {"PATH": env_path},
            },
        ],
        "latex-workshop.latex.recipes": [
            {"name": "latexmk", "tools": ["latexmk"]},
            {"name": "pdflatex -> bibtex -> pdflatex x2", "tools": ["pdflatex", "bibtex", "pdflatex", "pdflatex"]},
        ],
        "latex-workshop.latex.autoBuild.run": "onFileChange",
        "latex-workshop.latex.autoBuild.interval": 1000,
        "latex-workshop.view.pdf.viewer": "tab",
        "latex-workshop.view.pdf.internal.synctex.keybinding": "double-click",
        "latex-workshop.synctex.afterBuild.enabled": True,
        "latex-workshop.view.pdf.zoom": "page-width",
        "latex-workshop.view.pdf.scale": 1,
        "latex-workshop.latex.rootFile.doNotPrompt": True,
        "latex-workshop.latex.rootFile.useSubFile": False,
        "latex-workshop.latex.watch.usePolling": True,
        "latex-workshop.latex.watch.delay": 300,
        "latex-workshop.latex.outDir": "%DIR%",
        "latex-workshop.message.error.show": True,
        "latex-workshop.message.warning.show": False,
        "latex-workshop.latex.clean.fileTypes": [
            "*.aux",
            "*.bbl",
            "*.blg",
            "*.idx",
            "*.ind",
            "*.lof",
            "*.lot",
            "*.out",
            "*.toc",
            "*.fls",
            "*.log",
            "*.fdb_latexmk",
            "*.synctex.gz",
        ],
    }


def detect_user_dirs(home: Path):
    candidates = [
        home / ".windsurf-server/data/User",
        home / ".cursor-server/data/User",
        home / ".vscode-server/data/User",
        home / ".config/Cursor/User",
        home / ".config/Code/User",
        home / "Library/Application Support/Cursor/User",
        home / "Library/Application Support/Code/User",
    ]
    return [path for path in candidates if path.exists()]


def detect_windsurf_server(home: Path):
    base = home / ".windsurf-server/bin"
    if not base.exists():
        return None
    matches = sorted(base.glob("*/bin/windsurf-server"))
    return matches[-1] if matches else None


def update_workspace(workspace_dir: Path, settings, dry_run: bool):
    settings_file = workspace_dir / ".vscode/settings.json"
    if dry_run:
        print(f"Would update workspace settings: {settings_file}")
        return settings_file
    existing = load_jsonc(settings_file, {})
    backup(settings_file)
    merge_dict(existing, settings)
    dump_json(settings_file, existing)
    print(f"Updated workspace settings: {settings_file}")
    return settings_file


def update_user_settings(user_dir: Path, dry_run: bool):
    settings_file = user_dir / "settings.json"
    if dry_run:
        print(f"Would update user settings: {settings_file}")
        return settings_file
    settings = load_jsonc(settings_file, {})
    backup(settings_file)
    merge_dict(settings, USER_SETTINGS)
    dump_json(settings_file, settings)
    print(f"Updated user settings: {settings_file}")
    return settings_file


def update_keybindings(user_dir: Path, dry_run: bool):
    keybindings_file = user_dir / "keybindings.json"
    if dry_run:
        print(f"Would update keybindings: {keybindings_file}")
        return keybindings_file
    keybindings = load_jsonc(keybindings_file, [])
    if not isinstance(keybindings, list):
        raise SystemExit(f"{keybindings_file} must be a JSON array")
    backup(keybindings_file)
    exists = any(
        isinstance(item, dict)
        and item.get("key") == KEYBINDING["key"]
        and item.get("when") == KEYBINDING["when"]
        for item in keybindings
    )
    if not exists:
        keybindings.append(KEYBINDING)
    keybindings_file.parent.mkdir(parents=True, exist_ok=True)
    keybindings_file.write_text(
        "// Place your key bindings in this file to override the defaults\n"
        + json.dumps(keybindings, indent=4, ensure_ascii=False)
        + "\n"
    )
    print(f"Updated keybindings: {keybindings_file}")
    return keybindings_file


def install_extension(home: Path, dry_run: bool):
    server = detect_windsurf_server(home)
    if server:
        extensions_dir = home / ".windsurf-server/extensions"
        command = [str(server), "--install-extension", LATEX_WORKSHOP_EXTENSION, "--extensions-dir", str(extensions_dir), "--force"]
    else:
        cli = shutil.which("cursor") or shutil.which("code")
        if not cli:
            print("No windsurf-server/cursor/code CLI found; install James-Yu.latex-workshop from the Extensions panel.")
            return False
        command = [cli, "--install-extension", LATEX_WORKSHOP_EXTENSION, "--force"]
    print("Installing extension:", " ".join(command))
    if dry_run:
        return True
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        print("Extension installation failed. If your remote editor uses a proxy, make sure the proxy is reachable first.")
        return False
    return True


def check_optional_dependencies():
    if shutil.which("pdfinfo"):
        print("pdfinfo is installed; auto_page_fit can read PDF pages accurately.")
    else:
        print("pdfinfo is not installed; install poppler-utils for more accurate auto_page_fit page counts.")
    try:
        subprocess.run(["python3", "-c", "import anthropic"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("anthropic SDK is installed; auto_revise is available.")
    except Exception:
        print("anthropic SDK is not installed; run `pip install anthropic` to use auto_revise.")


def main():
    parser = argparse.ArgumentParser(description="Configure Overleaf-like LaTeX live preview in Cursor/VSCode/Windsurf.")
    parser.add_argument("workspace", nargs="?", default=os.getcwd(), help="Workspace directory to configure. Defaults to current directory.")
    parser.add_argument("--editor-user-dir", default="", help="Explicit Cursor/VSCode/Windsurf User config directory.")
    parser.add_argument("--path-prefix", default=DEFAULT_PATH_PREFIX, help="PATH prefix used by LaTeX Workshop tools.")
    parser.add_argument("--skip-extension", action="store_true", help="Do not install the LaTeX Workshop extension.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files or installing extensions.")
    args = parser.parse_args()

    home = Path.home()
    workspace_dir = Path(args.workspace).expanduser().resolve()
    latexmk, pdflatex, bibtex, synctex, env_path = resolve_tools(args.path_prefix)
    settings = workspace_settings(latexmk, pdflatex, bibtex, env_path)

    print(f"Workspace: {workspace_dir}")
    print(f"latexmk: {latexmk}")
    print(f"pdflatex: {pdflatex}")
    print(f"bibtex: {bibtex}")
    print(f"synctex: {synctex}")

    update_workspace(workspace_dir, settings, args.dry_run)

    user_dirs = [Path(args.editor_user_dir).expanduser().resolve()] if args.editor_user_dir else detect_user_dirs(home)
    if not user_dirs:
        print("No editor user settings directory found; workspace settings were still configured.")
    for user_dir in user_dirs:
        update_user_settings(user_dir, args.dry_run)
        update_keybindings(user_dir, args.dry_run)

    if not args.skip_extension:
        install_extension(home, args.dry_run)

    check_optional_dependencies()
    print("Done. Reload the editor window, open your main .tex file, then press Ctrl+S to build and view PDF.")
    print("Use the LaTeX Workshop PDF tab for reverse SyncTeX; directly opening the PDF file may not support source jumps.")


if __name__ == "__main__":
    main()
PY

info "✓ 安装脚本执行完成"

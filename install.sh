#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── 1. 检查依赖 ────────────────────────────────────────────────
info "检查依赖..."
command -v latexmk  >/dev/null 2>&1 || error "未找到 latexmk，请先安装 TeX Live：sudo apt install texlive-latex-extra latexmk"
command -v synctex  >/dev/null 2>&1 || error "未找到 synctex，请先安装 TeX Live：sudo apt install texlive-latex-extra"
info "latexmk $(latexmk --version | head -1 | grep -oP 'Version \\S+')"
info "synctex $(synctex --version | head -1 | grep -oP 'version \\S+')"

# ── 2. 确定编辑器类型（Cursor 优先） ───────────────────────────
if [ -d "$HOME/.config/Cursor/User" ]; then
    EDITOR_NAME="Cursor"
    USER_DIR="$HOME/.config/Cursor/User"
elif [ -d "$HOME/.config/Code/User" ]; then
    EDITOR_NAME="VSCode"
    USER_DIR="$HOME/.config/Code/User"
elif [ -d "$HOME/Library/Application Support/Cursor/User" ]; then
    EDITOR_NAME="Cursor (macOS)"
    USER_DIR="$HOME/Library/Application Support/Cursor/User"
elif [ -d "$HOME/Library/Application Support/Code/User" ]; then
    EDITOR_NAME="VSCode (macOS)"
    USER_DIR="$HOME/Library/Application Support/Code/User"
else
    error "未找到 Cursor 或 VSCode 配置目录，请先安装编辑器。"
fi
info "检测到编辑器：$EDITOR_NAME"

# ── 3. 确定工作区目录 ─────────────────────────────────────────
WORKSPACE_DIR="${1:-$(pwd)}"
VSCODE_DIR="$WORKSPACE_DIR/.vscode"
mkdir -p "$VSCODE_DIR"
info "工作区目录：$WORKSPACE_DIR"

# ── 4. 写入工作区 settings.json ──────────────────────────────
SETTINGS_FILE="$VSCODE_DIR/settings.json"
LATEX_SETTINGS=$(cat "$SCRIPT_DIR/configs/workspace_settings.json")

if [ -f "$SETTINGS_FILE" ]; then
    # 合并：用 python3 合并 JSON
    info "合并现有 $SETTINGS_FILE ..."
    python3 - <<PYEOF
import json, sys
with open('$SETTINGS_FILE', 'r') as f:
    existing = json.load(f)
with open('$SCRIPT_DIR/configs/workspace_settings.json', 'r') as f:
    latex = json.load(f)
existing.update(latex)
with open('$SETTINGS_FILE', 'w') as f:
    json.dump(existing, f, indent=4, ensure_ascii=False)
print('合并完成')
PYEOF
else
    cp "$SCRIPT_DIR/configs/workspace_settings.json" "$SETTINGS_FILE"
    info "已创建 $SETTINGS_FILE"
fi

# ── 5. 写入用户 keybindings.json ────────────────────────────
KEYBINDINGS_FILE="$USER_DIR/keybindings.json"
NEW_BINDINGS=$(cat "$SCRIPT_DIR/configs/keybindings_patch.json")

if [ -f "$KEYBINDINGS_FILE" ]; then
    info "合并 keybindings..."
    python3 - <<PYEOF
import json, re

def load_jsonc(path):
    with open(path, 'r') as f:
        content = f.read()
    content = re.sub(r'//[^\n]*', '', content)
    content = re.sub(r'/\\*.*?\\*/', '', content, flags=re.DOTALL)
    return json.loads(content)

existing = load_jsonc('$KEYBINDINGS_FILE')
new_bindings = load_jsonc('$SCRIPT_DIR/configs/keybindings_patch.json')

existing_keys = {(b.get('key',''), b.get('when','')) for b in existing}
for binding in new_bindings:
    key = (binding.get('key',''), binding.get('when',''))
    if key not in existing_keys:
        existing.append(binding)

with open('$KEYBINDINGS_FILE', 'w') as f:
    f.write('// Place your key bindings in this file to override the defaults\n')
    json.dump(existing, f, indent=4, ensure_ascii=False)
print('keybindings 合并完成')
PYEOF
else
    echo '// Place your key bindings in this file to override the defaults' > "$KEYBINDINGS_FILE"
    cat "$SCRIPT_DIR/configs/keybindings_patch.json" >> "$KEYBINDINGS_FILE"
    info "已创建 $KEYBINDINGS_FILE"
fi

# ── 6. 完成 ──────────────────────────────────────────────────
echo ""
info "✓ 安装完成！"
echo ""
echo "  下一步："
echo "  1. 在 $EDITOR_NAME 中按 Ctrl+Shift+P → 输入 'Reload Window' 重载配置"
echo "  2. 打开你的 .tex 文件"
echo "  3. 按 Ctrl+S → 自动编译并打开 PDF 预览"
echo "  4. 在 PDF 中双击 → 跳转到对应 tex 行"
echo "  5. 在 tex 中按 Ctrl+Alt+J → 高亮 PDF 对应位置"
echo ""

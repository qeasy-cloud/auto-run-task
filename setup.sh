#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# Auto Task Runner — Environment Setup
# Creates .task_env virtual environment and installs deps
# ──────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.task_env"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

echo "╔═══════════════════════════════════════════╗"
echo "║   🛠️  Auto Task Runner — Setup            ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Create venv if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment: .task_env ..."
    python3 -m venv "$VENV_DIR"
    echo "   ✅ Created."
else
    echo "📦 Virtual environment already exists."
fi

# Install deps
echo "📥 Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -q -r "$REQ_FILE"
echo "   ✅ Installed."

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Usage:"
echo "  source $VENV_DIR/bin/activate"
echo "  python $SCRIPT_DIR/run.py --help"
echo ""
echo "Or run directly:"
echo "  $VENV_DIR/bin/python $SCRIPT_DIR/run.py --help"

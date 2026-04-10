#!/usr/bin/env bash
# ============================================================
#  Career Planning Agent - Update Script
#  Usage:  sudo bash deploy-update.sh
# ============================================================
set -euo pipefail

APP_DIR="/opt/career-agent/app"
VENV_DIR="/opt/career-agent/venv"

cd "$APP_DIR"

echo ""
echo "[INFO] Updating Career Planning Agent..."
echo ""

# ── Save hashes before pull ──────────────────────────────────
OLD_REQ=$(md5sum requirements.txt | cut -d' ' -f1)
OLD_PKG=$(md5sum frontend/package-lock.json 2>/dev/null | cut -d' ' -f1 || echo "none")
OLD_SRC=$(find frontend/src -type f -exec md5sum {} + 2>/dev/null | sort | md5sum | cut -d' ' -f1)

# ── Pull latest code ────────────────────────────────────────
echo "[1/4] Pulling latest code..."
git pull origin master

# ── Check Python deps ───────────────────────────────────────
NEW_REQ=$(md5sum requirements.txt | cut -d' ' -f1)
if [ "$OLD_REQ" != "$NEW_REQ" ]; then
    echo "[2/4] requirements.txt changed, reinstalling..."
    "$VENV_DIR/bin/pip" install -r requirements.txt
else
    echo "[2/4] Python deps unchanged, skipping."
fi

# ── Check frontend rebuild ──────────────────────────────────
NEW_PKG=$(md5sum frontend/package-lock.json 2>/dev/null | cut -d' ' -f1 || echo "none")
NEW_SRC=$(find frontend/src -type f -exec md5sum {} + 2>/dev/null | sort | md5sum | cut -d' ' -f1)

if [ "$OLD_PKG" != "$NEW_PKG" ] || [ "$OLD_SRC" != "$NEW_SRC" ]; then
    echo "[3/4] Frontend changed, rebuilding..."
    cd frontend
    if [ "$OLD_PKG" != "$NEW_PKG" ]; then
        npm ci --prefer-offline
    fi
    npm run build
    # Sync latest graph data
    if [ -f "$APP_DIR/artifacts/pipeline/graph.json" ]; then
        mkdir -p dist/data
        cp "$APP_DIR/artifacts/pipeline/graph.json" dist/data/graph.json
    fi
    cd "$APP_DIR"
else
    echo "[3/4] Frontend unchanged, skipping build."
fi

# ── Restart backend ─────────────────────────────────────────
echo "[4/4] Restarting backend..."
systemctl restart career-agent

sleep 3

if systemctl is-active --quiet career-agent; then
    echo ""
    echo "[OK] Update complete! Backend is running."
else
    echo ""
    echo "[ERR] Backend failed. Check: journalctl -u career-agent -n 50"
fi

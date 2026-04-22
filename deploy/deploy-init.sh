#!/usr/bin/env bash
# ============================================================
#  Career Planning Agent - First-time Server Setup
#  Usage:  sudo bash deploy-init.sh
#  Target: Ubuntu / Debian / Alibaba Cloud Linux
# ============================================================
set -euo pipefail

# ── Configuration ────────────────────────────────────────────
REPO_URL="https://github.com/your-username/career-planning-agent.git"
APP_DIR="/opt/career-agent/app"
VENV_DIR="/opt/career-agent/venv"
SERVICE_USER="career-agent"

# ── Pre-flight checks ───────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERR] Please run as root: sudo bash deploy-init.sh"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Career Planning Agent - Server Setup"
echo "=========================================="
echo ""

# ── Step 1: Detect OS & install packages ────────────────────
echo "[1/9] Installing system packages..."

if command -v apt-get &>/dev/null; then
    # Debian / Ubuntu
    apt-get update -qq
    apt-get install -y -qq gcc git curl nginx python3 python3-venv python3-pip
    # Node.js
    if ! command -v node &>/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        apt-get install -y -qq nodejs
    fi
elif command -v dnf &>/dev/null; then
    # RHEL / Alibaba Cloud Linux
    dnf install -y gcc git curl --disableexcludes=all
    dnf install -y python3 python3-devel python3-pip --disableexcludes=all
    dnf install -y nginx --disableexcludes=all
    if ! command -v node &>/dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        dnf install -y nodejs --disableexcludes=all
    fi
else
    echo "[ERR] Unsupported OS. Only apt (Debian/Ubuntu) and dnf (RHEL/Alibaba Cloud) are supported."
    exit 1
fi

echo "[OK] python3: $(python3 --version)"
echo "[OK] node: $(node --version)"
echo "[OK] nginx: $(nginx -v 2>&1)"

# ── Step 2: Create service user ─────────────────────────────
echo "[2/9] Creating service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /sbin/nologin --home-dir /opt/career-agent "$SERVICE_USER"
fi
mkdir -p /opt/career-agent

# ── Step 3: Clone repo ──────────────────────────────────────
echo "[3/9] Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  Repo already exists, pulling latest..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# ── Step 4: Python virtual environment ──────────────────────
echo "[4/9] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

# ── Step 5: .env file ───────────────────────────────────────
echo "[5/9] Configuring environment..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "  ================================================"
    echo "  IMPORTANT: Edit .env and set your API keys!"
    echo "  nano $APP_DIR/.env"
    echo "  ================================================"
    echo ""
    read -p "  Press Enter after editing .env (or edit later)..."
fi
chmod 600 "$APP_DIR/.env"

# ── Step 6: Data files ──────────────────────────────────────
echo "[6/9] Checking data files..."
if [ ! -d "$APP_DIR/data" ] || [ -z "$(ls -A "$APP_DIR/data" 2>/dev/null)" ]; then
    echo ""
    echo "  ================================================"
    echo "  WARNING: data/ directory is missing or empty!"
    echo ""
    echo "  The data/ directory contains required runtime files"
    echo "  (graph.json, level_skills.json, etc.) but is gitignored."
    echo ""
    echo "  You must upload it manually before starting the service:"
    echo "    scp -r ./data root@your-server-ip:$APP_DIR/"
    echo "  ================================================"
    echo ""
    read -p "  Press Enter to continue (service will fail without data)..."
fi

# ── Step 7: Build frontend ──────────────────────────────────
echo "[7/9] Building frontend..."
cd "$APP_DIR/frontend"

# API_BASE is '/api' (relative path), no env override needed
npm ci --prefer-offline
npm run build

cd "$APP_DIR"

# ── Step 8: Set permissions ─────────────────────────────────
echo "[8/9] Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" /opt/career-agent
# Nginx needs read access to frontend/dist and all parent dirs
chmod -R o+rX /opt/career-agent

# ── Step 9: Nginx configuration ─────────────────────────────
echo "[9/9] Configuring Nginx & systemd..."
cp "$APP_DIR/deploy/career-agent.nginx" /etc/nginx/conf.d/career-agent.conf

# Remove default server configs to avoid port 80 conflict
rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

nginx -t
systemctl enable --now nginx
systemctl reload nginx

# ── Step 10: Systemd service ────────────────────────────────
cp "$APP_DIR/deploy/career-agent.service" /etc/systemd/system/career-agent.service
systemctl daemon-reload
systemctl enable --now career-agent

# ── Validation ───────────────────────────────────────────────
echo ""
echo "Waiting for backend to start..."
sleep 4

if systemctl is-active --quiet career-agent; then
    echo "[OK] Backend service is running"
else
    echo "[ERR] Backend failed to start. Check: journalctl -u career-agent -n 50"
fi

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "  Frontend:   http://$SERVER_IP"
echo "  API Docs:   http://$SERVER_IP/api/docs"
echo ""
echo "  Useful commands:"
echo "    journalctl -u career-agent -f       # View backend logs"
echo "    systemctl restart career-agent       # Restart backend"
echo "    sudo bash $APP_DIR/deploy/deploy-update.sh  # Update code"
echo ""
echo "  REMINDER: Open port 80 in Alibaba Cloud security group!"
echo ""

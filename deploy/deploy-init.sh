#!/usr/bin/env bash
# ============================================================
#  Career Planning Agent - First-time Server Setup
#  Usage:  sudo bash deploy-init.sh
#  Target: Alibaba Cloud Linux (RHEL-based)
# ============================================================
set -euo pipefail

# ── Configuration ────────────────────────────────────────────
REPO_URL="https://gitee.com/questionliuxinyu/career-planning-agent.git"
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

# ── Step 1: System packages ─────────────────────────────────
echo "[1/9] Installing system packages..."

# Nginx repo (not in default repos on Alibaba Cloud Linux)
if [ ! -f /etc/yum.repos.d/nginx.repo ]; then
    cat > /etc/yum.repos.d/nginx.repo << 'REPO'
[nginx-stable]
name=nginx stable repo
baseurl=http://nginx.org/packages/centos/8/$basearch/
gpgcheck=0
enabled=1
REPO
fi

dnf install -y gcc git --disableexcludes=all
dnf install -y python3.11 python3.11-devel python3.11-pip --disableexcludes=all
dnf install -y nginx --disableexcludes=all

# Node.js 18+
if ! command -v node &>/dev/null; then
    echo "[INFO] Installing Node.js..."
    curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
    dnf install -y nodejs --disableexcludes=all
fi

echo "[OK] python3.11: $(python3.11 --version)"
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
    cd "$APP_DIR" && git pull origin master
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# ── Step 4: Python virtual environment ──────────────────────
echo "[4/9] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3.11 -m venv "$VENV_DIR"
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

# ── Step 6: Build frontend ──────────────────────────────────
echo "[6/9] Building frontend..."
cd "$APP_DIR/frontend"

# VITE_API_URL empty = same-origin (Nginx proxies /api/* to backend)
echo "VITE_API_URL=" > .env

npm ci --prefer-offline
npm run build

# Sync latest graph data into build output
if [ -f "$APP_DIR/artifacts/pipeline/graph.json" ]; then
    mkdir -p "$APP_DIR/frontend/dist/data"
    cp "$APP_DIR/artifacts/pipeline/graph.json" "$APP_DIR/frontend/dist/data/graph.json"
    echo "  [OK] Synced graph.json into frontend build"
fi

cd "$APP_DIR"

# ── Step 7: Set permissions ─────────────────────────────────
echo "[7/9] Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" /opt/career-agent
# Nginx needs read access to frontend/dist and all parent dirs
chmod -R o+rX /opt/career-agent

# ── Step 8: Nginx configuration ─────────────────────────────
echo "[8/9] Configuring Nginx..."
cp "$APP_DIR/deploy/career-agent.nginx" /etc/nginx/conf.d/career-agent.conf

# Remove default server configs to avoid port 80 conflict
rm -f /etc/nginx/conf.d/default.conf

nginx -t
systemctl enable --now nginx
systemctl reload nginx

# ── Step 9: Start backend service ────────────────────────────
echo "[9/9] Starting backend service..."
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
echo "  Frontend:  http://$SERVER_IP"
echo "  API Docs:  http://$SERVER_IP/api/docs"
echo "  API Health: http://$SERVER_IP/api/health"
echo ""
echo "  Useful commands:"
echo "    journalctl -u career-agent -f      # View backend logs"
echo "    systemctl restart career-agent      # Restart backend"
echo "    sudo bash $APP_DIR/deploy/deploy-update.sh  # Update code"
echo ""
echo "  REMINDER: Open port 80 in Alibaba Cloud security group!"
echo ""

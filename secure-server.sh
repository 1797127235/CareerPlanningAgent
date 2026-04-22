#!/bin/bash
# =============================================================================
# 职途智析 服务器安全加固脚本
# 在阿里云 ECS (Ubuntu 22.04) 上以 root 执行
# =============================================================================
set -euo pipefail

APP_DIR="/root/CareerPlanningAgent"
NGINX_ROOT="/var/www/career-agent"
SERVICE_USER="career-agent"

echo "=== [1/9] 创建非 root 运行用户 ==="
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/false -d /var/lib/$SERVICE_USER -m $SERVICE_USER
fi

# 确保应用目录可被服务用户读取
chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR
chmod -R u+rwX,go-rwx $APP_DIR/.env 2>/dev/null || true

echo "=== [2/9] 加固 .env 文件权限 ==="
if [[ -f "$APP_DIR/.env" ]]; then
    chmod 600 "$APP_DIR/.env"
    chown $SERVICE_USER:$SERVICE_USER "$APP_DIR/.env"
fi

echo "=== [3/9] 配置 UFW 防火墙 ==="
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

echo "=== [4/9] 配置 fail2ban (防暴力破解) ==="
apt-get update -qq
apt-get install -y -qq fail2ban

cat > /etc/fail2ban/jail.local << 'FAIL2BAN'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
FAIL2BAN

systemctl restart fail2ban
systemctl enable fail2ban

echo "=== [5/9] 配置 Nginx (安全头 + 速率限制 + 静态文件) ==="
mkdir -p /etc/nginx/conf.d

# 复制前端构建产物到 www-data 可访问目录
mkdir -p "$NGINX_ROOT"
if [[ -d "$APP_DIR/frontend/dist" ]]; then
    rsync -a --delete "$APP_DIR/frontend/dist/" "$NGINX_ROOT/"
    chown -R www-data:www-data "$NGINX_ROOT"
fi

# 速率限制区域
cat > /etc/nginx/conf.d/rate-limits.conf << 'RATECONF'
# 登录/注册接口：5r/m
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;
# API 通用：100r/m
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
# SSE 聊天：30r/m（流式消耗大）
limit_req_zone $binary_remote_addr zone=chat:10m rate=30r/m;
RATECONF

cat > /etc/nginx/conf.d/career-agent.conf << 'NGINX_CONF'
server {
    listen 80;
    server_name _;
    root /var/www/career-agent;
    index index.html;
    client_max_body_size 20M;

    # ── Security Headers ─────────────────────────────────────────────
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    # CSP: 允许同域 + ws: 用于 Vite HMR (生产可收紧)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' ws: wss:; frame-ancestors 'self';" always;

    # ── Hide nginx version ───────────────────────────────────────────
    server_tokens off;

    # ── Block hidden files ───────────────────────────────────────────
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # ── Static assets (long cache) ───────────────────────────────────
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # ── Frontend SPA fallback ────────────────────────────────────────
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ── API: Chat / SSE (higher timeout, no buffering) ───────────────
    location /api/chat {
        limit_req zone=chat burst=10 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # ── API: Auth (strict rate limit) ────────────────────────────────
    location /api/auth/ {
        limit_req zone=auth burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    # ── API: All other routes ────────────────────────────────────────
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
NGINX_CONF

rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=== [6/9] 配置 systemd 服务 (非 root 运行) ==="
cat > /etc/systemd/system/career-agent.service << SERVICE_CONF
[Unit]
Description=Career Planning Agent - FastAPI Backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
Environment=PYTHONPATH=$APP_DIR
Environment=ENV=production
ExecStart=$APP_DIR/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

# ── Security hardening ─────────────────────────────────────────────
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

# ── Resource limits ────────────────────────────────────────────────
LimitNOFILE=65535
LimitNPROC=4096

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_CONF

systemctl daemon-reload
systemctl enable career-agent

echo "=== [7/9] 配置 SQLite 自动备份 ==="
mkdir -p /var/backups/career-agent
cat > /etc/cron.d/career-agent-backup << 'CRON'
# 每天 03:17 备份 SQLite 数据库，保留 14 天
17 3 * * * root sqlite3 /root/CareerPlanningAgent/data/app_state/app.db ".backup /var/backups/career-agent/app-$(date +\%Y\%m\%d-\%H\%M).db" && find /var/backups/career-agent -name "app-*.db" -mtime +14 -delete
CRON
chmod 644 /etc/cron.d/career-agent-backup

echo "=== [8/9] 配置日志轮转 ==="
cat > /etc/logrotate.d/career-agent << 'LOGROTATE'
/var/log/career-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 career-agent career-agent
    sharedscripts
    postrotate
        systemctl reload career-agent 2>/dev/null || true
    endscript
}
LOGROTATE

echo "=== [9/9] 重启服务 ==="
systemctl restart career-agent
sleep 3
systemctl status career-agent --no-pager

echo ""
echo "========================================"
echo "安全加固完成"
echo "========================================"
echo ""
echo "下一步（强烈建议）："
echo "  1. 配置 HTTPS: certbot --nginx -d your-domain.com"
echo "  2. 修改 SSH 端口并禁用 root 登录: nano /etc/ssh/sshd_config"
echo "  3. 确认 .env 中 JWT_SECRET_KEY 已设置为随机字符串"
echo ""
echo "检查命令："
echo "  journalctl -u career-agent -f       # 查看后端日志"
echo "  tail -f /var/log/nginx/error.log    # 查看 Nginx 错误"
echo "  fail2ban-client status              # 查看封禁状态"
echo "  ufw status verbose                  # 查看防火墙状态"
echo "========================================"

#!/bin/bash
set -euo pipefail

echo "=== Step 1: Install Nginx ==="
apt update
apt install -y nginx

echo "=== Step 2: Write Nginx config ==="
cat > /etc/nginx/conf.d/career-agent.conf << 'NGINX_CONF'
server {
    listen 80;
    server_name _;
    root /root/CareerPlanningAgent/frontend/dist;
    index index.html;
    client_max_body_size 20M;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        add_header Cache-Control no-cache;
        add_header X-Accel-Buffering no;
    }

    location ~ /\. {
        deny all;
    }
}
NGINX_CONF

rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=== Step 3: Write systemd service ==="
cat > /etc/systemd/system/career-agent.service << 'SERVICE_CONF'
[Unit]
Description=Career Planning Agent Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/CareerPlanningAgent
Environment=PYTHONPATH=/root/CareerPlanningAgent
EnvironmentFile=/root/CareerPlanningAgent/.env
ExecStart=/root/CareerPlanningAgent/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_CONF

systemctl daemon-reload
systemctl enable --now career-agent

echo "=== Step 4: Status check ==="
sleep 3
systemctl status career-agent --no-pager

echo ""
echo "========================================"
echo "Done! Check: http://YOUR_SERVER_IP"
echo "Backend logs: journalctl -u career-agent -f"
echo "========================================"

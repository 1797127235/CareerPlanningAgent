# 服务器部署与维护指南

## 基本信息

| 项目 | 值 |
|------|-----|
| 服务器 IP | 8.130.154.124 |
| 访问地址 | http://8.130.154.124 |
| API 文档 | http://8.130.154.124/api/docs |
| SSH 用户 | admin |
| 应用目录 | /opt/career-agent/app |
| 代码仓库 | https://gitee.com/questionliuxinyu/career-planning-agent |

---

## 日常操作

### 推送代码更新

```bash
# 1. 本地提交并推送
git add .
git commit -m "描述改动"
git push origin master

# 2. SSH 到服务器
ssh admin@8.130.154.124

# 3. 执行更新脚本（自动判断是否需要重装依赖/重建前端）
cd /opt/career-agent/app
sudo bash deploy/deploy-update.sh
```

> 脚本会自动检测：Python 依赖是否变化、前端代码是否变化，按需执行，最后重启后端。

---

### 查看后端日志

```bash
# 实时日志
sudo journalctl -u career-agent -f

# 最近 50 条
sudo journalctl -u career-agent -n 50 --no-pager
```

### 重启 / 停止 / 查看状态

```bash
sudo systemctl restart career-agent   # 重启后端
sudo systemctl stop career-agent      # 停止后端
sudo systemctl start career-agent     # 启动后端
sudo systemctl status career-agent    # 查看状态

sudo systemctl reload nginx           # 重载 Nginx 配置
sudo systemctl restart nginx          # 重启 Nginx
```

### 健康检查

```bash
curl http://localhost/api/health
# data_loaded: true 表示图谱数据已加载
```

---

## 修改配置（API Key 等）

```bash
sudo nano /opt/career-agent/app/.env
sudo systemctl restart career-agent
```

---

## 前端单独重新构建

如果只改了前端，不想跑完整更新脚本：

```bash
cd /opt/career-agent/app/frontend
sudo npx vite build
sudo systemctl reload nginx
```

---

## 首次部署（新服务器）

```bash
git clone https://gitee.com/questionliuxinyu/career-planning-agent.git
cd career-planning-agent
sudo bash deploy/deploy-init.sh
```

> 如果遇到 nginx 安装失败，先手动添加 nginx 源：
> ```bash
> sudo tee /etc/yum.repos.d/nginx.repo << 'EOF'
> [nginx-stable]
> name=nginx stable repo
> baseurl=http://nginx.org/packages/centos/8/$basearch/
> gpgcheck=0
> enabled=1
> EOF
> ```
> 然后重新运行脚本。

---

## 常见问题

**Q: git pull 报 dubious ownership**
```bash
sudo git config --global --add safe.directory /opt/career-agent/app
```

**Q: 前端 npm build 报 TypeScript 错误**
```bash
# 跳过 tsc，直接用 vite build
cd /opt/career-agent/app/frontend
sudo npx vite build
```

**Q: 端口 80 无法访问**
- 检查阿里云安全组是否开放了 TCP 80 入方向
- 检查 Nginx 状态：`sudo systemctl status nginx`

**Q: data_loaded: false**
- 不影响核心功能（图谱、简历解析）
- 表示 job_type_profiles.json 不存在，是遗留的可选数据

---

## 架构说明

```
用户浏览器
    ↓ HTTP :80
  Nginx
    ├── / → 前端静态文件 (/opt/career-agent/app/frontend/dist)
    └── /api/* → 反向代理 → FastAPI :8000
                                ↓
                        Python 后端
                        + Qdrant 本地向量库
                        + artifacts/pipeline/graph.json
```

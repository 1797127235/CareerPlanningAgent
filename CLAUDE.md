# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 启动与开发命令

**一键启动（推荐）**
```bash
start.bat   # 按提示选 1 启动前端+后端
```

**手动启动**
```bash
# 后端
python -m uvicorn backend.app:app --reload   # http://localhost:8000

# 前端
cd frontend && npm run dev                    # http://localhost:5173
```
